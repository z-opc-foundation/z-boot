#!/usr/bin/env python3
"""
publish_bump_check.py — 判"这一版号还能不能发"，发版批量决策前必须先看它。

为什么需要它：Central 不可覆盖。仓迁到 z-boot-parent 后，构建口径变了 ⇒ flatten 出来的
对外 pom 里那批依赖面值会跟着地板/ fleet 一起动（z-msg 那一刀实测 z-util-core 1.0.10→1.0.13、
z-boot starter 1.0.17→1.0.19、jackson 2.13.5→2.18.6）。中央上 1.2.1 那个 pom 已经写死，
重发同号必被拒 ⇒ **迁过的仓在发中央之前都要先按这份报告决定抬不抬号**。只看号在不在中央
（repo1_census 那种 ranged GET）判不出这件事：号在、但 pom 内容已经不一样了才是要命的。

口径：
  · 只认盘上的 `.flattened-pom.xml`（= 上一次真构建产物的对外形状），不认 pom.xml 本身；
    所以跑之前那仓至少 `package` 过一遍，否则报"无 flatten"。
  · 逐件按 Maven 的坐标 (g:a:v) 去 repo1 取**全文** pom 比对依赖集合，不是 ranged GET
    （ranged GET 只拿 1 字节，比对不了内容 —— 这是踩过的坑）。
  · 中央 404 ⇒ NEW（首次发布，不需要抬号）；200 且依赖集合逐字相同 ⇒ SAME；
    200 但有出入 ⇒ BUMP（同号发不出去，必须抬号或确认不发）。
  · **形状差单列**：叶子 pom 自己带不带 `<parent>` 是一等事实。带 parent 的那族，
    版本的 `(none)` 是"由父 pom 的 DM 补"，不是缺陷；迁移把 flatten 换成 `oss` 会顺手
    把 parent 剥掉、版本写死 ⇒ 那是**换发布形状**（判成 SHAPE），与"面值漂了"（BUMP）
    是两件事。SHAPE 同号也发不动，但它的解法有两条（抬号 / 把 flatten 改回原形状），
    而 BUMP 只有一条 ⇒ 混在一起会得出"必须抬 16 仓的号"这种过强的结论。
  · excludeArtifacts（central-publishing 那段）里的件不算：它们本来就不发。

只读，不写任何东西、不碰 ~/.m2。

用法：
  python3 z-boot/_doc/003_script/publish_bump_check.py --repo z-msg
  python3 z-boot/_doc/003_script/publish_bump_check.py            # 扫所有 parent=z-boot-parent 的仓
  python3 z-boot/_doc/003_script/publish_bump_check.py --quiet     # 只印每仓结论行
"""
import os
import sys
import glob
import time
import argparse
import urllib.request
import xml.etree.ElementTree as ET

NS = "{http://maven.apache.org/POM/4.0.0}"
ZBOOT = os.path.dirname(os.path.abspath(__file__))
FOUNDATION = os.path.abspath(os.path.join(ZBOOT, "..", "..", ".."))
REPO1 = "https://repo1.maven.org/maven2"


def q(t):
    return t.text.strip() if t is not None and t.text else None


def has_parent(root):
    """发布形状的一等事实：叶子 pom 自己带不带 <parent>。
    带 parent 的族（z-oss / z-skill 那一类）中央那份叶子是**靠 parent 的 DM 补版本**的，
    所以它的 dependency 看起来"没有 version"不是缺陷；flatten 换成 oss 会把 parent 剥掉、
    同时把版本写死 ⇒ 那是**换发布形状**，与"版本漂了"是两件事，要分开报。"""
    return root.find(NS + "parent") is not None


def coord_of(root):
    g = a = v = None
    p = root.find(NS + "parent")
    pg, pa, pv = (q(p.find(NS + x)) for x in ("groupId", "artifactId", "version")) if p is not None else (None,) * 3
    g = q(root.find(NS + "groupId")) or pg
    a = q(root.find(NS + "artifactId"))
    v = q(root.find(NS + "version")) or pv
    return g, a, v


