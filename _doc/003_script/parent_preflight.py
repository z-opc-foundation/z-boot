#!/usr/bin/env python3
"""parent_preflight.py — 把某仓迁入 z-boot-parent 之前，先把它现在"靠旧 parent 借到什么"量清楚。

为什么要有它：换 parent 不是改一行 —— 旧 parent（`com.zifang:z-opc:1.0.0-SNAPSHOT` 这类只在本机
~/.m2 里的 pom）通过 properties / dependencyManagement 悄悄供给这个仓的一切。悬空的那格
`${compile.version}` 就是实测案例：z-cache 引用它、自己没定义、旧父链里也没有，而 javadoc 插件挂着
`failOnError=false` 把炸点吞了，所以这处点伤一路没人看见。靠眼睛对 36 个仓对不完，所以量。

报四类，全是"改完会不会变味"的前置事实：
  1 悬空属性      —— pom 里 `${x}` 引用了，但本仓 properties + 新父链（parent→floor→fleet）都没有
  2 版本键        —— 本仓自己钉的版本键里，哪些与 floor/fleet 面值**相同**（可删）、
                    哪些**不同**（是刻意的分歧，必须留且要按坐标写直接 DM 才顶得住）
  3 自家模块      —— 仓内 reactor 的 jar 模块清单（迁移后要在本仓 DM 里钉 ${project.version}，
                    否则继承来的 fleet 面值会改写**传递依赖**版本，shade 包会打进旧字节码）
  4 BOM import    —— 现有哪些 import；floor/parent 已经供给同一坐标的话，重复 import 是 dm 打架的来源

用法：
    python3 _doc/003_script/parent_preflight.py --repo ../z-cache
    python3 _doc/003_script/parent_preflight.py --all          # 逐仓报摘要（../ 下所有带 pom.xml 的目录）
退出码：0=量到了（不代表可以迁），2=量不出来（pom 解析不了 / 找不到 BOM）。
"""
import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET

NS = "{http://maven.apache.org/POM/4.0.0}"
HERE = os.path.dirname(os.path.abspath(__file__))
ZBOOT = os.path.abspath(os.path.join(HERE, "..", ".."))
# Maven 自己的内置属性 + JDK/环境属性：这些不该被当成"悬空的仓内属性"
BUILTIN = re.compile(r"^(project\.|pom\.|settings\.|java\.|os\.|maven\.|basedir|file\.separator|"
                     r"path\.separator|line\.separator|exec\.executable|env\.)")


def strip(p):
    return re.sub(r"<!--.*?-->", "", open(p, encoding="utf-8").read(), flags=re.S)


def load(path):
    try:
        return ET.fromstring(strip(path))
    except ET.ParseError as exc:
        sys.exit(f"✗ {path} 解析不了：{exc}")


def props(root):
    """项目级 properties + 各 profile 里的 properties。
    只读项目级会把 `<profiles><profile><properties>` 里定义的键（central.gpg.skip 这类）
    误报成悬空 —— 第一版就是这么假红了 z-mq 一格。"""
    out = {}
    e = root.find(NS + "properties")
    if e is not None:
        out.update({c.tag.replace(NS, ""): (c.text or "").strip() for c in e})
    pf = root.find(NS + "profiles")
    for p in (list(pf) if pf is not None else []):
        pe = p.find(NS + "properties")
        if pe is not None:
            out.update({c.tag.replace(NS, ""): (c.text or "").strip() for c in pe})
    return out


def all_poms(repo):
    out = []
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in ("target", "node_modules", ".git", "src", "_frontend", "bin")]
        if "pom.xml" in filenames:
            out.append(os.path.join(dirpath, "pom.xml"))
    return sorted(out)


def bom_supplied():
    """新父链能给什么：parent 自己的 properties + floor/fleet 的 properties 与 DM 面值。
    面值按各 BOM **自己**的 properties 解（Maven 就是这么插值的：父 pom 的 ${x} 用父的 x）。"""
    supply_props, supply_dm = {}, {}
    for rel in (f"z-boot-parent/pom.xml", "z-boot-dependencies/pom.xml", "z-boot-fleet/pom.xml"):
        p = os.path.join(ZBOOT, rel)
        if not os.path.isfile(p):
            sys.exit(f"✗ 找不到 {p} —— 先在 z-boot 里把三个 pom 算出来再跑本尺")
        r = load(p)
        pr = props(r)
        supply_props.update({k: v for k, v in pr.items() if k not in supply_props})
        dm = r.find(NS + "dependencyManagement")
        if dm is not None:
            for d in dm.find(NS + "dependencies"):
                a = d.findtext(NS + "artifactId", "")
                v = d.findtext(NS + "version", "")
                for _ in range(6):
                    m = re.search(r"\$\{([^}]+)\}", v)
                    if not m:
                        break
                    if m.group(1) in pr:
                        v = v.replace(m.group(0), pr[m.group(1)])
                    else:
                        v = "?"
                supply_dm.setdefault(a, (d.findtext(NS + "groupId", ""), v,
                                         d.findtext(NS + "scope", "") or "-"))
    return supply_props, supply_dm


