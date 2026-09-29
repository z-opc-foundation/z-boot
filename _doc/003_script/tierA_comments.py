#!/usr/bin/env python3
"""消费者轮的第二刀：撤掉 simpleclient 压法之后，把**解释这两格的注释**一并改口。

只认"删格后仍会误导人"的注释；纯历史账（迁移那一刻的差集、判账过程）不动，但要把
"留着"这类现在不再成立的结论改成当时判断 + 现已撤销。每处硬点命中 1 次，不符 ⇒ 零写入。
"""
import os
import re
import sys

ROOT = "/Users/zifang/workplace/ceo_workplace/z-opc-foundation"

GW_OLD = re.compile(r"[ \t]*<!-- 旧 parent 直接钉过、而新父链给的值\*\*更低\*\*的两族三格.*?-->\n", re.S)
GW_NEW = """          <!-- 2026-09-29 撤掉过两格 io.prometheus:simpleclient / simpleclient_common（原钉 0.16.0）：
               那两格压的是地板 z-boot-dependencies 按坐标**直接**钉的 simpleclient=0.8.1（现读 1.0.19 发布件），
               而 micrometer-registry-prometheus 的 PrometheusMeterRegistry 要 io.prometheus.client.exemplars.ExemplarSampler
               （0.15.0 起才有）。地板 1.0.20 已把那一格删掉、让 micrometer 自己的 pom 说话 ⇒ 压法失去对象。
               净室实测（parent 1.0.21 + 空本地仓 + repo1-only）：树里落 simpleclient 0.15.0 + simpleclient_common 0.15.0
               + 三格 simpleclient_tracer_*，log4j-slf4j2-impl 0 命中。
             · org.yaml:snakeyaml 这一格**留着**：它压的是 floor import 的 spring-boot-dependencies:2.7.18 给
               的 1.30（CVE-2022-1471 口径），与地板这一刀无关。 -->
"""

IDX_OLD = re.compile(r"[ \t]*<!-- io\.prometheus:simpleclient\(-common\) 0\.16\.0 —— 本仓启动实测逼出来的两格.*?-->\n", re.S)
IDX_NEW = """          <!-- 2026-09-29 撤掉本仓那两格 io.prometheus:simpleclient / simpleclient_common（原钉 0.16.0）。
               这两格是 2026-09-29 早上用 z-indexer-server 的 fat jar 在 corretto-1.8 上实测逼出来的：
               z-boot-gw-starter 带 micrometer-registry-prometheus:1.9.17，而地板 z-boot-dependencies 按坐标
               直接钉了 simpleclient=0.8.1（现读 1.0.19 发布件），编译期毫无怨言、启动才炸
               NoClassDefFoundError: io/prometheus/client/exemplars/ExemplarSampler。
               根修已经在地板 1.0.20 发出去（删掉那格 0.8.1，让 micrometer 自己的 pom 说话），
               parent 随之 1.0.21 ⇒ 本仓不再需要本地压法，净室实测落 0.15.0 + 三格 tracer。 -->
"""

OPC_OLD = re.compile(r"[ \t]*<!-- ===== Prometheus / simpleclient 版本钉死 \(FEATURE_PROM_FIX.*?"
                     r"这是唯一压得住继承条目的层级（README 步骤 5）。 -->\n", re.S)
OPC_NEW = """          <!-- ===== Prometheus / simpleclient（FEATURE_PROM_FIX）：2026-09-29 已撤销本仓那两格 =====
                 原来钉 0.16.0 的起因（保留原文要点，别当成虚构）：z-gw-core 间接带进
                 micrometer-registry-prometheus，其 PrometheusMeterRegistry 要 io.prometheus.client.exemplars.ExemplarSampler，
                 而地板 z-boot-dependencies 1.0.18/1.0.19 的直接 DM 里按坐标写着 simpleclient=**0.8.1**（现读发布件），
                 于是编译期无话、启动期 ClassNotFoundException；@SpringBootApplication(exclude=...) 挡不住，
                 因为类加载发生在排除判断之前。
                 现在根修已经在地板 1.0.20 落地（那一格已删）+ parent 1.0.21 ⇒ 压法失去对象，本仓撤掉
                 simpleclient 与 simpleclient_common 两条直接条目；净室实测链上落 0.15.0（含 ExemplarSampler）
                 加三格 simpleclient_tracer_*。⚠ 撤销的前提是**本仓 <parent> 已经在 1.0.21**：
                 停在 1.0.19/1.0.20 的消费者继承的还是带 0.8.1 的旧地板，撤了就是原地复发。 -->
"""

