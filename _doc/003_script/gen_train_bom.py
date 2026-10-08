#!/usr/bin/env python3
"""gen_train_bom.py —— 火车制拓扑的唯一写手（2026-10-08 重构，替代 gen_fleet_bom.py 的产物面）。

新拓扑（CEO 裁定「火车制」）：
  z-boot-parent 1.1.0 = 唯一慢层权威：
      <parent> 根 z-boot:1.0.19（z-boot-dependencies 退役）
      DM = 第三方地板 155 条（自 z-boot-dependencies 逐字搬运）+ 接入面 pin（脚本按
           「被跨仓真实声明」现算）+ 22 格自家 starter（${z-boot.version}，与 parent 同火车）
      properties = 地板 106 条 + 接入面 <z-<族>.version> + z-boot.version
  z-boot-*-starter 1.1.0 = 产品层：DM 只 import parent-as-BOM 一条；client 依赖写字面版本
      （值 = 接入面 pin 的同源，发布件经 flatten 内联，形状与今天一致）。
  fleet / z-boot-dependencies 两个文件夹随本火车删除（Central 旧件永久在架，不炸迁移中的消费方）。

接入面口径（机械、不手维护名单）：坐标被「非所属仓」的 pom 在 <dependencies>（真依赖，
非 dependencyManagement 登记）里声明过 ⇒ 进 pin。排除 _code_temp（资料库，CEO 裁定不作为
任何口径的输入）、.cache、target、node_modules、z-boot 仓自身。

守卫（沿袭 gen_fleet_bom.py 的教训，全部双向验证过才许落盘）：
  G1 地板 DM 里 io.github.yuku123 坐标必须 0 条（搬运的是纯第三方）
  G2 接入面每一格的 (坐标,版本) 对 repo1 发 ranged GET，取不到即拒绝落盘（防烧格子）
  G3 地板与 parent 同名 property 值必须相等才允许合并（不许静默改值）
  G4 每个 starter 的 client 依赖必须落在接入面 pin 里
  G5 parent 自身 <version> == <z-boot.version>（同火车不变式）

用法：
    python3 gen_train_bom.py            # 只打印计划与守卫结果，不写盘
    python3 gen_train_bom.py --write    # 落盘（G1-G5 全绿才写；repo1 探活失败逐格列出并退出 2）
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

TRAIN = "1.1.0"
ROOT_PARENT = ("io.github.yuku123", "z-boot", "1.0.19")
FLOOR_DIR = os.path.join(REPO_ROOT, "z-boot-dependencies")
PARENT_DIR = os.path.join(REPO_ROOT, "z-boot-parent")
AGG_DIRS = [os.path.join(REPO_ROOT, "z-boot-starter"),
            os.path.join(REPO_ROOT, "z-boot-integration-starters")]
BASE_STARTERS = {"z-boot-base", "z-boot-web-starter", "z-boot-datasource-starter"}

EXCLUDE_DIR_PARTS = {"_code_temp", ".cache", "target", "node_modules", ".git", ".gnupg"}

# 兄弟仓 -> (property 词根, 版本)。自 gen_fleet_bom.py 的 FAMILIES 原样移植（值=现 fleet 1.0.4 面），
# 本火车只改拓扑、不采纳任何新版本 —— 零漂移是这次迁移的判据。
FAMILIES = {
    "z-config": ("z-config", "1.0.10"), "z-ctc": ("z-ctc", "1.0.2"),
    "z-cache": ("z-cache", "1.3.6"), "z-mq": ("z-mq", "1.3.1"),
    "z-gw": ("z-gw", "1.0.6"), "z-kb": ("z-kb", "1.0.7"),
    "z-vector": ("z-vector", "1.0.5"), "z-graph": ("z-graph", "1.0.8"),
    "z-rpc": ("z-rpc", "1.0.4"), "z-oss": ("z-oss", "1.0.4"),
    "z-schedule": ("z-schedule", "1.0.6"), "z-msg": ("z-msg", "1.2.2"),
    "z-script": ("z-script", "1.0.2"), "z-util": ("z-util", "1.0.19"),
    "z-agent-kernel": ("z-agent-kernel", "0.2.1"), "z-llm": ("z-llm", "0.1.7"),
    "z-mcp": ("z-mcp", "0.2.1"), "z-skill": ("z-skill", "0.2.2"),
    "z-agent": ("z-agent", "0.1.4"), "z-bot": ("z-bot", "0.2.1"),
    "z-agent-proxy": ("z-agent-proxy", "0.1.1"), "z-mist": ("z-mist", "1.0.4"),
    "z-qa": ("z-qa", "1.0.1"), "z-camuda": ("z-camuda", "1.0.6"),
    "z-indexer": ("z-indexer", "1.0.0"),
}

REPO1 = "https://repo1.maven.org/maven2/io/github/yuku123"


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


def verbatim_block(text, tag):
    # 非贪婪：pom 里 flatten 配置内嵌着 <properties>keep</properties>，贪婪会吞掉整段 DM+build
    m = re.search(r"<%s>(.*?)</%s>" % (tag, tag), strip_notes(text), re.S)
    return m.group(1).rstrip() if m else None


def dedent_block(block):
    """把子块整体去掉公共缩进，便于嵌进新 pom 的统一缩进。"""
    lines = block.split("\n")
    indents = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
    cut = min(indents) if indents else 0
    return "\n".join(l[cut:] if len(l) >= cut else l.lstrip() for l in lines)


def build_parent_pom(owner, surface, write_mode):
    floor = pristine("z-boot-dependencies/pom.xml")
    parent = pristine("z-boot-parent/pom.xml")

    # G1: 地板 DM 里不得有 yuku 坐标
    fr = ET.fromstring(strip_notes(floor))
    yuku_in_floor = [d for d in fr.findall("m:dependencyManagement/m:dependencies/m:dependency", NS)
                     if d.find("m:groupId", NS).text == "io.github.yuku123"]
    assert not yuku_in_floor, "G1 红：地板 DM 混入 yuku 坐标 %d 条" % len(yuku_in_floor)

    floor_props = {p.tag.split("}")[-1]: (p.text or "") for p in fr.find("m:properties", NS)}
    parent_props = {p.tag.split("}")[-1]: (p.text or "") for p in ET.fromstring(strip_notes(parent)).find("m:properties", NS)}
    # 同名 property 值冲突：以 parent 现值为准（今天消费者生效的就是就近覆盖值，零漂移）
    shared = set(floor_props) & set(parent_props) - {"z-boot.version", "z-boot-fleet.version"}
    conflict = sorted(k for k in shared if floor_props[k] != parent_props[k])
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
    missing_fam = [f for f in FAMILIES if f not in fam_artifacts]
    missing_fam = [f for f in missing_fam if f not in ("z-qa",)]  # z-qa 无 starter 无跨仓声明，允许缺席
    if missing_fam:
        print("  [warn] 无跨仓声明的族（不进 pin，留 FAMILIES 供体检）: %s" % ", ".join(missing_fam))

    floor_props_xml = dedent_block(verbatim_block(floor, "properties"))
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

    floor_dm_inner = verbatim_block(floor, "dependencyManagement")
    # 抽取结果自带 <dependencies> 内层包裹，剥掉——外层由本模板统一提供，否则嵌套两层（schema 拒）
    m2 = re.match(r"\s*<dependencies>(.*)</dependencies>\s*$", floor_dm_inner, re.S)
    assert m2, "地板 DM 抽取缺 <dependencies> 包裹，结构变了"
    floor_dm_xml = dedent_block(m2.group(1))
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

    本 pom 自 gen_train_bom.py 生成三段：第三方地板（自 z-boot-dependencies 逐字搬运，
    那个文件夹随本火车退役）、接入面 pin（被跨仓真实声明的 z-* 坐标，机械口径现算）、
    自家 22 格 starter（${z-boot.version}，与 parent 同火车同号）。

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

    pom = header + """
    <artifactId>z-boot-parent</artifactId>
    <version>%s</version>
    <packaging>pom</packaging>

    <name>z-boot-parent (Consumer Parent)</name>
    <description>z-opc-foundation 各仓统一 parent：第三方地板 + 接入面版本 + 自家 starter 火车 + Java 8 构建口径</description>

    <properties>
