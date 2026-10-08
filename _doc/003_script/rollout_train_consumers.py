#!/usr/bin/env python3
"""rollout_train_consumers.py —— 火车制消费者轮：全组织 <parent> 抬到 z-boot-parent:1.1.0。

改动面（最小一刀）：
  1. 仓根 pom 的 <parent> 是 io.github.yuku123:z-boot-parent 且版本 ∈ {1.0.21, 1.0.23} ⇒ 抬 1.1.0。
  2. z-schedule-admin（parent 是 spring-boot-starter-parent，不继承 z-boot-parent）：
     字面 z-boot-web/datasource-starter 抬 1.1.0、z-util.version 抬 1.0.19（对齐本班火车采纳值）。
  3. z-camuda-admin 的 <z-boot-fleet.version> 死键（fleet 已退役）⇒ 删除。
  4. 只报告不动：z-product/** 独立 pom（z-boot.version=1.0.0-SNAPSHOT，不在任何 reactor）、
     DM/依赖里残留 z-boot-fleet / z-boot-dependencies 结构引用（应为 0，有则列出人工判）。

用法：
  python3 rollout_train_consumers.py            # dry-run：打印将改清单，零写入
  python3 rollout_train_consumers.py --write    # 落盘
"""
import os
import re
import sys

FOUNDATION = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
TRAIN = "1.1.0"
OLD_PARENT_VERSIONS = ("1.0.21", "1.0.23")
EXCLUDE = {"z-boot", "z-opc-foundation-lead"}
SKIP_DIRS = {"_code_temp", ".cache", "target", "node_modules", ".git"}


def repo_root_poms():
    for d in sorted(os.listdir(FOUNDATION)):
        if d in EXCLUDE or d.startswith("."):
            continue
        p = os.path.join(FOUNDATION, d, "pom.xml")
        if os.path.isfile(p):
            yield d, p