# z-opc 根 pom 那段"链更低/链不供"的判账：把现在不再成立的结论改成"当时 + 已撤"
OPC_LINE_A = re.compile(
    r"[ \t]*z-wf-core/-web/-starter 1\.0\.5、io\.prometheus:simpleclient_common 0\.16\.0）⇒ 删一条\n"
    r"[ \t]*就是让该坐标退回传递解析 ⇒ 逐字留着。")
OPC_LINE_A_NEW = """                 z-wf-core/-web/-starter 1.0.5、io.prometheus:simpleclient_common 0.16.0）⇒ 当时删一条
                 就是让该坐标退回传递解析 ⇒ 那九条逐字留着；simpleclient_common 这条 2026-09-29 随地板 1.0.20
                 撤掉了 —— 它当年不是为了绕"链不供"，而是压 floor 直钉的 0.8.1（现读 1.0.19 发布件），
                 那一格删掉后压法失去对象，详见下面 FEATURE_PROM_FIX 那段。"""
OPC_LINE_B = re.compile(
    r"io\.prometheus:simpleclient 本仓 0\.16\.0 vs 链 \*\*floor 直钉 0\.8\.1\*\* —— 这条更狠：\n"
    r"\s*它就在 floor 的 151 条直接条目里（1\.0\.18 与 1\.0\.19 都是 0\.8\.1），删掉本仓这条就是\n"
    r"\s*把 FEATURE_PROM_FIX（见下面 0\.16\.0 那段注释）钉死的 ClassNotFoundException 修复\n"
    r"\s*静默撤掉 ⇒ 留着，并把这一格记进\"链更低\"表。")
OPC_LINE_B_NEW = """io.prometheus:simpleclient 本仓 0.16.0 vs 链 **floor 直钉 0.8.1** —— 这条更狠：
                   当时（迁移那一刻）它就在 floor 1.0.18/1.0.19 的 151 条直接条目里，删掉本仓这条会把
                   FEATURE_PROM_FIX 钉死的 ClassNotFoundException 修复静默撤掉 ⇒ 当时判"留着"是对的。
                   2026-09-29 地板 1.0.20 已删掉那一格（parent 随之 1.0.21）⇒ 这两格连同
                   simpleclient_common 一起撤销，现状见下面 FEATURE_PROM_FIX 那段。"""

EDITS = {
    "z-gw/pom.xml": [(GW_OLD, GW_NEW, 1, "撤掉过两格")],
    "z-indexer/pom.xml": [(IDX_OLD, IDX_NEW, 1, "撤掉本仓那两格")],
    "z-opc/pom.xml": [(OPC_OLD, OPC_NEW, 1, "已撤销本仓那两格"),
                      (OPC_LINE_A, OPC_LINE_A_NEW, 1, "当时删一条"),
                      (OPC_LINE_B, OPC_LINE_B_NEW, 1, "当时判")],
}


def blank(t):
    # 这一刀**故意**匹配注释正文，所以绝不能先把注释抹成空格（抹了就一处也匹配不到）。
    # 上一刀 tierA_parent21.py 需要等长替换，是因为它要避开注释里的假 <parent>；两处口径相反，别照抄。
    return t


plans, errs = {}, []
for rel, specs in EDITS.items():
    p = os.path.join(ROOT, rel)
    raw = open(p, encoding="utf-8").read()
    m = blank(raw)
    pairs = []
    for rx, new, exp, done_marker in specs:
        hits = list(rx.finditer(m))
        if len(hits) == 0 and done_marker in raw:
            continue  # 幂等：这一处已经改过口，别把它当成命中失败
        if len(hits) != exp:
            errs.append("%s: %s 命中 %d 次，预期 %d" % (rel, rx.pattern[:40], len(hits), exp))
        pairs += [(h.start(), h.end(), new) for h in hits]
    if errs:
        continue
    pairs.sort()  # 位移与替换必须一起排：v1 只排了 spans，把 OPC_NEW 拼进了另一处注释里
    out, prev = [], 0
    for s, e, r in pairs:
        out.append(m[prev:s]); out.append(r); prev = e
    out.append(m[prev:])
    plans[p] = "".join(out)

if errs:
    sys.stderr.write("✗ 拒绝写入：\n" + "\n".join("   " + e for e in errs) + "\n")
    sys.exit(2)
if "--write" not in sys.argv:
    for p, txt in plans.items():
        print("dry-run %s: %d → %d 字节" % (os.path.relpath(p, ROOT), len(open(p).read()), len(txt)))
    sys.exit(0)
import xml.etree.ElementTree as ET
for p, txt in plans.items():
    ET.fromstring(txt)  # 全部先验一遍再落盘：v1 边验边写，z-opc 报错时 z-gw 已改动
for p, txt in plans.items():
    open(p, "w", encoding="utf-8").write(txt)
print("written: %d 个文件" % len(plans))