def repo_modules(repo):
    """仓内 reactor 的坐标（根 + 各 active <module>，注释掉的天然不算）。"""
    root = load(os.path.join(repo, "pom.xml"))
    arts = [root.findtext(NS + "artifactId", "").strip()]
    mods = root.find(NS + "modules")
    for m in (list(mods) if mods is not None else []):
        name = (m.text or "").strip()
        p = os.path.join(repo, name, "pom.xml")
        if os.path.isfile(p):
            arts.append(load(p).findtext(NS + "artifactId", "").strip())
    return [a for a in arts if a]


def ref_sites(repo, poms, keys, supply_dm, supply_props):
    """每个 ${key} 到底挂在哪些坐标上 —— 只按**键名**判"父链供不供"会误判：
    z-vector 的 zutil.version 被报成"父链没供给"，可 fleet 其实管着 z-util-core/math/ml 三格
    且面值同为 1.0.13 ⇒ 正确动作是"删键 + 连带删掉这 4 处 <version>"，不是留着键自己钉。
    反过来 protobuf-java-util 父链真的不管 ⇒ 删键当场悬空。两种情况在报表里必须长得不一样，
    否则派出去的代理就会只删键不删引用（本仓实测坏过一次，mvn validate rc=1）。"""
    out = {}
    for p in poms:
        rel = os.path.relpath(p, repo)
        try:
            r = load(p)
        except Exception:
            continue
        for tag in ("dependency", "plugin"):
            for d in r.iter(NS + tag):
                v = (d.findtext(NS + "version", "") or "").strip()
                m = re.fullmatch(r"\$\{([^}]+)\}", v)
                if not m or m.group(1) not in keys:
                    continue
                gid = d.findtext(NS + "groupId", "") or "(继承)"
                aid = d.findtext(NS + "artifactId", "")
                out.setdefault(m.group(1), []).append((rel, f"{gid}:{aid}", tag))
    return out


