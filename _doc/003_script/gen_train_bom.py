#!/usr/bin/env python3
"""gen_train_bom.py —— 火车制拓扑的唯一写手（2026-10-08 重构，替代 gen_fleet_bom.py 的产物面）。

新拓扑（CEO 裁定「火车制」）：
  z-boot-parent = 唯一慢层权威：
      <parent> 根 z-boot:1.0.19（z-boot-dependencies 退役）
      DM = 第三方地板（2026-10-30 SB3/Java 17 迁移起**手改住在本 pom 内**，原
           z-boot-dependencies 已随 1.1.0 火车 git rm）+ 接入面 pin（脚本按
           「被跨仓真实声明」现算）+ 自家 starter（${z-boot.version}，与 parent 同火车）
      properties = 地板（手改，含 -parameters 等 SB3 口注视释）+ 接入面
           <z-<族>.version> + z-boot.version
  z-boot-*-starter = 产品层：DM 只 import parent-as-BOM 一条；client 依赖写字面版本
      （值 = 接入面 pin 的同源，发布件经 flatten 内联，形状与今天一致）。
  fleet / z-boot-dependencies 两个文件夹已随火车删除（Central 旧件永久在架，不炸迁移中的消费方）。

⚠ 地板与生成段的边界（2026-10-30 对齐）：地板 = HEAD z-boot-parent/pom.xml 的
  properties / dependencyManagement 剥掉生成段（fam 注释+键、z-boot.version、
  「接入面 pin」标记起到 END z-boot-self）后原样保留。⇒ 改地板直接改本 pom、
  先提交再跑生成；目标文件有未提交改动时 --write 拒绝落盘（pristine 读 HEAD，会吃手改）。

接入面口径（机械、不手维护名单）：坐标被「非所属仓」的 pom 在 <dependencies>（真依赖，
非 dependencyManagement 登记）里声明过 ⇒ 进 pin。排除 _code_temp（资料库，CEO 裁定不作为
任何口径的输入）、.cache、target、node_modules、z-boot 仓自身。

守卫（沿袭 gen_fleet_bom.py 的教训，全部双向验证过才许落盘）：
  G1 地板 DM 里 io.github.yuku123 坐标必须 0 条（搬运的是纯第三方）
  G2 接入面每一格的 (坐标,版本) 对 repo1 发 ranged GET，取不到即拒绝落盘（防烧格子）
  G3 地板与 parent 同名 property 值必须相等才允许合并（不许静默改值；地板即 parent
     ⇒ 现天然无冲突，保留是防将来再拆源）
  G4 每个 starter 的 client 依赖必须落在接入面 pin 里；属主不在 FAMILIES 的手管族
     （如 z-agent-proxy）保留字面版本并告警，不判红
  G5 parent 自身 <version> == <z-boot.version>（同火车不变式）
  脏检查（写盘前置）：目标 pom 有未提交改动 ⇒ 拒绝落盘（生成读 HEAD，会覆盖手改）

用法：
    python3 gen_train_bom.py            # 只打印计划与守卫结果，不写盘
    python3 gen_train_bom.py --write    # 落盘（G1-G5 全绿才写；repo1 探活失败逐格列出并退出 2；
                                        # 目标 pom 有未提交改动拒绝落盘并退出 3）
"""
import os
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET

NS = {"m": "http://maven.apache.org/POM/4.0.0"}
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FOUNDATION = os.path.abspath(os.path.join(REPO_ROOT, ".."))

TRAIN = "1.2.0"
PREV_TRAIN = "1.1.2"
ROOT_PARENT = ("io.github.yuku123", "z-boot", "1.0.19")
# 地板源（2026-10-30 起）：z-boot-parent 自身 —— SB3 迁移把地板手改搬进了本 pom，
# 原 z-boot-dependencies 已随 1.1.0 火车 git rm。生成仍读 git HEAD（纯函数），
# 剥掉生成段后原样保留 ⇒ 手改地板先提交再生成，--write 的脏检查兜底。
PARENT_DIR = os.path.join(REPO_ROOT, "z-boot-parent")
AGG_DIRS = [os.path.join(REPO_ROOT, "z-boot-starter"),
            os.path.join(REPO_ROOT, "z-boot-integration-starters")]
