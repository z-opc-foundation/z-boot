#!/usr/bin/env python3
"""published_graph_audit.py — 逐边对账：中央上每个自家发布件的 pom 里写着的内部依赖，
那些坐标在中央**取不取得动**（pom / jar 各一次 ranged GET，按 Maven 口径先补出版本再点）。

为什么单独要它（另两个量具都管不到这一层）：
  * central_chain_probe 走 `<parent>` 链，查"pom 206 但 parent 404 所以读不动"那一族；
  * repo1_census 查"我这仓的坐标在不在中央"；
  * 而**发布 pom 里的兄弟依赖边**没人查过。z-cache:1.0.2 那次的形状是"叶子 206、parent 404"，
    换成边的形状就是"聚合件指向一个中央没有的 starter 版本"：消费者一行 import 就炸，
    而本机因为 `~/.m2` 里有东西全绿。fleet 的 175 格由 chain_probe 覆盖，这里覆盖**边**。

三处会造成假报警的口径，都按实测处理（第一版就踩过前两条）：
  1. 版本 `${...}` 先按**该 pom 自己的** `<properties>` 补，`${project.version}`/`${revision}` 按
     pom 自身版本补；补不出再沿 `<parent>` 链（中央回读）找 DM/import 条目。BOM 的 DM 条目天生写
     属性名，叶子 pom 的无版本依赖靠父链供面值都是**合法形状**，不是缺陷 —— 只有链上也补不出
     才算 NO_VERSION_UNMANAGED（那种消费者当场红）。
  2. `<packaging>pom</packaging>` 的坐标没有 jar 是正常的：先读目标 pom 的 packaging，只有 jar 族
     才点 jar。现测 z-util-all:1.0.14 / z-util-serialize:1.0.14 就是 pom 聚合件。
  3. repo1 偶尔整秒级超时（实测同一 jar 先 JAR_0 后 206）⇒ code=0 一律重试 3 次再判。

`<dependencyManagement>` 里的条目是登记位（`dm`），`<dependencies>` 里的才是使用点（`deps`）：
dm 断一格只会让消费者拿不到面值，deps 断了是构建当场红 ⇒ 分开计数。

只查每个坐标的 **latest** 版（新消费者实际拿到的那份）。只读，不写任何东西。

用法：
  python3 z-boot/_doc/003_script/published_graph_audit.py
  python3 z-boot/_doc/003_script/published_graph_audit.py --only z-ctc    # 只查名字含此串的坐标
  python3 z-boot/_doc/003_script/published_graph_audit.py --quiet         # 只印结论与问题行
"""
import argparse
import concurrent.futures as cf
import re
import threading
import urllib.request
import xml.etree.ElementTree as ET

BASE = "https://repo1.maven.org/maven2/io/github/yuku123/"
NS = "{http://maven.apache.org/POM/4.0.0}"
_lock = threading.Lock()
_poms = {}      # (art, ver) -> root Element | None
_status = {}    # url -> last http code（诊断用）


def _fetch(url, ranged=False, tries=3):
    last = 0
    for _ in range(tries):
        req = urllib.request.Request(url)
        if ranged:
            req.add_header("Range", "bytes=0-0")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except Exception as e:
            last = getattr(e, "code", None) or 0
            if last:      # 明确的 4xx/5xx 不用重试
                return last, ""
    return last, ""       # 0 = 网络抖动，调用方按 UNKNOWN 处理


def pom(art, ver):
    key = (art, ver)
    with _lock:
        if key in _poms:
            return _poms[key]
    code, body = _fetch(BASE + art + "/" + ver + "/" + art + "-" + ver + ".pom")
    root = None
    if code == 200:
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            root = None
    with _lock:
        _poms[key] = root
        return root


def alive(url):
    for _ in range(3):
        c = _fetch(url, ranged=True)[0]
        if c in (200, 206, 404):
            return c
    return 0


def text(el, tag):
    return el.findtext(NS + tag) if el is not None else None


def artifacts():
    code, body = _fetch(BASE)
    if code != 200:
        raise SystemExit("列目录失败 %s %s" % (code, BASE))
    return sorted(a for a in set(re.findall(r'href="([a-z0-9.-]+)/"', body)) if a != "..")


def latest(a):
    code, body = _fetch(BASE + a + "/maven-metadata.xml")
    if code != 200:
        return None
    m = re.search(r"<latest>([^<]+)</latest>", body)
    if m:
        return m.group(1)
    vs = [v for v in re.findall(r"<version>([^<]+)</version>", body) if "SNAPSHOT" not in v]
    return vs[-1] if vs else None


