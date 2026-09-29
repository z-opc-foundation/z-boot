#!/usr/bin/env python3
"""phantom_dep_census.py —— 数"只存在于本机 ~/.m2 的跨仓 com.zifang 依赖"，并分桶到能动手的粒度。

为什么另起一个量具（现成的三个都覆盖不到这一层）：
  · `central_chain_probe` 走 `<parent>` 链，`repo1_census` 数坐标在不在，
    `published_graph_audit` 查**发布 pom** 的兄弟依赖边 —— 三者看的都是"中央"，
    而幻影坐标的特征恰恰是**中央没有、本机却有**：盘上的仓照样绿，换台机器当场红。
  · `~/.m2/repository/com/zifang/` 现 285 个目录，全是指向陈旧 1.0.0-SNAPSHOT 的安装件，
    它把这笔账遮得死死的 —— 所以这个量具不查中央，只查**盘上 pom 的依赖声明**。

三个必须做对的口径（每一个都对应一次假报警）：
  1. **先剥 XML 注释**。这些 pom 的注释里反复出现 `com.zifang:...1.0.0-SNAPSHOT` 这种坐标字样，
     不剥就会把"记录幻影的说明文字"数成"依赖幻影的代码"（步骤 17/18 同一坑第三次复发）。
  2. **仓内坐标不算跨仓**。artifactId 只要出现在本仓 reactor（根 pom 沿 `<modules>` 递归，
     不含 target/.mvn）里，就是同仓父子格，中央本来就不需要它 —— 判定跨仓要用 reactor 集合，
     不能用 groupId 前缀（z-opc 把 z-meta/z-ext/z-team 的**副本**vendor 在自己树里，
     前缀法会把它们全数成幻影）。
  3. **真实依赖与仅 DM 登记分开数**。`<dependencyManagement>` 里的格子没人用就不解析，
     删不删都不影响构建；模块 `<dependencies>` 里那一条才是"换台机器起不来"的东西。
     混在一起的后果实测过：全组织 560 处 `com.zifang` groupId 声明里，真正会拦住建造的只有 15 处。

还报一个"有没有地方可搬"的初判：把跨仓格子的 artifactId 拿到**全组织 reactor** 里找同名件，
找得到且那个模块的 groupId 是 `io.github.yuku123` ⇒ 候选换坐标（还要人工比 jar 类集，
`z-rpc-core` 就是被类集比否掉的：旧快照 83 个 class、中央 1.0.4 只有 11 个）。找不到 ⇒ 必须先
整仓换 namespace + 首发中央（`z-task-*` / `z-agent-mcp-*` / `z-agent-llm-gateway-*` 都在这一类）。

用法：python3 z-boot/_doc/003_script/phantom_dep_census.py [--root <目录>] [--json]
退出码恒 0 —— 它是账，不是闸门。
"""
import argparse
import json
import os
import re
import sys

IGNORE_DIRS = {".git", "target", "node_modules", ".mvn", ".idea", "dist", "build"}
# z-boot 是"五个各自独立的 Maven 文件夹"，根 pom 不聚合它们 ⇒ 反应堆根要按文件夹拆开数
MULTI_ROOT_REPOS = {"z-boot": ["z-boot-dependencies", "z-boot-fleet", "z-boot-parent",
                               "z-boot-starter", "z-boot-integration-starters"]}