def main():
    write = "--write" in sys.argv
    changed, skipped, notes = [], [], []
    specials_run = set()
    for repo, p in repo_root_poms():
        text = open(p, encoding="utf-8").read()
        stripped = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        m = re.search(r"<parent>\s*<groupId>io\.github\.yuku123</groupId>\s*"
                      r"<artifactId>z-boot-parent</artifactId>\s*<version>([^<]+)</version>", stripped)
        if m and m.group(1) in OLD_PARENT_VERSIONS:
            new = text.replace("<version>%s</version>" % m.group(1),
                               "<version>%s</version>" % TRAIN, 1)
            assert new != text
            changed.append((repo, p, m.group(1)))
            if write:
                open(p, "w", encoding="utf-8").write(new)
        # 特例 pass（与 parent 命中无关，每仓只跑一次）
        # z-ops：自包含设计，DM import z-boot-dependencies:${z-boot.version}(=1.0.12)。
        # 火车制：换 import z-boot-parent:1.1.0（坐标超集、地板逐字同值）；starter 版本交
        # parent DM 的 z-boot-self 段供；本地 <z-boot.version> 键随之悬空 ⇒ 删除。
        if repo == "z-ops" and "z-boot.version" in stripped:
            specials_run.add(repo)
            n = text
            n = n.replace("""<artifactId>z-boot-dependencies</artifactId>
                <version>${z-boot.version}</version>""",
                          """<artifactId>z-boot-parent</artifactId>
                <version>%s</version>""" % TRAIN)
            n = re.sub(r"\n\s*<z-boot\.version>[^<]*</z-boot\.version>", "", n, count=1)
            if n != text:
                changed.append((repo, p, "floor import → z-boot-parent:%s + drop z-boot.version 键" % TRAIN))
                if write:
                    open(p, "w", encoding="utf-8").write(n)
            else:
                notes.append("z-ops: 期望的 import 形状没匹配上（人工看 pom）")
        # z-schedule-admin（parent=spring-boot-starter-parent，不继承 z-boot-parent）：字面对齐本班火车
        sa = os.path.join(FOUNDATION, "z-schedule", "z-schedule-admin", "pom.xml")
        if repo == "z-schedule" and os.path.isfile(sa) and "z-schedule-admin" not in specials_run:
            specials_run.add("z-schedule-admin")
            t = open(sa, encoding="utf-8").read()
            n = t.replace("<version>1.0.21</version>", "<version>%s</version>" % TRAIN)
            n = re.sub(r"(<z-util\.version>)[^<]+(</z-util\.version>)", r"\g<1>1.0.19\g<2>", n)
            if n != t:
                changed.append(("z-schedule/z-schedule-admin", sa, "z-boot-* 字面→1.1.0, z-util→1.0.19"))
                if write:
                    open(sa, "w", encoding="utf-8").write(n)
        # z-camuda-admin 的 fleet 死键
        cam_admin = os.path.join(FOUNDATION, repo, "z-camuda-admin", "pom.xml")
        if os.path.isfile(cam_admin):
            t = open(cam_admin, encoding="utf-8").read()
            n = re.sub(r"\n\s*<z-boot-fleet\.version>[^<]*</z-boot-fleet\.version>", "", t)
            if n != t:
                changed.append((repo + "/z-camuda-admin", cam_admin, "drop z-boot-fleet.version"))
                if write:
                    open(cam_admin, "w", encoding="utf-8").write(n)
        if repo == "z-opc":
            gp = os.path.join(FOUNDATION, repo, "z-product", "pom.xml")
            if os.path.isfile(gp):
                skipped.append("z-product/pom.xml: 独立 pom（z-boot.version=1.0.0-SNAPSHOT），按原账不动")
        # z-opc：4 份 pom 直接 import z-boot-dependencies:${z-boot-floor.version}(=1.0.20)。
        # 换成 import z-boot-parent:1.1.0（坐标超集、地板段逐字同值）；键随之悬空 ⇒ 删。
        if repo == "z-opc":
            for rel in ("pom.xml", "z-team/pom.xml", "z-agent/z-agent-center/pom.xml",
                        "z-agent/z-agent-knowledge/pom.xml"):
                fp = os.path.join(FOUNDATION, repo, rel)
                if not os.path.isfile(fp):
                    continue
                t = open(fp, encoding="utf-8").read()
                n = re.sub(
                    r"<artifactId>z-boot-dependencies</artifactId>(.*?)<version>\$\{z-boot-floor\.version\}</version>",
                    lambda m: "<artifactId>z-boot-parent</artifactId>" + m.group(1) + "<version>%s</version>" % TRAIN,
                    t, flags=re.S)
                n = re.sub(r"\n\s*<z-boot-floor\.version>[^<]*</z-boot-floor\.version>", "", n, count=1)
                if n != t:
                    changed.append(("z-opc/" + rel, fp, "floor import → z-boot-parent:%s" % TRAIN))
                    if write:
                        open(fp, "w", encoding="utf-8").write(n)
        if re.search(r"<artifactId>z-boot-(fleet|dependencies)</artifactId>", stripped):
            notes.append("%s: pom 结构里仍引用 z-boot-fleet/z-boot-dependencies（人工判）" % repo)
        if repo == "z-opc":
            gp = os.path.join(FOUNDATION, repo, "z-product", "pom.xml")
            if os.path.isfile(gp):
                skipped.append("z-product/pom.xml: 独立 pom（z-boot.version=1.0.0-SNAPSHOT），按原账不动")

    print("== 将改 %d 处 ==" % len(changed))
    for repo, p, what in changed:
        print("  %-28s %s" % (repo, what))
    for n in notes:
        print("[note] %s" % n)
    for s in skipped:
        print("[skip] %s" % s)
    if not write:
        print("（dry-run，零写入；--write 落盘）")


if __name__ == "__main__":
    main()