def props_of(root):
    p = root.find(NS + "properties")
    return {c.tag.replace(NS, ""): (c.text or "").strip() for c in p} if p is not None else {}


def interp(val, props, selfv):
    for _ in range(8):
        m = re.search(r"\$\{([^}]+)\}", val)
        if not m:
            return val
        k = m.group(1)
        if k in ("project.version", "revision", "version"):
            rep = selfv
        elif k in ("project.groupId", "groupId"):
            rep = "io.github.yuku123"
        else:
            rep = props.get(k)
        if rep is None:
            return None
        val = val.replace("${" + k + "}", rep)
    return None if "${" in val else val


def chain(art, ver, limit=6):
    """按 Maven 口径往上的 pom 列表（含自己）。只跟自家那一截父链：本工具只判
    io.github.yuku123 的边，org.springframework.* 那类父 pom 不在 BASE 下，硬去找会假报断链。
    自家链上任意一跳中央取不到 ⇒ 记断链并停下（那就是 z-cache:1.0.2 那一族的形状）。"""
    out, cur, depth = [], (art, ver), 0
    broken = None
    while cur and depth < limit:
        r = pom(*cur)
        if r is None:
            broken = cur
            break
        out.append(r)
        p = r.find(NS + "parent")
        if p is None:
            cur = None
            continue
        if p.findtext(NS + "groupId", "") != "io.github.yuku123":
            cur = None                      # 出自家命名空间：这截父链与本工具的判据无关，停
            continue
        pv = p.findtext(NS + "version")
        if pv and "${" in pv:
            pv = interp(pv, props_of(r), text(r, "version") or "")
        cur = (p.findtext(NS + "artifactId"), pv)
        if not cur[0] or not cur[1]:
            cur = None
        depth += 1
    return out, broken


def managed_map(root, selfv, seen=None, depth=0):
    """该 pom 的 DM 面值表 {artifactId: version}，含 scope=import 的 BOM 递归（深度限 3）。"""
    props = props_of(root)
    dm = root.find(NS + "dependencyManagement")
    out = {}
    if dm is None or depth > 3:
        return out
    imports = []
    for d in dm.iter(NS + "dependency"):
        a = d.findtext(NS + "artifactId")
        v = d.findtext(NS + "version")
        if not a or v is None:
            continue
        v = interp(v.strip(), props, selfv)
        if d.findtext(NS + "scope") == "import" and d.findtext(NS + "type") == "pom":
            if v:
                imports.append((a, v))
            continue
        if v:
            out[a] = v
    if seen is None:
        seen = set()
    for a, v in imports:
        if (a, v) in seen:
            continue
        seen.add((a, v))
        r = pom(a, v)
        if r is None:
            continue
        for k, val in managed_map(r, v, seen, depth + 1).items():
            out.setdefault(k, val)
    return out


def edges(a, v):
    """返回 (边列表 [(art, ver|None, scope, where, note)], 自身备注)"""
    r = pom(a, v)
    if r is None:
        return [], "POM_UNREADABLE"
    props = props_of(r)
    selfv = text(r, "version") or v
    ch, broken = chain(a, v)
    mgr = {}
    for node in reversed(ch):        # 越靠上的父链越先写，本 pom 的 DM 优先覆盖
        sv = text(node, "version") or v
        for k, val in managed_map(node, sv).items():
            mgr[k] = val
    dmnode = r.find(NS + "dependencyManagement")
    dm_arts = {d.findtext(NS + "artifactId", "") for d in dmnode.iter(NS + "dependency")} if dmnode is not None else set()
    out = []
    for d in r.iter(NS + "dependency"):
        if d.findtext(NS + "groupId", "") != "io.github.yuku123":
            continue
        art = d.findtext(NS + "artifactId", "")
        if art == a:
            continue
        ver = d.findtext(NS + "version")
        scope = d.findtext(NS + "scope", "compile")
        where = "dm" if art in dm_arts else "deps"
        if ver is None:
            if art in mgr:
                out.append((art, mgr[art], scope, where, "via_parent"))
            else:
                out.append((art, None, scope, where, "NO_VERSION_UNMANAGED"))
            continue
        r2 = interp(ver.strip(), props, selfv)
        if r2 is None:
            r2 = mgr.get(art)
            out.append((art, r2, scope, where, "via_parent" if r2 else "UNRESOLVED_VERSION"))
        else:
            out.append((art, r2, scope, where, ""))
    if broken:
        return out, "PARENT_CHAIN_BREAK@%s:%s" % broken
    return out, ""