def deps(root):
    """只收 <dependencies> 里的依赖，跳过 <dependencyManagement> 里的条目（两者同名不同职）。
    DM 单独一份：BOM 型发布件对外供的就是它，混在一起会把"删了个版本属性"算成依赖变动。
    (g, a, version, scope) 四元组；<exclusions> 不参与比对（不改对外版本）。"""
    out, dm = set(), set()

    def walk(e, inside_dm):
        for ch in e:
            tag = ch.tag.replace(NS, "")
            if tag == "dependencyManagement":
                walk(ch, True)
                continue
            if tag == "dependency":
                tgt = dm if inside_dm else out
                tgt.add((q(ch.find(NS + "groupId")), q(ch.find(NS + "artifactId")),
                         q(ch.find(NS + "version")) or "(none)", q(ch.find(NS + "scope")) or "compile"))
                continue
            walk(ch, inside_dm)

    # 只从 <project> 直属的 <dependencies> 走，profile 里的先不管（发布形状由 active profile 决定）
    for ch in root:
        tag = ch.tag.replace(NS, "")
        if tag == "dependencyManagement":
            walk(ch, True)
        elif tag == "dependencies":
            walk(ch, False)
    return out, dm


def excluded(root_pom_text):
    """central-publishing-maven-plugin 的 <excludeArtifacts> 清单（不发中央的那些件）。"""
    ex = set()
    try:
        root = ET.fromstring(root_pom_text)
    except ET.ParseError:
        return ex
    for pl in root.iter(NS + "plugin"):
        if q(pl.find(NS + "artifactId")) != "central-publishing-maven-plugin":
            continue
        cfg = pl.find(NS + "configuration")
        if cfg is None:
            continue
        for e in cfg.iter(NS + "excludeArtifacts"):
            for x in e.findall(NS + "excludeArtifact"):
                if q(x):
                    ex.add(q(x))
    return ex


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "publish-bump-check/1"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def report(repo, quiet):
    rp = os.path.join(repo, "pom.xml")
    if not os.path.isfile(rp):
        return
    text = open(rp, encoding="utf-8").read()
    try:
        rroot = ET.fromstring(text)
    except ET.ParseError:
        print(f"{os.path.basename(repo)}: 根 pom 解析失败，跳过")
        return
    p = rroot.find(NS + "parent")
    pname = (q(p.find(NS + "artifactId")) if p is not None else None) or "NONE"
    flat = sorted(glob.glob(os.path.join(repo, "**", ".flattened-pom.xml"), recursive=True))
    ex = excluded(text)
    if not flat:
        print(f"{os.path.basename(repo):<15} parent={pname:<16} 盘上无 .flattened-pom.xml ⇒ 没跑过构建，判不了（先 package 一遍）")
        return
    rows, counts = [], {"NEW": 0, "SAME": 0, "BUMP": 0, "SHAPE": 0, "SKIP": 0, "UNREAD": 0, "UNPARSED": 0}
    for f in flat:
        try:
            loc = ET.parse(f).getroot()
        except ET.ParseError:
            counts["UNPARSED"] += 1
            continue
        g, a, v = coord_of(loc)
        if a is None:
            counts["UNPARSED"] += 1
            continue
        if a in ex:
            counts["SKIP"] += 1
            continue
        url = f"{REPO1}/{g.replace('.', '/')}/{a}/{v}/{a}-{v}.pom"
        code, body = fetch(url)
        local_parent = has_parent(loc)
        if code == 404:
            verdict, detail = "NEW", "" if local_parent else "(自包含形状)"
        elif code != 200:
            verdict, detail = "UNREAD", f"(取不到 central 那份：HTTP {code} ⇒ 不可判，别当 SAME)"
        else:
            try:
                pub_root = ET.fromstring(body)
                pub, pub_dm = deps(pub_root)
            except ET.ParseError:
                verdict, detail = "BUMP", "中央那份 pom 解析不了"
            else:
                l, l_dm = deps(loc)
                # 带 parent 的叶子靠父 pom 的 DM 补版本，打印出来就是 "(none)" —— 那是形状，不是缺陷
                shape_shift = has_parent(pub_root) != local_parent
                if l == pub and l_dm == pub_dm and not shape_shift:
                    verdict, detail = "SAME", ""
                else:
                    # 按 (g,a,scope) 归并版本：一个坐标可能出现多次（不同 scope），逐个 scope 比
                    def moves(P, L):
                        def keyed(s):
                            d = {}
                            for (g_, a_, v_, sc_) in s:
                                d.setdefault((g_, a_, sc_), set()).add(v_)
                            return d
                        Pk, Lk = keyed(P), keyed(L)
                        drift, shape = [], []
                        for k in sorted(set(Pk) | set(Lk)):
                            pv, lv = Pk.get(k, set()), Lk.get(k, set())
                            if pv == lv:
                                continue
                            g_, a_, sc_ = k
                            sfx = f'@{sc_}' if sc_ != 'compile' else ''
                            if shape_shift and ("(none)" in pv or "(none)" in lv):
                                shape.append(f"{g_}:{a_}{sfx}")
                                continue
                            if pv and lv:
                                drift.append(f"{g_}:{a_}{sfx} {'/'.join(sorted(pv))}→{'/'.join(sorted(lv))}")
                            elif lv:
                                drift.append(f"+{g_}:{a_}{sfx} {'/'.join(sorted(lv))}")
                            else:
                                drift.append(f"-{g_}:{a_}{sfx} {'/'.join(sorted(pv))}")
                        return drift, shape
                    dm_mv, dm_sh = moves(pub_dm, l_dm)
                    dep_mv, dep_sh = moves(pub, l)
                    n_shape = len(dm_sh) + len(dep_sh)
                    parts = ([f"依赖{len(dep_mv)}格: " + "; ".join(dep_mv[:5])] if dep_mv else []) + \
                            ([f"DM{len(dm_mv)}格: " + "; ".join(dm_mv[:5])] if dm_mv else [])
                    if not parts and shape_shift:
                        # 只有形状差：对外面值没漂，但发出去的那份 pom 与中央同号那份不是同一个东西 ⇒ 一样得抬号
                        verdict, detail = "SHAPE", (f"中央那份{'带' if has_parent(pub_root) else '不带'}<parent>，本地 flatten "
                                                    f"{'带' if local_parent else '不带'} ⇒ 换发布形状（{n_shape} 格版本由 parent 补）")
                    else:
                        verdict, detail = "BUMP", " ｜ ".join(parts) + \
                            (f" …(+{n_shape} 格形状差)" if shape_shift and n_shape > 5 else
                             (" ｜ 另有形状差" if shape_shift else "")) + \
                            (" …" if len(dep_mv) > 5 or len(dm_mv) > 5 else "")
        counts[verdict] = counts.get(verdict, 0) + 1
        rows.append((verdict, f"{g}:{a}:{v}", detail))
        time.sleep(0.05)
    name = os.path.basename(repo)
    tag = f"parent={pname}"
    if quiet:
        line = f"{name:<15} {tag:<26} " + " ".join(f"{k}={counts[k]}" for k in ("NEW", "SAME", "BUMP", "SHAPE", "SKIP", "UNREAD") if counts.get(k))
        if counts.get("BUMP"):
            line += "   ⚠ 面值漂了，同号发不动，必须抬 revision"
        elif counts.get("SHAPE"):
            line += "   ⚠ 只有发布形状差：抬号，或把 flatten 形状改回中央那一版的样子"
        print(line)
    else:
        print(f"\n=== {name}  {tag}  flatten 件 {len(flat)} 个 ===")
        for verdict, c, detail in rows:
            print(f"  {verdict:<5} {c:<58} {detail}")
        print(f"  小结: " + " ".join(f"{k}={counts[k]}" for k in sorted(counts) if counts[k]))
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", action="append", help="仓目录名（相对 foundation 根），可多次；不给就扫 parent=z-boot-parent 的全部")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    if a.repo:
        targets = [os.path.join(FOUNDATION, r) for r in a.repo]
    else:
        targets = []
        for d in sorted(os.listdir(FOUNDATION)):
            rp = os.path.join(FOUNDATION, d, "pom.xml")
            if not os.path.isfile(rp):
                continue
            try:
                root = ET.parse(rp).getroot()
            except ET.ParseError:
                continue
            p = root.find(NS + "parent")
            if p is not None and q(p.find(NS + "artifactId")) == "z-boot-parent":
                targets.append(os.path.join(FOUNDATION, d))
    tot = {}
    for t in targets:
        r = report(t, a.quiet)
        if r:
            for k, v in r.items():
                tot[k] = tot.get(k, 0) + v
    print(f"\n合计 {len(targets)} 仓：" + " ".join(f"{k}={tot.get(k,0)}" for k in ("NEW", "SAME", "BUMP", "SHAPE", "SKIP", "UNREAD", "UNPARSED")))
    if tot.get("BUMP"):
        print("⚠ 有件的对外 pom 与中央同号那份**面值不同** ⇒ 批量发布前逐仓决定抬号；不抬就发不出去。")
    if tot.get("SHAPE") and not tot.get("BUMP"):
        print("⚠ 只有发布形状差（叶子带不带 <parent>）⇒ 可以不改号，但要把 flatten 配置还原成中央那一版的样子。")


if __name__ == "__main__":
    main()