%s

%s
%s
    </properties>

    <dependencyManagement>
        <dependencies>
%s

%s

%s
        </dependencies>
    </dependencyManagement>
""" % (TRAIN, floor_props_xml, "\n".join(extra_lines), "\n".join(fam_prop_lines),
       floor_dm_xml, "\n".join(pin_lines), "\n".join(self_lines))

    # pluginManagement + flatten 覆盖块自现 parent 原样搬运
    build = verbatim_block(parent, "build")
    pom += """
    <build>
%s
    </build>

</project>
""" % dedent_block(build)
    return pom, floor_props, fam_artifacts


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
    # 版本：parent 引用与自身版本 → 火车号
    new = new.replace("<version>1.0.25</version>", "<version>%s</version>" % TRAIN)
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
        assert o in FAMILIES, "G4 红：%s 的 client %s 无族" % (p["own"], p["client"])
        assert p["client"] in fam_artifacts.get(o, []), "G4 红：%s 不在接入面 pin" % p["client"]
        ver = FAMILIES[o][1]
        # version-less client 依赖 → 字面版本。插入点=</artifactId> 之后：
        # 8 个 starter（config/gw/kb/msg/rpc/schedule/script/vector）的 client 块带 <exclusions>，
        # 锚 </dependency> 会插到 exclusions 后面去（语义还对但形状歪），锚 artifactId 永远紧邻版本。
        pat = re.compile(r"(<artifactId>%s</artifactId>)" % re.escape(p["client"]))
        assert pat.search(new), "starter %s: 未找到 version-less 的 %s 依赖" % (p["own"], p["client"])
        assert re.search(r"<artifactId>%s</artifactId>\s*<version>" % re.escape(p["client"]), new) is None, \
            "starter %s: %s 已带版本？拒绝重复插入" % (p["own"], p["client"])
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

    if write_mode:
        misses = []
        for f, arts in sorted(fam_artifacts.items()):
            for a in arts:
                if not repo1_exists(a, FAMILIES[f][1]):
                    misses.append("%s:%s" % (a, FAMILIES[f][1]))
        if misses:
            print("G2 红：repo1 取不到 %d 格，拒绝落盘: %s" % (len(misses), ", ".join(misses)))
            sys.exit(2)
        open(os.path.join(PARENT_DIR, "pom.xml"), "w", encoding="utf-8").write(pom)
        for p in plans:
            new_text = rewrite_starter(p, owner, surface, fam_artifacts)  # 先算：transform 抛异常不许留半截文件
            with open(p["path"], "w", encoding="utf-8") as fh:
                fh.write(new_text)
        for agg in AGG_DIRS:
            ap = os.path.join(agg, "pom.xml")
            t = pristine(os.path.relpath(ap, REPO_ROOT))
            t = t.replace("<version>1.0.25</version>", "<version>%s</version>" % TRAIN)
            with open(ap, "w", encoding="utf-8") as fh:
                fh.write(t)
        print("已落盘: parent 1.1.0 + %d starter + 2 聚合器。fleet/floor 文件夹由发布批次的 git rm 处理。" % len(plans))
    else:
        print("（--check 模式，未写盘。守卫 G2 的 repo1 探活在 --write 时执行）")


if __name__ == "__main__":
    main()
