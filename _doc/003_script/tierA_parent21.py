#!/usr/bin/env python3
"""消费者轮：33 仓 <parent> 抬到 z-boot-parent:1.0.21，并撤掉三处过渡性 simpleclient 压法。

两阶段（坑 22 的教训）：先把全部新文本在内存里算完、逐文件硬点命中数，任何一处不符 ⇒ 退出 2、零写入。
定位用"注释换成等长空格"后的 span（坑 18 的修法）：pom 注释里满是假 <parent>/<dependency> 标签，
拿 str.replace 或逐行正则都会命中注释里那一份。
"""
import os
import re
import sys

ROOT = "/Users/zifang/workplace/ceo_workplace/z-opc-foundation"
PARENT_RE = re.compile(
    r"<parent>\s*<groupId>io\.github\.yuku123</groupId>\s*<artifactId>\s*z-boot-parent\s*</artifactId>"
    r"\s*<version>\s*(?:1\.0\.19|1\.0\.20)\s*</version>", re.S)
FLOOR_PROP = re.compile(r"<z-boot-floor\.version>\s*1\.0\.19\s*</z-boot-floor\.version>")

# 撤掉的过渡压法：floor 1.0.20 不再按坐标钉 simpleclient=0.8.1 之后，这一格的存在意义就没了
# （净室实测：链上落 0.15.0 + 三格 tracer，ExemplarSampler 从 0.15.0 起就有）。
# snakeyaml=2.0 那一格**不在**本刀里：它压的是 Boot BOM 的 1.30，与地板这一刀无关。
PRESS_RE = re.compile(
    r"[ \t]*<dependency>\s*<groupId>io\.prometheus</groupId>\s*"
    r"<artifactId>\s*simpleclient(?:_common)?\s*</artifactId>\s*<version>\s*0\.16\.0\s*</version>\s*</dependency>\n")


def blank_comments(t):
    return re.sub(r"<!--.*?-->", lambda m: " " * len(m.group(0)), t, flags=re.S)


def splice(text, spans, repls):
    out, prev = [], 0
    for (s, e), r in zip(spans, repls):
        out.append(text[prev:s]); out.append(r); prev = e
    out.append(text[prev:])
    return "".join(out)


plans, errs = {}, []
for d in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, d, "pom.xml")
    if d == "z-boot" or not os.path.isfile(p):
        continue
    raw = open(p, encoding="utf-8").read()
    m = blank_comments(raw)
    hits = list(PARENT_RE.finditer(m))
    if not hits:
        continue
    if len(hits) != 1:
        errs.append("%s: parent 格命中 %d 次，预期 1" % (d, len(hits)))
        continue
    new = PARENT_RE.sub("<parent>\n        <groupId>io.github.yuku123</groupId>\n"
                        "        <artifactId>z-boot-parent</artifactId>\n"
                        "        <version>1.0.21</version>", raw[hits[0].start():hits[0].end()], count=1)
    plans[p] = splice(raw, [(hits[0].start(), hits[0].end())], [new])
    if d == "z-opc":
        fh = list(FLOOR_PROP.finditer(m))
        if len(fh) != 1:
            errs.append("z-opc: z-boot-floor.version 键命中 %d 次，预期 1" % len(fh))
            continue
        n2 = splice(plans[p], [(fh[0].start(), fh[0].end())],
                    ["<z-boot-floor.version>1.0.20</z-boot-floor.version>"])
        plans[p] = n2

for d in ("z-gw", "z-indexer", "z-opc"):
    p = os.path.join(ROOT, d, "pom.xml")
    if p not in plans:
        errs.append("%s: 不在 parent 迁移清单里，撤压法无从谈起" % d); continue
    m = blank_comments(plans[p])
    hits = list(PRESS_RE.finditer(m))
    if len(hits) != 2:
        errs.append("%s: simpleclient(-common) 0.16.0 格命中 %d 次，预期 2" % (d, len(hits))); continue
    plans[p] = splice(plans[p], [(h.start(), h.end()) for h in hits], [""] * 2)

if errs:
    sys.stderr.write("✗ 拒绝写入：\n" + "\n".join("   " + e for e in errs) + "\n")
    sys.exit(2)

if "--write" not in sys.argv:
    print("dry-run：%d 个文件待写" % len(plans))
    for p, txt in plans.items():
        raw = open(p, encoding="utf-8").read()
        import difflib
        diff = [l for l in difflib.unified_diff(raw.splitlines(), txt.splitlines(), lineterm="", n=0)
                if l[:1] in "+-" and not l.startswith(("+++", "---"))]
        print("  %-40s 变更 %d 行: %s" % (os.path.relpath(p, ROOT), len(diff),
                                          " | ".join(l for l in diff)[:170]))
    sys.exit(0)

for p, txt in plans.items():
    import xml.etree.ElementTree as ET
    ET.fromstring(txt)
    open(p, "w", encoding="utf-8").write(txt)
print("written: %d 个文件" % len(plans))