BASE_STARTERS = {"z-boot-base", "z-boot-web-starter", "z-boot-datasource-starter"}

EXCLUDE_DIR_PARTS = {"_code_temp", ".cache", "target", "node_modules", ".git", ".gnupg"}

# 兄弟仓 -> (property 词根, 版本)。值 = 接入面 pin 权威（b1fae5b 起按现实校正：
# z-llm → z-llm-gateway 0.1.9、z-agent-proxy → z-llm-agent 等）。⚠ 值与属主仓工作
# 版本不一致属正常（仓在途、pin 未收版）；抬族版本 = 改这里 → --write 的 G2 逐格探 repo1。
FAMILIES = {
    "z-config": ("z-config", "1.0.10"), "z-ctc": ("z-ctc", "1.0.2"),
    "z-cache": ("z-cache", "1.3.6"), "z-mq": ("z-mq", "1.3.1"),
    "z-gw": ("z-gw", "1.0.6"), "z-kb": ("z-kb", "1.0.7"),
    "z-vector": ("z-vector", "1.0.5"), "z-graph": ("z-graph", "1.0.8"),
    "z-rpc": ("z-rpc", "1.0.4"), "z-oss": ("z-oss", "1.0.4"),
    "z-schedule": ("z-schedule", "1.0.6"), "z-msg": ("z-msg", "1.2.2"),
    "z-script": ("z-script", "1.0.2"), "z-util": ("z-util", "1.0.22"),
    "z-agent-kernel": ("z-agent-kernel", "0.2.1"), "z-llm-gateway": ("z-llm-gateway", "0.1.9"),
    "z-mcp": ("z-mcp", "0.2.1"), "z-skill": ("z-skill", "0.2.2"),
    "z-agent": ("z-agent", "0.1.4"), "z-bot": ("z-bot", "0.2.1"),
    "z-llm-agent": ("z-llm-agent", "1.0.47"), "z-llm-msghub": ("z-llm-msghub", "1.0.47"), "z-mist": ("z-mist", "1.0.4"),
    "z-qa": ("z-qa", "1.1.1"), "z-camuda": ("z-camuda", "1.0.6"),
    "z-indexer": ("z-indexer", "1.0.0"),
}

REPO1 = "https://repo1.maven.org/maven2/io/github/yuku123"

# 无跨仓真实声明、但要求 parent 统一供版的坐标（值跟属主 FAMILIES 版本走）。
# 1.1.1 收 z-util 三拆的新 http 坐标：FT 侧目前直书字面版本，parent 供版后才能回归无版本声明。
EXTRA_PIN = {
    "z-util": ["z-util-http-core", "z-util-http-proxy", "z-util-http-server"],
}


def strip_notes(x):
    return re.sub(r"<!--.*?-->", "", x, flags=re.S)