def check(art, ver):
    if ver is None:
        return "NO_VERSION"
    base = BASE + art + "/" + ver + "/" + art + "-" + ver
    c = alive(base + ".pom")
    if c == 404:
        return "POM_404"
    if c == 0:
        return "PROBE_TIMEOUT"
    if c not in (200, 206):
        return "POM_%s" % c
    r = pom(art, ver)
    pkg = (text(r, "packaging") or "jar") if r is not None else "unknown"
    if pkg != "jar":
        return "OK"        # pom / 聚合件本就没有 jar
    c = alive(base + ".jar")
    if c == 404:
        return "JAR_404"
    if c == 0:
        return "PROBE_TIMEOUT"
    return "OK" if c in (200, 206) else "JAR_%s" % c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--workers", type=int, default=10)
    args = ap.parse_args()

    arts = [a for a in artifacts() if not args.only or args.only in a]
    with cf.ThreadPoolExecutor(args.workers) as ex:
        lvs = list(ex.map(latest, arts))
    pairs = [(a, v) for a, v in zip(arts, lvs) if v]
    if not args.quiet:
        print("中央自家坐标 %d 个（有 latest 版 %d，无 metadata %d）"
              % (len(arts), len(pairs), len(arts) - len(pairs)))

    with cf.ThreadPoolExecutor(args.workers) as ex:
        res = list(ex.map(lambda av: (av,) + tuple(edges(*av)), pairs))
    selfbad = [(a, v, n) for (a, v), es, n in res if n]

    todo = {}
    for (a, v), es, n in res:
        for art, ver, scope, where, note in es:
            todo[(a, v, art, ver, scope, where, note)] = None
    if not args.quiet:
        print("内部边（去重）%d 条，逐条点…（缓存 pom %d 份）" % (len(todo), len(_poms)))
    with cf.ThreadPoolExecutor(args.workers) as ex:
        checked = list(ex.map(lambda k: (k, check(k[2], k[3])), todo.keys()))
    bad = [(k, s) for k, s in checked if s not in ("OK", "PROBE_TIMEOUT")]
    timeouts = [(k, s) for k, s in checked if s == "PROBE_TIMEOUT"]

    lat = dict(pairs)
    old, unmanaged = {}, {}
    for (a, v, art, ver, scope, where, note) in todo.keys():
        if note in ("NO_VERSION_UNMANAGED", "UNRESOLVED_VERSION"):
            unmanaged.setdefault((a, v), []).append((art, note))
        elif art in lat and ver != lat[art]:
            old.setdefault((art, ver, lat[art]), []).append(a)
    ndeps = len([1 for k in todo if k[5] == "deps"])
    print("\n结论：%d 坐标 / %d 条内部边（使用点 %d、登记位 %d）"
          % (len(pairs), len(todo), ndeps, len(todo) - ndeps))
    print("      断边 %d（deps %d / dm %d）、父链补不出版本 %d 处、指向旧号 %d 种、自身读不动 %d、超时 %d"
          % (len(bad), len([1 for k, s in bad if k[5] == "deps"]),
             len([1 for k, s in bad if k[5] == "dm"]), len(unmanaged), len(old), len(selfbad), len(timeouts)))
    for k, s in sorted(bad):
        print("  ✗ %s:%s 边 %s:%s [%s/%s%s] → %s" % (k[0], k[1], k[2], k[3], k[4], k[5],
                                                    ("/" + k[6]) if k[6] else "", s))
    for a, v, n in sorted(selfbad):
        print("  ✗ 自身/父链读不动 %s:%s → %s" % (a, v, n))
    for (a, v), lst in sorted(unmanaged.items()):
        print("  ! 版本补不出 %s:%s → %s" % (a, v, ", ".join("%s(%s)" % x for x in lst[:5])))
    if timeouts and not args.quiet:
        print("  （超时 %d 条已单列，不算断链；重跑即知）" % len(timeouts))
    if old and not args.quiet:
        print("\n指向旧号的边（不断链，是账目债 ⇒ 攒进下一次发版批次）：")
        for (art, ver, cur), srcs in sorted(old.items()):
            print("  %-40s 指 %s（中央现 latest %s）← %d 个发布件：%s"
                  % (art, ver, cur, len(set(srcs)), ",".join(sorted(set(srcs))[:4])))


if __name__ == "__main__":
    main()
