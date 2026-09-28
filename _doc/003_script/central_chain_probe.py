#!/usr/bin/env python3
"""
central_chain_probe.py — 查"repo1 上 206 但其实读不动"的那一类发布件。

为什么需要它：ranged GET 拿 206 只证明文件在，不证明 Maven 能解析它。发布件的 pom 若带着
`<parent>`，Maven 必须能把那件 parent 也取到才算读得通；而我们早期发布的一批件的根 pom
写着 `com.zifang:z-opc:1.0.0-SNAPSHOT` 这类**只在作者 ~/.m2 里存在**的 parent，中央永远没有
⇒ 干净机器上解析它们必挂，本机却因为 `~/.m2` 有快照而一路绿。Central 不可覆盖，这种号
**永远修不好**，只能把消费方抬到第一个自包含的版本。所以这条必须单独量，不能靠 repo1_census。

两类消费方都查：
  1. z-boot-fleet 的 dependencyManagement —— 全组织继承来的那一格，面值错了 30 个仓一起挂；
  2. 指定仓（--repo）自家 pom 里**写死字面版本**的 io.github.yuku123 依赖 —— 字面 <version>
     优先级高于任何 DM，fleet 顶不住它（README 步骤 4 的那一族坑）。

parent 链按 Maven 的解析顺序逐跳取，任意一跳 404 ⇒ 判 POISONED；链上出现 com.zifang ⇒ 单独
标注（那些 groupId 从没上过中央）。只读，不写任何东西。

用法：
  python3 z-boot/_doc/003_script/central_chain_probe.py                 # 只查 fleet
  python3 z-boot/_doc/003_script/central_chain_probe.py --repo z-kb     # fleet + 该仓字面格
  python3 z-boot/_doc/003_script/central_chain_probe.py --quiet         # 只印结论行
"""
import argparse
import concurrent.futures
import os
import re
import sys
import urllib.error
import urllib.request

BASE = "https://repo1.maven.org/maven2"
INTERNAL = re.compile(r"^(io\.github\.yuku123|com\.zifang)$")
MAX_DEPTH = 8


def pom_url(g, a, v):
    return f"{BASE}/{g.replace('.', '/')}/{a}/{v}/{a}-{v}.pom"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "central-chain-probe"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # DNS/超时也按"读不动"报出来，别静默
        return -1, f"{type(e).__name__}: {e}"


def strip_comment(pom):
    return re.sub(r"<!--.*?-->", "", pom, flags=re.S)


def parent_of(pom):
    body = strip_comment(pom)
    m = re.search(r"<parent>\s*(.*?)</parent>", body, re.S)
    if not m:
        return None
    inner = m.group(1)
    got = {}
    for k in ("groupId", "artifactId", "version"):
        f = re.search(rf"<{k}>([^<]+)</{k}>", inner)
        got[k] = f.group(1).strip() if f else None
    return got if got.get("groupId") and got.get("artifactId") and got.get("version") else None


def resolve_property(pom, value):
    """parent <version> 写成 ${x} 的极少见形状：按本 pom 的 properties 兜一次。"""
    m = re.fullmatch(r"\$\{([^}]+)\}", value or "")
    if not m:
        return value
    key = m.group(1)
    f = re.search(rf"<{re.escape(key)}>[^<]*</{re.escape(key)}>", strip_comment(pom))
    return f.group(0).split(">")[1].split("<")[0].strip() if f else None


def probe(coord):
    g, a, v = coord
    chain, seen = [], []
    cur = (g, a, v)
    while cur and len(seen) < MAX_DEPTH:
        cg, ca, cv = cur
        if (cg, ca, cv) in seen:
            return coord, "CYCLE", chain
        seen.append((cg, ca, cv))
        status, text = fetch(pom_url(cg, ca, cv))
        chain.append(f"{cg}:{ca}:{cv} -> http {status}")
        if status != 200:
            verdict = "ABSENT" if status == 404 else "NETWORK"
            return coord, verdict, chain
        if cur != (g, a, v) and not INTERNAL.match(cg):
            return coord, "THIRD_PARTY_PARENT_STOP", chain
        p = parent_of(text)
        if not p:
            return coord, "SELF_CONTAINED", chain
        nv = resolve_property(text, p["version"])
        if nv is None:
            return coord, "UNRESOLVED_PARENT_VERSION", chain
        cur = (p["groupId"], p["artifactId"], nv)
        if cur[0] == "com.zifang":
            chain.append(f"parent 是 {cur[0]}:{cur[1]}:{cur[2]}（该 groupId 从未上中央）")
            st, _ = fetch(pom_url(*cur))
            return coord, "POISONED", chain if st != 200 else chain
    return coord, "TOO_DEEP", chain


