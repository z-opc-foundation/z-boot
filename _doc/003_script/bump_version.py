#!/usr/bin/env python3
"""
bump_version.py — 抬一仓的自身版本（含全 reactor 的自引用），只动"自己的版本"这一件事。

为什么要有它：Central 不可覆盖 ⇒ 迁移后对外 pom 面值变了的仓必须抬号才发得出去（见
publish_bump_check.py）。而一个仓的"自己版本"写在多处：根 pom 的 `<version>`（或
`<revision>` 属性）+ 每个子模块 `<parent><version>`。手工 sed 会把**别人的**版本一起换掉
（`<version>1.0.3</version>` 既可能是本仓模块，也可能是 z-boot-datasource-starter 或 mysql
driver），抬一次号就把一仓的依赖口径改花了。

口径：只重写这三条路径下的文本，其余一个字节都不碰：
    project/version                      —— 根 pom 自己的版本
    project/parent/version               —— 子模块指向父 pom
    project/properties/revision          —— ci-friendly 仓的属性
并且**只在文本逐字等于旧号时**替换（不做前缀匹配，1.0.3 不会误伤 1.0.30）。

注释必须活着：这些 pom 里的注释是组织口径的出处（哪条为什么按坐标写着、哪条为什么和地板
不同值），所以不用 ElementTree 重写文件（它会丢注释、丢空白），改成自己扫标签路径 + 原地
替换那一段文本。

自引用漏网之处**只报不改**：属性（如 `<z-msg.version>`）和 DM 里指向本仓坐标的 `<version>`
可能是旧号，机器不该替人决定。--show-self 会把它们逐行列出来。

用法：
  python3 z-boot/_doc/003_script/bump_version.py --repo z-msg            # dry-run，只报要改哪几行
  python3 z-boot/_doc/003_script/bump_version.py --repo z-msg --to 1.2.2 --write
  python3 z-boot/_doc/003_script/bump_version.py --all --next            # 全组织 BUMP 仓批量：旧号末位 +1
"""
import os
import re
import sys
import glob
import argparse
import xml.etree.ElementTree as ET

NS = "{http://maven.apache.org/POM/4.0.0}"
ZBOOT = os.path.dirname(os.path.abspath(__file__))
FOUNDATION = os.path.abspath(os.path.join(ZBOOT, "..", "..", ".."))


def strip_ns(tag):
    return tag.split("}", 1)[-1]


def eff_version(root):
    """根 pom 的对外版本：字面值，或 ${revision}（读 properties 里的 revision）。"""
    props = {}
    pe = root.find(NS + "properties")
    if pe is not None:
        for c in pe:
            if isinstance(c.tag, str):
                props[strip_ns(c.tag)] = (c.text or "").strip()
    ve = root.find(NS + "version")
    v = (ve.text or "").strip() if ve is not None and ve.text else None
    if v == "${revision}":
        return v, props.get("revision")
    return v, v


def next_patch(v):
    parts = v.split(".")
    if len(parts) < 2 or not parts[-1].isdigit():
        return None
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def own_group(root):
    ge = root.find(NS + "groupId") or root.find(NS + "parent/" + NS + "groupId")
    return ge.text.strip() if ge is not None and ge.text else None


def leftover_refs(pom_files, old):
    """报（不改）：仍然写着旧号的每一处，带上下文。
    机器不该替人决定"这条 1.0.5 是本仓的自引用、还是隔壁仓/第三方恰好同号"，
    所以逐处点名 + 把最近的 <artifactId> 一起打出来给人看。
    "是不是自身版本"按当前内容现算，不搬旧偏移（抬完号长度一变旧偏移就错位）。"""
    hits = []
    for f in pom_files:
        raw = open(f, encoding="utf-8").read()
        scan = blank_comments(raw)
        own = [(s, e) for s, e, _ in own_version_spans(raw)]
        for m in re.finditer(r">([^<>]*)<", scan):
            if m.group(1).strip() != old:
                continue
            p = m.start(1)
            if any(s <= p < e for s, e in own):
                continue
            ctx = scan.rfind("<artifactId>", 0, m.start())
            who = None
            if 0 <= ctx:
                t = re.search(r"<artifactId>([^<]*)</artifactId>", scan[ctx: ctx + 120])
                who = t.group(1) if t else None
            prop = re.search(r"<([a-zA-Z0-9_.\-]+)>\s*" + re.escape(old), scan[max(0, m.start(1) - 60): m.end(1) + 60])
            hits.append((f, raw.count("\n", 0, m.start()) + 1, who or (prop.group(1) if prop else "?"), old))
    return hits