def report(repo, supply_props, supply_dm):
    poms = all_poms(repo)
    root = load(os.path.join(repo, "pom.xml"))
    own = props(root)
    for p in poms[1:]:
        own.update({k: v for k, v in props(load(p)).items() if k not in own})
    used = {}
    for p in poms:
        for key in re.findall(r"\$\{([^}]+)\}", strip(p)):
            used.setdefault(key.strip(), set()).add(os.path.relpath(p, repo))
    dangling = {k: v for k, v in used.items()
                if not BUILTIN.match(k) and k not in own and k not in supply_props
                and k not in ("revision", "sha1", "changelist")}
    version_keys = {k: v for k, v in own.items() if k.endswith(".version")
                    and not k.startswith(("project.", "flatten."))}
    same, differ, missing = [], [], []
    for k, v in sorted(version_keys.items()):
        # 先按**同名 property** 比（父链就是这么供的：floor 里 netty.version=4.1.138.Final），
        # 再退一步按 DM 里同名坐标比（fleet 的 z-* 格是 property+坐标成对的）。
        # 早先用"artifactId = 键去掉 .version"去查 DM，会把 maven-compiler-plugin.version
        # 这种插件版本键拿去跟一条不相干的 DM 比，报出假分歧。
        pv = supply_props.get(k)
        art = k[: -len(".version")]
        dv = supply_dm.get(art, ("", None, ""))[1] if pv is None else None
        ref = pv if pv is not None else dv
        if ref is None:
            missing.append((k, v))
        elif ref == v:
            same.append((k, v, ref))
        else:
            differ.append((k, v, ref))

    dm = root.find(NS + "dependencyManagement")
    imports = []
    if dm is not None:
        for d in dm.find(NS + "dependencies"):
            if d.findtext(NS + "scope", "") == "import":
                imports.append(f"{d.findtext(NS + 'groupId')}:{d.findtext(NS + 'artifactId')}"
                               f":{d.findtext(NS + 'version')}")
    par = root.find(NS + "parent")
    ptxt = "(无 parent)" if par is None else \
        f"{par.findtext(NS + 'groupId')}:{par.findtext(NS + 'artifactId')}:{par.findtext(NS + 'version')}"
    rp = root.find(NS + "relativePath")
    rp_txt = "" if rp is None else (f" relativePath={rp.text or '(空)'}"
                                   + (" ⇒ 指向不存在的路径" if rp.text and
                                      not os.path.isfile(os.path.join(repo, rp.text)) else ""))

    print(f"\n{'='*72}\n{os.path.basename(repo)}   parent: {ptxt}{rp_txt}")
    print(f"  pom 数 {len(poms)} / 版本键 {len(version_keys)} / reactor 模块 {len(repo_modules(repo))} 个")
    if dangling:
        print("  ⚠ 1 悬空属性（新父链也补不上，迁移前必须处理）：")
        for k, v in sorted(dangling.items()):
            print(f"      ${{{k}}}  ← {', '.join(sorted(v))}")
    else:
        print("  ✓ 1 悬空属性 0 个")
    print("  · 2 与父链同值（可删，改由 parent 下发）：" + (", ".join(f"{k}={v}" for k, v, _ in same) or "无"))
    print("  ⚠ 2 与父链**不同值**（刻意的分歧：删掉就换味，且 import 顶不住继承来的直接 DM，"
          "要按坐标写直接条目）："
          + (", ".join(f"{k}: 本仓 {v} vs 父链 {s}" for k, v, s in differ) or "无"))
    print("  · 2 父链没供给、必须自己留着的键：" + (", ".join(f"{k}={v}" for k, v in missing) or "无"))
    print("  · 3 迁移后要在本仓 DM 钉 ${project.version} 的自家坐标："
          + ", ".join(repo_modules(repo)))
    print("  · 4 现存 BOM import：" + ("; ".join(imports) or "无"))
    watch = {k for k, _ in missing} | {k for k, _, _ in same} | {k for k, _, _ in differ}
    sites = ref_sites(repo, poms, watch, supply_dm, supply_props)
    hang = [(k, f, c, t) for k, lst in sites.items() for f, c, t in lst if k in dict(missing)]
    if hang:
        print("  ⚠ 5 挂在「父链没供给的键」上的 <version> 引用点（删键必须连带处理每一处）：")
        for k, f, c, t in sorted(hang):
            dv = supply_dm.get(c.split(":")[-1], ("", None, ""))[1]
            own_v = dict(version_keys).get(k, "")
            verdict = (f"父链按坐标供 {dv}" + ("（同值：删掉这行即可）" if dv == own_v else "（不同值！）")
                       if dv else "父链不供这个坐标：留着键，或改成字面量")
            print(f"      ${{{k}}}  {c}  ← {f} [{t}]  ⇒ {verdict}")
    sup = [(k, f, c, t) for k, lst in sites.items() for f, c, t in lst if k in {x for x, _, _ in same}]
    if sup:
        print("  · 5 挂在「同值可删键」上的引用点：" + "; ".join(
            f"${{{k}}}×{sum(1 for x, _, _, _ in sup if x == k)}处({','.join(sorted({f for kk, f, _, _ in sup if kk == k}))})"
            for k in sorted({k for k, _, _, _ in sup})))
    return len(dangling), len(differ)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo")
    ap.add_argument("repos", nargs="*", help="仓目录名，等价于 --repo，可一次给多个")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    supply_props, supply_dm = bom_supplied()
    print(f"新父链供给：properties {len(supply_props)} 个 / DM 面值 {len(supply_dm)} 条（按各 BOM 自身属性解出）")
    foundation = os.path.abspath(os.path.join(ZBOOT, ".."))
    picked = ([a.repo] if a.repo else []) + list(a.repos)
    if a.all:
        targets = [os.path.join(foundation, d) for d in sorted(os.listdir(foundation))
                   if os.path.isfile(os.path.join(foundation, d, "pom.xml"))]
    elif picked:
        targets = [os.path.abspath(p) for p in picked]
    else:
        ap.error("要 --repo <路径> / 直接给仓名 / --all")
    tot_d = tot_v = 0
    for t in targets:
        d, v = report(t, supply_props, supply_dm)
        tot_d += d
        tot_v += v
    print(f"\n合计：{len(targets)} 个仓 / 悬空属性 {tot_d} 格 / 与父链不同值的版本键 {tot_v} 格")


if __name__ == "__main__":
    main()