def strip_comments(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def modules_of(text):
    m = re.search(r"<modules>(.*?)</modules>", text, re.S)
    if not m:
        return []
    return [x.strip() for x in re.findall(r"<module>\s*([^<]+?)\s*</module>", m.group(1))]


def artifact_id(text):
    seg = text.split("</parent>", 1)[1] if "</parent>" in text else text
    m = re.search(r"<artifactId>\s*([^<]+?)\s*</artifactId>", seg)
    return m.group(1) if m else None


def read(path):
    try:
        return strip_comments(open(path, encoding="utf-8", errors="ignore").read())
    except Exception:
        return None


def reactor(root):
    """返回 (reactor 里的 artifactId 集合, {pom 路径: 文本})；只沿 <modules> 走，不算盘上散 pom。"""
    ids, poms = set(), {}

    def walk(d):
        p = os.path.join(d, "pom.xml")
        if not os.path.exists(p):
            return
        t = read(p)
        if t is None:
            return
        poms[p] = t
        a = artifact_id(t)
        if a:
            ids.add(a)
        for m in modules_of(t):
            c = os.path.normpath(os.path.join(d, m))
            if os.path.isdir(c):
                walk(c)

    walk(root)
    return ids, poms


def dm_spans(text):
    return [(m.start(), m.end()) for m in re.finditer(r"<dependencyManagement>(.*?)</dependencyManagement>", text, re.S)]


def cells(text, own_ids):
    """跨仓 com.zifang 依赖格 → (kind, artifactId, versionFace)。kind 是 hard / dm。"""
    spans = dm_spans(text)
    out = []
    for m in re.finditer(r"<dependency>(.*?)</dependency>", text, re.S):
        body = m.group(1)
        g = re.search(r"<groupId>\s*([^<]+?)\s*</groupId>", body)
        a = re.search(r"<artifactId>\s*([^<]+?)\s*</artifactId>", body)
        if not (g and a) or g.group(1) != "com.zifang":
            continue
        if a.group(1) in own_ids:
            continue
        v = re.search(r"<version>\s*([^<]+?)\s*</version>", body)
        out.append(("dm" if any(s <= m.start() < e for s, e in spans) else "hard",
                    a.group(1), v.group(1) if v else "(no version)"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/Users/zifang/workplace/ceo_workplace/z-opc-foundation")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    repos = sorted(d for d in os.listdir(args.root)
                   if os.path.isdir(os.path.join(args.root, d)) and d not in IGNORE_DIRS)
    per_repo, published_aliases = {}, set()
    for r in repos:
        roots = [os.path.join(args.root, r)]
        for sub in MULTI_ROOT_REPOS.get(r, []):
            p = os.path.join(args.root, r, sub)
            if os.path.isdir(p):
                roots.append(p)
        own, poms = set(), {}
        for rt in roots:
            ids, pm = reactor(rt)
            own |= ids
            poms.update(pm)
        if not poms:
            continue
        hard, dm = [], []
        for path, text in poms.items():
            for kind, a, v in cells(text, own):
                (hard if kind == "hard" else dm).append(
                    (os.path.relpath(path, args.root), a, v))
        per_repo[r] = {"own_modules": len(own), "hard": hard, "dm_only": dm,
                       "own_ids": sorted(own)}
        published_aliases |= own

    # "有没有地方可搬"：全组织里同名且 groupId 已是 io.github.yuku123 的 artifact
    new_ns = set()
    for r in repos:
        p = os.path.join(args.root, r, "pom.xml")
        for dirpath, dirs, files in os.walk(os.path.join(args.root, r)):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            if "pom.xml" not in files:
                continue
            t = read(os.path.join(dirpath, "pom.xml"))
            if not t:
                continue
            seg = t.split("</parent>", 1)[1] if "</parent>" in t else t
            a = artifact_id(t)
            g = re.search(r"<groupId>\s*([^<]+?)\s*</groupId>", seg)
            ns = g.group(1) if g else None
            if ns is None:
                par = re.search(r"<parent>(.*?)</parent>", t, re.S)
                ns = re.search(r"<groupId>\s*([^<]+?)\s*</groupId>", par.group(1)).group(1) if par else None
            if a and ns == "io.github.yuku123":
                new_ns.add(a)

    rows = []
    for r in repos:
        info = per_repo.get(r)
        if not info or not (info["hard"] or info["dm_only"]):
            continue
        arts_hard = sorted(set(a for _, a, _ in info["hard"]))
        rows.append({
            "repo": r,
            "modules": info["own_modules"],
            "hard_sites": len(info["hard"]),
            "hard_artifacts": arts_hard,
            "hard_flippable_candidates": sorted(a for a in arts_hard if a in new_ns),
            "dm_only_kinds": len(set(a for _, a, _ in info["dm_only"])),
            "detail": info["hard"],
        })

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    tot_h = sum(x["hard_sites"] for x in rows)
    tot_d = sum(x["dm_only_kinds"] for x in rows)
    print("跨仓 com.zifang：真实依赖 %d 处 / 仅 DM 登记 %d 种" % (tot_h, tot_d))
    for x in rows:
        print("\n== %-12s reactor %3d 模块  真实 %2d 处 / 仅 DM %2d 种"
              % (x["repo"], x["modules"], x["hard_sites"], x["dm_only_kinds"]))
        for rel, a, v in x["detail"]:
            flag = "候选换坐标(仍需比 jar 类集)" if a in x["hard_flippable_candidates"] else "中央无同名发布件"
            print("   %-56s com.zifang:%s:%s  [%s]" % (rel, a, v, flag))
    print("\n判据：真实依赖那几行才是拦住建造的；候选换坐标要再比 jar 类集（z-rpc-core 就是这样被否掉的）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