def blank_comments(text):
    """把 <!-- ... --> 整段换成等长空格：偏移量不变，但标签栈不会被注释里的假标签带跑。
    必须做这一步：这些 pom 的注释里满是 `<dependencyManagement>`、`<z-llm.version>0.1.6
    </z-llm.version>` 这类字样（还有不配对的半个标签），不排除就会把层级判断带歪 ——
    z-llm / z-vector / z-wf 第一版就是这样"一处都没改到"的。"""
    out = list(text)
    i = 0
    while True:
        s = text.find("<!--", i)
        if s < 0:
            break
        e = len(text) if text.find("-->", s) < 0 else text.find("-->", s) + 3
        for k in range(s, min(e, len(text))):
            if text[k] not in "\r\n":
                out[k] = " "
        i = e
    return "".join(out)


TOKEN = re.compile(r"<(/?)([a-zA-Z0-9_:.\-]+)([^<>]*?)(/?)>")
TEXT_OF = re.compile(r"<(version|revision)>([^<]*)</\1>")


def own_version_spans(text):
    """返回该文件里"自己的版本"文本的绝对区间 [(start, end, 原文本)]：
    project/version、project/parent/version、project/properties/revision 三条路径。
    DM / dependencies / plugin / relocation 下的 <version> 一律不算 —— 那是别人的版本。"""
    scan = blank_comments(text)
    stack = []
    spans = []
    for m in TOKEN.finditer(scan):
        close, tag, _attr, selfclose = m.groups()
        if selfclose:
            continue
        if close:
            for k in range(len(stack) - 1, -1, -1):
                if stack[k] == tag:
                    del stack[k:]
                    break
            continue
        stack.append(tag)
        if tag not in ("version", "revision"):
            continue
        names = list(stack)
        ok = (
            names == ["project", "version"]
            or (names[0] == "project" and names[1:] == ["parent", "version"])
            or names == ["project", "properties", "revision"]
        )
        if not ok:
            continue
        t = TEXT_OF.match(scan, m.start())
        if t:
            spans.append((t.start(2), t.end(2), t.group(2)))
    return spans


def bump_file(f, old, new, write):
    raw = open(f, encoding="utf-8").read()
    hits = [s for s in own_version_spans(raw) if s[2] == old]
    if not hits:
        return []
    if write:
        out = raw
        for start, end, _ in sorted(hits, reverse=True):
            out = out[:start] + new + out[end:]
        open(f, "w", encoding="utf-8").write(out)
    return sorted(raw.count("\n", 0, st) + 1 for st, _e, _ in hits)


def repo_poms(repo):
    files = []
    for f in glob.glob(os.path.join(repo, "**", "pom.xml"), recursive=True):
        parts = set(f.split(os.sep))
        if {"target", "node_modules", "_frontend", "_code_temp", "_migration", ".git"} & parts:
            continue
        files.append(f)
    return sorted(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo")
    ap.add_argument("--to")
    ap.add_argument("--next", action="store_true", help="目标号 = 旧号末位 +1")
    ap.add_argument("--all", action="store_true", help="扫所有 parent=z-boot-parent 的仓")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    repos = []
    if a.all:
        for d in sorted(os.listdir(FOUNDATION)):
            p = os.path.join(FOUNDATION, d, "pom.xml")
            if not os.path.isfile(p):
                continue
            raw = open(p, encoding="utf-8", errors="replace").read()
            if "z-boot-parent" in raw and d != "z-boot":
                repos.append(d)
    elif a.repo:
        repos = [a.repo]
    else:
        ap.error("要 --repo 或 --all")

    rc = 0
    for d in repos:
        repo = os.path.join(FOUNDATION, d)
        root_pom = os.path.join(repo, "pom.xml")
        root = ET.parse(root_pom).getroot()
        _written, old = eff_version(root)
        if not old or "SNAPSHOT" in old:
            print(f"{d:<16} SKIP（版本 {old} 不可发中央）")
            continue
        new = a.to or (next_patch(old) if a.next else None)
        if not new:
            print(f"{d:<16} {old} —— 未给 --to/--next")
            continue
        files = repo_poms(repo)
        total, per = 0, []
        for f in files:
            ch = bump_file(f, old, new, a.write)
            if not ch:
                continue
            total += len(ch)
            per.append((os.path.relpath(f, repo), ch))
        # 根 pom 必须至少改到一处：没改到就是号判错了，别把半套改动留下
        if not total or not any(rel == "pom.xml" for rel, _ in per):
            print(f"{d:<16} ✗ 根 pom 的自身版本没被定位到（old={old}）⇒ 拒绝，不写")
            rc = 1
            continue
        status = "WROTE" if a.write else "dry-run"
        print(f"{d:<16} {status} {old} -> {new}  行数={total} 文件={len(per)}")
        for rel, ch in per:
            print(f"      {rel}:{','.join(map(str, ch))}")
        left = leftover_refs(files, old)
        if left:
            print(f"      ⚠ 改完仍写着 {old} 的地方（机器不替人判这是自引用还是同号的别家）：")
            for f, i, who, _v in left:
                print(f"        {os.path.relpath(f, repo)}:{i}  最近的 artifactId = {who}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
