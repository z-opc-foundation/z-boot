#!/usr/bin/env python3
"""repo1_census.py — 数一个仓在 Central 上到底有没有发布成功：逐坐标点 4 件套。

为什么要有它：`BUILD SUCCESS` 只说明 mvn 侧跑完了，件有没有真落到 repo1 是另一件事，
而这两件事的判据不一样 —— 踩过的那次是 z-boot 1.0.19"半发"：20 个集成 starter 停在 1.0.18，
因为它们的 pom 按字面版本 import `z-boot-fleet:1.0.0`，而 fleet 从来没上过 Central。
本机 `~/.m2` 里有本地 install，所以 `mvn` 一切正常；只有干净机器才炸。

坐标清单**机械取自磁盘 pom 的 active `<module>`**（按 Maven 口径递归，被 XML 注释掉的模块
天然不算 —— 靠 grep 判断在不在 reactor 里会误报，见 central_pom_scan.py 的同款坑）。
默认只点 repo1，**不回退本地 `~/.m2`**：本地装过不等于对外可见。

用法：
    python3 _doc/003_script/repo1_census.py                    # 只点 z-boot 自己的 29 个坐标
    python3 _doc/003_script/repo1_census.py --repo ../z-cache  # 点任意一个仓（按它的 reactor  enumerates）
    python3 _doc/003_script/repo1_census.py --repo ../z-mq --quiet   # 只报缺的
退出码：0=全部可见，1=有点不到的件，2=清单本身取不出来（pom 解析不了 / 版本解析不出）。
"""
import argparse
import concurrent.futures as cf
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

NS = "{http://maven.apache.org/POM/4.0.0}"
BASE = "https://repo1.maven.org/maven2/"


def art_text(p):
    return re.sub(r"<!--.*?-->", "", open(p, encoding="utf-8").read(), flags=re.S)


def props_of(root):
    out = {}
    e = root.find(NS + "properties")
    if e is not None:
        for c in e:
            out[c.tag.replace(NS, "")] = (c.text or "").strip()
    return out


def resolve(version, props):
    """把 ${...} 按 properties 链解掉；解不动就返回 None（宁可判 2，也不发一个假坐标去探）。"""
    if version is None:
        return None
    for _ in range(6):
        m = re.search(r"\$\{([^}]+)\}", version)
        if not m:
            return version
        val = props.get(m.group(1))
        if val is None:
            return None
        version = version.replace(m.group(0), val)
    return version if "${" not in version else None


def coord(pom, inherited_version, inherited_group, parent_props):
    try:
        root = ET.fromstring(art_text(pom))
    except ET.ParseError as exc:
        sys.exit(f"✗ {pom} 解析不了：{exc}")
    props = dict(parent_props)
    props.update(props_of(root))
    par = root.find(NS + "parent")
    aid = root.findtext(NS + "artifactId", "").strip()
    # groupId / version 都可以不写而从 <parent> 继承 —— 漏了这一步会拼出 "…//artifact/ver/"
    # 这种半空路径，repo1 一律 404，看着像"没发布"其实是脚本自己没算出坐标。
    gid = root.findtext(NS + "groupId") or (par.findtext(NS + "groupId") if par is not None else None) \
        or inherited_group
    ver = root.findtext(NS + "version") or (par.findtext(NS + "version") if par is not None else None) \
        or inherited_version
    pk = root.findtext(NS + "packaging", "jar").strip()
    return aid, (gid or "").strip(), resolve(ver, props), pk, props


def walk(pom, gid=None, ver=None, props=None):
    """(artifactId, groupId, version, packaging) 列表：自身 + active <module> 递归。"""
    self_aid, my_gid, my_ver, pk, my_props = coord(pom, ver, gid, props or {})
    out = [(self_aid, my_gid, my_ver, pk)] if self_aid else []
    base = os.path.dirname(pom)
    r = ET.fromstring(art_text(pom))
    mods = r.find(NS + "modules")
    for m in (list(mods) if mods is not None else []):
        name = (m.text or "").strip()
        if not name:
            continue
        child = os.path.join(base, name, "pom.xml")
        if not os.path.isfile(child):
            continue
        out += walk(child, my_gid, my_ver, my_props)
    return out


def independent_folders(root_pom):
    """根 pom 没有 <modules> 时的补集：z-boot 1.0.19 那种"根只是发布用 parent、
    五个文件夹各自独立成工程"的拓扑，按 Maven 口径递归是走不到的（中央也找不到）。
    只看**顶层**子目录，所以集成 starter 聚合里被注释掉的那个 webide starter 不会被捞进来。"""
    base = os.path.dirname(root_pom)
    out = []
    for d in sorted(os.listdir(base)):
        p = os.path.join(base, d, "pom.xml")
        if os.path.isdir(os.path.join(base, d)) and os.path.isfile(p):
            out.append(p)
    return out


def probe(aid, gid, ver, pk):
    """ranged GET：repo1(Fastly) 对 HEAD 一律不回 200，用 HEAD 量会把已发布成功的判成取不到。"""
    path = f"{gid.replace('.', '/')}/{aid}/{ver}/"
    items = [f"{aid}-{ver}.pom"]
    if pk != "pom":
        items += [f"{aid}-{ver}.jar", f"{aid}-{ver}-sources.jar", f"{aid}-{ver}-javadoc.jar"]
    miss = []
    for f in items:
        code = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                               "-r", "0-0", "--max-time", "30", BASE + path + f],
                              capture_output=True, text=True).stdout.strip()
        if code not in ("200", "206"):
            miss.append(f"{f}({code})")
    return miss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.path.join(os.path.dirname(__file__), "..", ".."),
                    help="仓根目录（默认 z-boot 自己）")
    ap.add_argument("--quiet", action="store_true", help="只报点不到的")
    a = ap.parse_args()
    root_pom = os.path.join(a.repo, "pom.xml")
    if not os.path.isfile(root_pom):
        sys.exit(f"✗ 找不到 {root_pom}")

    seen, coords = set(), []
    todo = [root_pom]
    r = ET.fromstring(art_text(root_pom))
    if r.find(NS + "modules") is None:
        todo += independent_folders(root_pom)
    for pom in todo:
        for aid, gid, ver, pk in walk(pom):
            if not ver:
                sys.exit(f"✗ {aid} 的版本解析不出来（property 不在父链上？这种坐标不能拿去探 repo1）")
            if (gid, aid, ver) not in seen:
                seen.add((gid, aid, ver))
                coords.append((aid, gid, ver, pk))
    if not coords:
        sys.exit("✗ 清单为空")

    with cf.ThreadPoolExecutor(16) as ex:
        res = list(ex.map(lambda c: (c, probe(c[0], c[1], c[2], c[3])), coords))

    bad = 0
    for (aid, gid, ver, pk), miss in sorted(res):
        if miss:
            bad += 1
            print(f"  ✗ {gid}:{aid}:{ver}  缺 {', '.join(miss)}")
        elif not a.quiet:
            print(f"  ✅ {aid}-{ver}  {'pom' if pk == 'pom' else 'pom+jar+sources+javadoc'} 齐")
    files = sum(1 if pk == "pom" else 4 for _, _, _, pk in coords)
    print(f"\n坐标 {len(coords)} 个 / 应有点件 {files} 件 / 缺件坐标 {bad} 个"
          f"   (repo1 only，不看 ~/.m2)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