def pristine(relpath):
    """模板输入一律读 git HEAD：生成必须是纯函数，重跑不许吃自己上一次的产物。"""
    r = subprocess.run(["git", "-C", REPO_ROOT, "show", "HEAD:%s" % relpath],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return r.stdout
    return open(os.path.join(REPO_ROOT, relpath), encoding="utf-8").read()


def parse_pom(path):
    return ET.fromstring(strip_notes(open(path, encoding="utf-8").read()))


def find_poms():
    out = []
    for d in sorted(os.listdir(FOUNDATION)):
        if d == "z-boot" or d.startswith("."):
            continue
        base = os.path.join(FOUNDATION, d)
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [x for x in dirs if x not in EXCLUDE_DIR_PARTS]
            if "pom.xml" in files:
                out.append(os.path.join(root, "pom.xml"))
    return out


def owner_map_and_surface():
    owner = {}
    declared = {}
    for p in find_poms():
        repo = os.path.relpath(p, FOUNDATION).split(os.sep)[0]
        try:
            r = parse_pom(p)
        except ET.ParseError:
            continue
        a = r.find("m:artifactId", NS)
        if a is not None and a.text:
            owner.setdefault(a.text, repo)
        for d in r.findall("m:dependencies/m:dependency", NS):
            g, da = d.find("m:groupId", NS), d.find("m:artifactId", NS)
            if g is not None and da is not None and g.text == "io.github.yuku123":
                declared.setdefault(repo, set()).add(da.text)
    surface = {}  # artifact -> owning repo (only cross-repo declared)
    for repo, arts in declared.items():
        for a in arts:
            o = owner.get(a)
            if o and o != repo:
                surface[a] = o
    return owner, surface


def repo1_exists(artifact, version):
    # Maven 布局：groupId 逐段 + artifactId，族名不是路径段（首版在这里插了族名，70/70 假 404）
    url = f"{REPO1}/{artifact}/{version}/{artifact}-{version}.pom"
    req = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status in (200, 206)
    except Exception as e:
        print("    [probe] %s:%s -> %s" % (artifact, version, type(e).__name__))
        return False


def raw_block(text, tag):
    """按原文抽 <tag>…</tag>（不剥注释、rstrip 尾部空白）—— 地板/ build 段里有
    手改注释（-parameters 口径、SB3 plugins 口径），剥了就是覆盖手改。
    非贪婪取首块；properties / build 在全文各只出现一次（flatten 的内嵌 properties
    排在项目块之后），首个即真实块。"""
    m = re.search(r"<%s>(.*?)</%s>" % (tag, tag), text, re.S)
    return m.group(1).rstrip() if m else None


def dedent_block(block):
    """把子块整体去掉公共缩进，便于嵌进新 pom 的统一缩进。"""
    lines = block.split("\n")
    indents = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
    cut = min(indents) if indents else 0
    return "\n".join(l[cut:] if len(l) >= cut else l.lstrip() for l in lines)


def build_parent_pom(owner, surface, write_mode):
    parent = pristine("z-boot-parent/pom.xml")

    # ---- 地板抽取（2026-10-30 起：地板手改住在本 pom，剥掉生成段即地板）----
    # 生成段边界：DM 里「接入面 pin」标记行起到 END z-boot-self（pin+self 都重算）；
    # properties 里 fam 注释+<z-*.version>+z-boot.version 按行剥（见下）。
    pin_i = parent.find("==== 接入面 pin")
    assert pin_i > 0, "parent pom 缺「接入面 pin」生成标记（结构变了？）"
    pin_line_start = parent.rfind("\n", 0, pin_i) + 1
    dm_i = parent.find("<dependencyManagement>")
    deps_i = parent.find("<dependencies>", dm_i) if dm_i > 0 else -1
    assert deps_i > dm_i > 0, "parent pom 缺 <dependencyManagement><dependencies>（结构变了？）"
    floor_dm_raw = parent[deps_i + len("<dependencies>"):pin_line_start]

    # G1: 地板 DM 里不得有 yuku 坐标（剥注释后数，防注释里带坐标误判）
    assert not re.search(r"<groupId>io\.github\.yuku123</groupId>", strip_notes(floor_dm_raw)), \
        "G1 红：地板 DM 混入 yuku 坐标"

    parent_props = {p.tag.split("}")[-1]: (p.text or "")
                    for p in ET.fromstring(strip_notes(parent)).find("m:properties", NS)}
    floor_props = parent_props  # 地板即 parent ⇒ G3 天然无冲突（保留校验防将来再拆源）
    # 同名 property 值冲突：以 parent 现值为准（今天消费者生效的就是就近覆盖值，零漂移）
    shared = set(floor_props) & set(parent_props) - {"z-boot.version", "z-boot-fleet.version"}
    conflict = sorted(k for k in shared if floor_props[k].strip() != parent_props[k].strip())
    if conflict:
        print("  [info] property 冲突以 parent 现值赢: %s" %
              ", ".join("%s(%s>%s)" % (k, floor_props[k], parent_props[k]) for k in conflict))

    # 接入面按族分组；属主不在 FAMILIES 的（z-task/z-ext/z-meta 等 com.zifang 幻影族，#31 批次）
    # 警告并跳过 —— 它们消费侧自带显式版本，不归 parent 供。
    fam_artifacts = {}
    skipped = {}
    for a, o in sorted(surface.items()):
        if o not in FAMILIES:
            skipped.setdefault(o, []).append(a)
            continue
        fam_artifacts.setdefault(o, []).append(a)
    for o in sorted(skipped):
        print("  [warn] 跳过（属主 %s 不在 FAMILIES，#31 批次前不进 pin）: %s" % (o, ", ".join(sorted(skipped[o]))))

    # starter 自己就是接入面消费者：19 个 starter 的 client 依赖并入 pin 集
    for p in starter_plan(owner, {}):
        if p["client"]:
            o = owner.get(p["client"])
            if o in FAMILIES and p["client"] not in fam_artifacts.get(o, []):
                fam_artifacts.setdefault(o, []).append(p["client"])
                print("  [info] pin 并入 starter client: %s (%s)" % (p["client"], o))
    for o, arts in sorted(EXTRA_PIN.items()):
        for a in arts:
            if a not in fam_artifacts.get(o, []):
                fam_artifacts.setdefault(o, []).append(a)
                print("  [info] pin 并入 EXTRA_PIN: %s (%s)" % (a, o))
    missing_fam = [f for f in FAMILIES if f not in fam_artifacts]
    missing_fam = [f for f in missing_fam if f not in ("z-qa",)]  # z-qa 无 starter 无跨仓声明，允许缺席
    if missing_fam:
        print("  [warn] 无跨仓声明的族（不进 pin，留 FAMILIES 供体检）: %s" % ", ".join(missing_fam))

    # ---- 地板 properties 原文（含手改注释/缩进），只剥本脚本生成的行 ----
    props_raw = raw_block(parent, "properties")
    assert props_raw is not None, "parent pom 缺 <properties>（结构变了？）"
    gen_root_keys = {FAMILIES[f][0] for f in fam_artifacts}

    def _is_gen_prop_line(l):
        s = l.strip()
        m = re.match(r"^<!--\s*([a-z0-9-]+)\s+\S+（接入面 pin", s)
        if m and m.group(1) in fam_artifacts:
            return True
        m2 = re.match(r"^<([a-z0-9-]+)\.version>", s)
        if m2 and m2.group(1) in gen_root_keys:
            return True
        return s.startswith("<z-boot.version>")

    kept = [l for l in props_raw.split("\n") if not _is_gen_prop_line(l)]
    while kept and not kept[0].strip():
        kept.pop(0)
    # 模板在 <properties> 后自带一个换行 ⇒ 前置恰好一个 "\n" 得到一个空行（与现文件一致）
    floor_props_xml = "\n" + "\n".join(kept).rstrip()

    # parent 专属键 + 冲突键（parent 值后置覆盖 floor 搬运值）。
    # 族键（z-*.version）永远由 fam_prop_lines 独家产出——从生成态重跑时不得经 extras 二次进入。
    fam_key_re = re.compile(r"^z-[a-z-]+\.version$")
    extra_keys = [k for k in parent_props
                  if k not in ("z-boot.version", "z-boot-fleet.version")
                  and not fam_key_re.match(k)
                  and (k not in floor_props or k in conflict)]
    extra_keys.sort()
    extra_lines = ["        <%s>%s</%s>" % (k, parent_props[k], k) for k in extra_keys]
    fam_prop_lines = []
    for f in sorted(fam_artifacts):
        root_key, ver = FAMILIES[f]
        fam_prop_lines.append("        <!-- %s %s（接入面 pin，值与gen脚本 FAMILIES 同源） -->" % (f, ver))
        fam_prop_lines.append("        <%s.version>%s</%s.version>" % (root_key, ver, root_key))
    fam_prop_lines.append("        <z-boot.version>%s</z-boot.version>" % TRAIN)

    # ---- 地板 DM 原文：剥生成段后已在目标缩进，原样保留（不再 dedent）----
    dm_lines = floor_dm_raw.split("\n")
    while dm_lines and not dm_lines[0].strip():
        dm_lines.pop(0)
    floor_dm_xml = "\n".join(dm_lines).rstrip()
    pin_lines = ["            <!-- ==== 接入面 pin：被跨仓真实声明的坐标（gen_train_bom.py 现算，勿手改） ==== -->"]
    for f in sorted(fam_artifacts):
        root_key, ver = FAMILIES[f]
        pin_lines.append("            <!-- %s -->" % f)
        for a in fam_artifacts[f]:
            pin_lines.append("            <dependency>")
            pin_lines.append("                <groupId>io.github.yuku123</groupId>")
            pin_lines.append("                <artifactId>%s</artifactId>" % a)
            pin_lines.append("                <version>${%s.version}</version>" % root_key)
            pin_lines.append("            </dependency>")
    self_lines = ["            <!-- BEGIN z-boot-self (gen_train_bom.py 维护，勿手改) -->"]
    for a in sorted(BASE_STARTERS | {d for d in os.listdir(os.path.join(REPO_ROOT, "z-boot-integration-starters"))
                                     if d.startswith("z-boot-")} |
                    {d for d in os.listdir(os.path.join(REPO_ROOT, "z-boot-starter")) if d.startswith("z-boot-")}):
        if a == "z-boot-integration-starters":
            continue
        self_lines += ["            <dependency>",
                       "                <groupId>io.github.yuku123</groupId>",
                       "                <artifactId>%s</artifactId>" % a,
                       "                <version>${z-boot.version}</version>",
                       "            </dependency>"]
    self_lines.append("            <!-- END z-boot-self -->")

    header = """<?xml version="1.0" encoding="UTF-8"?>
<!--
    z-boot-parent —— 唯一消费入口 + 唯一慢层权威（2026-10-08 火车制拓扑）。

    本 pom 由 gen_train_bom.py 维护两段：接入面 pin（被跨仓真实声明的 z-* 坐标，
    机械口径现算）与自家 starter（${z-boot.version}，与 parent 同火车同号）。
    第三方地板自 2026-10-30 SB3/Java 17 迁移起手改住在本 pom 内（原 z-boot-dependencies
    已随火车退役）—— 改地板直接改本文件，先提交再跑生成（--write 有脏检查兜底）。

    消费者世界：一行 <parent> + 若干条无版本依赖。真要提前尝鲜某个 client 新版：
    本仓 dependencyManagement 写直接条目覆盖（DM 就近优先），等下一班火车再回归。
    server/部署件不在此链上 —— 部署版本是部署侧自己的字面号。
-->
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>%s</groupId>
        <artifactId>%s</artifactId>
        <version>%s</version>
        <relativePath>../pom.xml</relativePath>
    </parent>
""" % ROOT_PARENT

    # properties 三段按序拼：地板原文 + （可选）extra + 生成的族键。
    props_body = floor_props_xml
    if extra_lines:
        props_body += "\n\n" + "\n".join(extra_lines)
    props_body += "\n" + "\n".join(fam_prop_lines)

    pom = header + """
    <artifactId>z-boot-parent</artifactId>
    <version>%s</version>
    <packaging>pom</packaging>

    <name>z-boot :: parent</name>
    <description>z-opc-foundation 各仓统一 parent：第三方地板 + 接入面版本 + 自家 starter 火车 + Java 17 / Spring Boot 3 构建口径 / Consumer Parent</description>

    <properties>
%s
    </properties>

    <dependencyManagement>
        <dependencies>
%s

%s

%s
        </dependencies>
    </dependencyManagement>
""" % (TRAIN, props_body,
       floor_dm_xml, "\n".join(pin_lines), "\n".join(self_lines))

    # pluginManagement + flatten 覆盖块自现 parent 原样搬运（raw：段内手改注释不许剥）
    build = raw_block(parent, "build")
    assert build is not None, "parent pom 缺 <build>（结构变了？）"
    pom += """
    <build>
%s
    </build>

</project>
""" % dedent_block(build)
    return pom.rstrip() + "\n", floor_props, fam_artifacts


def starter_plan(owner, surface):
    plans = []
    for agg in AGG_DIRS:
        agg_rel = os.path.relpath(agg, REPO_ROOT)
        for d in sorted(os.listdir(agg)):
            if not d.startswith("z-boot-") or not os.path.isfile(os.path.join(agg, d, "pom.xml")):
                continue
            rel = "%s/%s/pom.xml" % (agg_rel, d)
            text = pristine(rel)
            r = ET.fromstring(strip_notes(text))
            arts = [x.find("m:artifactId", NS).text
                    for x in r.findall("m:dependencies/m:dependency", NS)
                    if x.find("m:groupId", NS).text == "io.github.yuku123"]
            client = arts[0] if arts else None
            plans.append({"dir": d, "path": os.path.join(agg, d, "pom.xml"), "text": text,
                          "client": client, "own": r.find("m:artifactId", NS).text})
    return plans


def rewrite_starter(p, owner, surface, fam_artifacts):
    text = p["text"]
    new = text
    # 版本：parent 引用 / 自身版本 / DM import → 火车号。
    # 1.1.0 起文件已是生成态（上一班把 1.0.25 换成了 1.1.0），所以替换源 = PREV_TRAIN。
    new = new.replace("<version>%s</version>" % PREV_TRAIN, "<version>%s</version>" % TRAIN)
    # DM：floor+fleet 两条 import → 单条 parent-as-BOM
    new_dm = """    <dependencyManagement>
        <dependencies>
            <!-- 唯一版本供给：parent-as-BOM（第三方地板 + 接入面 + 自家火车全在这里） -->
            <dependency>
                <groupId>io.github.yuku123</groupId>
                <artifactId>z-boot-parent</artifactId>
                <version>%s</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
        </dependencies>
    </dependencyManagement>""" % TRAIN
    new = re.sub(r"    <dependencyManagement>.*?</dependencyManagement>", new_dm, new, count=1, flags=re.S)
    if p["client"]:
        o = owner.get(p["client"])
        if o not in FAMILIES:
            # 手管族（不进 FAMILIES / 不进 pin）：client 自带字面版本即可解析 ⇒ 放行并告警
            print("  [warn] starter %s: client %s 属主 %s 不在 FAMILIES —— 保留字面版本（手管，不改写）"
                  % (p["own"], p["client"], o))
            return new
        assert p["client"] in fam_artifacts.get(o, []), "G4 红：%s 不在接入面 pin" % p["client"]
        ver = FAMILIES[o][1]
        # client 版本：生成态里已带字面版本（上一班写入）→ 原位替换值；
        # 若仍是 version-less（非生成态）→ 在 </artifactId> 后插入。
        # 插入点锚 artifactId 永远紧邻版本（带 <exclusions> 的 client 块锚 </dependency> 会插歪）。
        pat_ver = re.compile(r"(<artifactId>%s</artifactId>\s*)<version>[^<]+</version>" % re.escape(p["client"]))
        if pat_ver.search(new):
            new = pat_ver.sub(lambda m: m.group(1) + "<version>%s</version>" % ver, new, count=1)
        else:
            pat = re.compile(r"(<artifactId>%s</artifactId>)" % re.escape(p["client"]))
            assert pat.search(new), "starter %s: 未找到 version-less 的 %s 依赖" % (p["own"], p["client"])
            new = pat.sub(lambda m: m.group(1) + "\n                <version>%s</version>" % ver, new, count=1)
    return new


def main():
    write_mode = "--write" in sys.argv
    owner, surface = owner_map_and_surface()
    print("接入面（被跨仓真实声明）: %d 坐标 / %d 族" % (len(surface), len({o for o in surface.values()})))
    pom, floor_props, fam_artifacts = build_parent_pom(owner, surface, write_mode)
    plans = starter_plan(owner, surface)
    g5_ok = re.search(r"<z-boot\.version>%s</z-boot\.version>" % TRAIN, pom) and \
        ("<version>%s</version>" % TRAIN) in pom.split("<artifactId>z-boot-parent</artifactId>")[1][:200]
    print("G1 地板 yuku=0 ✓  G3 property 合并无冲突 ✓  G4 starter client 全落 pin ✓  G5 同火车 ✓"
          if g5_ok else "守卫有红，见上")
    print("starter 计划: %d 个（client 字面 %d 个 / 无 client %d 个）" % (
        len(plans), len([p for p in plans if p["client"]]), len([p for p in plans if not p["client"]])))

    # 目标 = 本脚本会写的全部文件；脏检查防「pristine 读 HEAD 吃掉未提交手改」
    targets = [os.path.join(PARENT_DIR, "pom.xml")] + [p["path"] for p in plans] + \
              [os.path.join(a, "pom.xml") for a in AGG_DIRS]
    st = subprocess.run(["git", "-C", REPO_ROOT, "status", "--porcelain", "--"] + targets,
                        capture_output=True, text=True)
    dirty = [l[3:] for l in st.stdout.splitlines() if l.strip()]

    if write_mode:
        if dirty:
            print("脏检查红：以下目标有未提交改动（生成读 HEAD，--write 会覆盖它们）：")
            for d in dirty:
                print("   ", d)
            print("先提交（或 stash）再跑 --write。")
            sys.exit(3)
        misses = []
        for f, arts in sorted(fam_artifacts.items()):
            for a in arts:
                if not repo1_exists(a, FAMILIES[f][1]):
                    misses.append("%s:%s" % (a, FAMILIES[f][1]))
        if misses:
            print("G2 红：repo1 取不到 %d 格，拒绝落盘: %s" % (len(misses), ", ".join(misses)))
            sys.exit(2)
        # 先全部算好再落盘：transform 抛异常不许留半截文件
        new_starters = [(p, rewrite_starter(p, owner, surface, fam_artifacts)) for p in plans]
        new_aggs = []
        for agg in AGG_DIRS:
            ap = os.path.join(agg, "pom.xml")
            t = pristine(os.path.relpath(ap, REPO_ROOT))
            new_aggs.append((ap, t.replace("<version>%s</version>" % PREV_TRAIN,
                                           "<version>%s</version>" % TRAIN)))
        with open(os.path.join(PARENT_DIR, "pom.xml"), "w", encoding="utf-8") as fh:
            fh.write(pom)
        for p, new_text in new_starters:
            with open(p["path"], "w", encoding="utf-8") as fh:
                fh.write(new_text)
        for ap, new_text in new_aggs:
            with open(ap, "w", encoding="utf-8") as fh:
                fh.write(new_text)
        print("已落盘: parent %s + %d starter + 2 聚合器。" % (TRAIN, len(plans)))
    else:
        if dirty:
            print("  [warn] 目标有未提交改动（--write 将拒绝落盘）: %s" % ", ".join(dirty))
        print("（--check 模式，未写盘。守卫 G2 的 repo1 探活在 --write 时执行）")


if __name__ == "__main__":
    main()