def fleet_coords(root):
    path = os.path.join(root, "z-boot", "z-boot-fleet", "pom.xml")
    if not os.path.exists(path):
        return [], f"找不到 {path}"
    raw = open(path, encoding="utf-8").read()
    pom = strip_comment(raw)
    # fleet 的内部件那一格写的是 ${z-vector.version} 这类属性 ⇒ 先建属性表，再按属性取值，
    # 否则"字面量"过滤会把 163 格全部跳过（fleet 里内部件版本确实都在 properties 里集中写）。
    props = dict(re.findall(r"<([a-zA-Z0-9_.-]+)>([^<${]+)</\1>", pom))
    out = []
    for m in re.finditer(r"<dependency>(.*?)</dependency>", pom, re.S):
        b = m.group(1)
        g = re.search(r"<groupId>([^<]+)</groupId>", b)
        a = re.search(r"<artifactId>([^<]+)</artifactId>", b)
        v = re.search(r"<version>([^<]+)</version>", b)
        if not (g and a and v):
            continue
        if g.group(1).strip() != "io.github.yuku123":
            continue
        ver = v.group(1).strip()
        ref = re.fullmatch(r"\$\{([^}]+)\}", ver)
        if ref:
            ver = props.get(ref.group(1))
            if not ver:
                out.append((g.group(1).strip(), a.group(1).strip(), f"悬空${ref.group(1)}"))
                continue
        out.append((g.group(1).strip(), a.group(1).strip(), ver))
    return sorted(set(out)), None


def repo_literal_coords(root, repo):
    base = os.path.join(root, repo)
    out = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in ("target", "node_modules", ".git", "_doc")]
        if "pom.xml" not in filenames:
            continue
        path = os.path.join(dirpath, "pom.xml")
        pom = strip_comment(open(path, encoding="utf-8").read())
        body = re.sub(r"<dependencyManagement>.*?</dependencyManagement>", "", pom, flags=re.S)
        for m in re.finditer(r"<dependency>(.*?)</dependency>", body, re.S):
            b = m.group(1)
            g = re.search(r"<groupId>([^<]+)</groupId>", b)
            a = re.search(r"<artifactId>([^<]+)</artifactId>", b)
            v = re.search(r"<version>([^<]+)</version>", b)
            if not (g and a and v):
                continue
            if g.group(1).strip() != "io.github.yuku123" or a.group(1).strip() == "z-util-all":
                continue
            ver = v.group(1).strip()
            if ver.startswith("${"):
                continue
            out.append((g.group(1).strip(), a.group(1).strip(), ver, os.path.relpath(path, root)))
    return sorted(set(out))


def all_repos(root):
    out = []
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if name.startswith((".", "_")) or not os.path.isdir(p):
            continue
        if os.path.exists(os.path.join(p, "pom.xml")):
            out.append(name)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.getcwd(), help="工作区根（默认当前目录）")
    ap.add_argument("--repo", action="append", default=[], help="额外检查该仓 pom 里写死的内部件版本，可重复")
    ap.add_argument("--literals-all", action="store_true",
                    help="不探网络：逐仓统计内部件依赖写了字面版本的处数（迁移时要删的那些）")

    ap.add_argument("--quiet", action="store_true", help="只印结论行")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    if args.literals_all:
        total = 0
        for r in all_repos(args.root):
            hits = repo_literal_coords(args.root, r)
            own = [h for h in hits if not h[1].startswith(r + "-") or True]
            if own:
                total += len(own)
                print(f"{r}: 字面内部件版本 {len(own)} 处")
                for g, a, v, path in own[:8]:
                    print(f"    {a}:{v}  @ {path}")
        print(f"\n合计 {total} 处（字面 <version> 优先级高于任何 DM，fleet 顶不住它 ⇒ 迁移逐仓删干净）")
        return 0

    coords, notes = fleet_coords(args.root)
    if notes:
        print(notes, file=sys.stderr)
    literal = []
    for r in args.repo:
        literal += repo_literal_coords(args.root, r)

    todo = sorted({c[:3] for c in coords} | {c[:3] for c in literal})
    print(f"fleet 内部件 {len(coords)} 格；"
          + ("；".join(f"{r} 字面格 {sum(1 for c in literal if c[3].startswith(r + '/'))} 处" for r in args.repo) or "未指定 --repo"))
    print(f"待探测唯一坐标 {len(todo)} 个\n")

    bad = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(probe, todo))
    for (g, a, v), verdict, chain in results:
        if verdict != "SELF_CONTAINED":
            bad.setdefault(verdict, []).append(((g, a, v), chain))
            if not args.quiet:
                print(f"{verdict:26} {g}:{a}:{v}")
                for step in chain:
                    print(f"        {step}")

    ok = len(todo) - sum(len(x) for x in bad.values())
    print(f"\n结论：{ok}/{len(todo)} 读得通；问题格 {len(todo) - ok} 个")
    for verdict, items in sorted(bad.items()):
        print(f"  {verdict} × {len(items)}: " + ", ".join(f"{a}:{v}" for (_, a, v), _ in items[:12])
              + (" …" if len(items) > 12 else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
