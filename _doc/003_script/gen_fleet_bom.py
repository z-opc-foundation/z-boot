#!/usr/bin/env python3
"""生成 z-boot-fleet/pom.xml —— 兄弟仓(z-* L3)版本权威 BOM。

为什么要有这支脚本:fleet 的每一格都必须"repo1 上真的有这个坐标+这个版本"才写得进去。
手抄清单会漂(1.0.16 那阵子 README 少记两格就是手抄的账),所以坐标清单从兄弟仓盘上
的 pom 现取,版本逐件 HEAD repo1 复核;取不到的一律不进 BOM,只在报告里列出来。

同一支脚本也负责 z-boot-parent 里"自家 starter"那一段(--write-parent):清单按两个
聚合 pom 的 <modules> 现取(被注释掉的模块因为 XML 解析天然跳过),版本 = parent 自己的
<version>,逐件核 repo1。为什么自家坐标进 parent 而不是进 fleet:fleet 是"抬一格重发一次"
的独立发布件,而 z-boot 的 starter 只能和 z-boot 同版本 —— 钉在 parent 里,发版时一起动,
没有第二把可以漂的尺。

用法:
    python3 _doc/003_script/gen_fleet_bom.py            # 只打印报告,不写文件
    python3 _doc/003_script/gen_fleet_bom.py --write     # 写 z-boot-fleet/pom.xml
                                                       # 有 PENDING 格时拒绝落盘,除非加 --allow-pending
    python3 _doc/003_script/gen_fleet_bom.py --parent      # 只看 parent 自家段的账
    python3 _doc/003_script/gen_fleet_bom.py --write-parent  # 写 z-boot-parent 的自家段(同样带守卫)
"""
import concurrent.futures as cf
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

NS = "{http://maven.apache.org/POM/4.0.0}"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FOUNDATION = os.path.abspath(os.path.join(REPO_ROOT, ".."))
BASE = "https://repo1.maven.org/maven2/io/github/yuku123/"

# 兄弟仓 -> (fleet property 名, 目标版本)。property 名即 <z-xxx.version>。
#
# 【这一版把每一格抬到 repo1 现读的 max release】四特性审计（2026-09-29）实测 fleet:1.0.0 的 21 格
# 相对中央**一格都不领先、全部落后**（P4 同版率 0/21），后果是"继承 parent 的仓拿到的兄弟版永远比
# 中央旧一号"。抬每一格前先按 maven-metadata.xml 复量，别照抄下面这列。
#
# 【新增了四族】z-mist / z-qa / z-camuda / z-indexer：前三族中央上早就有发布件（1.0.4 / 1.0.1 / 1.0.6，
# maven-metadata 现读），却从来没进过 FAMILIES ⇒ 消费方 import fleet 也拿不到它们的版本格，
# 只能各仓自己钉字面值（z-opc 那份 DM 里 z-mist-web 1.0.2、z-camuda-starter 1.0.5 就是这么来的，
# 而且一钉就是落后三版）。漏登记不是"这些仓不重要"，是清单手抄的账 —— 见本脚本顶部注释。
FAMILIES = {
    "z-config":  ("z-config",  "1.0.9"),
    # 1.0.1 那格的旧注释（"repo1 实测 404 ⇒ 那一版没落进 Central"）已经不成立：
    # z-ctc/maven-metadata.xml 现读 latest=release=1.0.2 ⇒ 1.0.19 批次里 z-ctc 真发出去了，
    # 这一格跟着抬。（z-ctc-admin 仍不发布，见 SKIP_ARTIFACTS。）
    "z-ctc":     ("z-ctc",     "1.0.2"),
    "z-cache":   ("z-cache",   "1.3.6"),
    "z-mq":      ("z-mq",      "1.3.1"),
    "z-gw":      ("z-gw",      "1.0.5"),
    # 1.0.5 是缺陷 2 的那一版：AutoConfiguration.imports 从伪 src 路径搬进各模块的
    # src/main/resources，两个 spring.factories（正文只有裸类名、没有 key，加载器根本读不到）
    # 换成 .imports ⇒ 本仓 starter 第一次能"引入即装配"。1.0.4 已在中央但内容是坏的，
    # Central 不许覆盖，只能抬号重发。
    "z-kb":      ("z-kb",       "1.0.7"),
    "z-vector":  ("z-vector",   "1.0.5"),
    # 1.0.6 是"移植中途发出去的半成品"(api/protocol=52 而 core/bolt/starter=61),Central 不许覆盖
    # ⇒ 永久作废。1.0.7 是 Java 8 线的那一版,z-graph 仓 2026-09-28 发到 repo1(实测 200),已抬。
    "z-graph":   ("z-graph",    "1.0.8"),
    "z-rpc":     ("z-rpc",      "1.0.4"),
    "z-oss":     ("z-oss",      "1.0.4"),
    "z-schedule":("z-schedule", "1.0.6"),
    "z-msg":     ("z-msg",      "1.2.2"),
    "z-script":  ("z-script",   "1.0.1"),
    "z-util":    ("z-util",     "1.0.18"),
    "z-agent-kernel": ("z-agent-kernel", "0.2.1"),
    "z-llm":     ("z-llm",      "0.1.7"),
    # 0.2.1 = 发布 pom 改 flattenMode oss 的那一版（缺陷 3：resolveCiFriendliesOnly 留下的
    # <parent> + 无版本 dependency 要消费者自己走父链）。中央现存 0.2.0 是旧形状。
    "z-mcp":     ("z-mcp",      "0.2.1"),
    "z-skill":   ("z-skill",    "0.2.2"),
    "z-agent":   ("z-agent",    "0.1.4"),
    "z-bot":     ("z-bot",      "0.2.0"),
    "z-agent-proxy": ("z-agent-proxy", "0.1.1"),
    "z-mist":    ("z-mist",     "1.0.4"),
    "z-qa":      ("z-qa",       "1.0.1"),
    "z-camuda":  ("z-camuda",   "1.0.6"),
    # 首发（缺陷 7：中央 404，因为本仓原来既没有 central profile 也没有仓级元数据，
    # 根本没有发布通道）。z-indexer-server 是进程模块，见 SKIP_ARTIFACTS。
    "z-indexer": ("z-indexer",  "1.0.0"),
}
# fleet 自己的版本号。⚠ 每次 --write 改了内容，这一格必须一起抬：Central 不许覆盖已发布
# 版本，重发同号只会 400，而 400 之前你已经把一个"发不出去的 fleet"当权威用了一轮。
# 落盘前脚本会回读 repo1 确认这一格还空着(见 main 的守卫)。
# 1.0.1：内容变了（21 格全部抬到 repo1 现读值 + 新增 4 族）⇒ 必须抬号。
FLEET_VERSION = "1.0.3"

# 这些仓不是"目录=模块"的形状,坐标由人工登记(单模块仓或 artifactId 与仓名不同)。
EXTRA = {
    "z-agent-proxy": ["z-agent-proxy"],
    "z-bot": ["z-bot-core"],
}
# 不作为受管坐标发布的模块后缀(示例/引导/前端)
# z-msg-example 是示例工程(兄弟仓自己 install 过所以本地能查到),从来不上 Central —— 留在清单里
# 只会永久挂一个 PENDING,把 --write 的守卫变成噪音。
# z-ctc-admin 同理:2026-09-28 起被 z-ctc 的 excludeArtifacts 挡在 bundle 外,永不发布。
# z-indexer-server 同理:可执行进程（application.yaml + 59MB 内置工具链），被 z-indexer 根 pom
# central profile 的 excludeArtifacts 挡在 bundle 外，永不发布 —— 但 sibling_artifacts() 是扫
# 目录的，不看 excludeArtifacts，不登记这里就会永久挂一个 MISSING 让守卫变成噪音。
# z-script-admin / z-camuda-admin 是 2026-09-29 现读到的两格：两个仓的根 pom 都写了 excludeArtifacts
# (z-script/pom.xml:381、z-camuda/pom.xml:294)，可 sibling_artifacts() 的目录扫描照旧把它们端上来，
# 而 ~/.m2 里有上一轮 install 的旧件 ⇒ exists() 判 PENDING，直接把 --write 的守卫卡在"你钉了一个
# 永不发布的坐标"上。MISSING 的那些 admin（z-config/z-rpc/z-schedule/z-mist）没人 install 过，
# 天然被丢掉，所以只有这两格需要点名。
# (其余 *-admin / *-examples 是 repo1 上 MISSING,天然被丢掉了 —— 写明白省得下回靠运气)
SKIP_ARTIFACTS = {"z-gw-examples", "z-rpc-examples", "bootstrap-gennerate",
                  "z-msg-example", "z-ctc-admin", "z-indexer-server",
                  "z-script-admin", "z-camuda-admin"}


def art_text(p):
    return re.sub(r"<!--.*?-->", "", open(p, encoding="utf-8").read(), flags=re.S)


def sibling_artifacts(repo):
    """该兄弟仓在目标版本上应发布的 artifactId 清单(取 jar 模块,排除聚合 pom)。"""
    root = os.path.join(FOUNDATION, repo)
    out = list(EXTRA.get(repo, []))
    if not os.path.isdir(root):
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("target", "node_modules", ".git", "src", "_frontend", "bin")]
        if "pom.xml" not in filenames:
            continue
        p = os.path.join(dirpath, "pom.xml")
        try:
            r = ET.fromstring(art_text(p))
        except ET.ParseError:
            continue
        if r.find(NS + "artifactId") is None:
            continue
        aid = r.findtext(NS + "artifactId", "").strip()
        pk = r.findtext(NS + "packaging", "jar").strip()
        if pk != "jar" or not aid.startswith("z-") or aid in SKIP_ARTIFACTS:
            continue
        if aid not in out:
            out.append(aid)
    return sorted(out)


def exists(aid, ver):
    """repo1 上是否有该坐标的发布件;刚上传还没进索引的,用本地 ~/.m2 兜底(报告里标 PENDING)。

    ⚠ 用 ranged GET 而不是 HEAD:repo1(Fastly)对 HEAD 一律不回 200,拿 HEAD 量会把
    已经发布成功的坐标全判成"取不到"。
    """
    for ext in (".jar", ".pom"):
        code = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                               "-r", "0-0", "--max-time", "25", f"{BASE}{aid}/{ver}/{aid}-{ver}{ext}"],
                              capture_output=True, text=True).stdout.strip()
        if code in ("200", "206"):
            return "OK"
    m2 = os.path.expanduser(f"~/.m2/repository/io/github/yuku123/{aid}/{ver}")
    if os.path.isdir(m2) and any(f.endswith((".jar", ".pom")) for f in os.listdir(m2)):
        return "PENDING"
    return "MISSING"


PARENT_BEGIN = "<!-- BEGIN z-boot-self"
PARENT_END = "<!-- END z-boot-self"
SELF_AGGREGATORS = ("z-boot-starter", "z-boot-integration-starters")


def self_starter_artifacts():
    """z-boot 自家要发布的 starter:取两个聚合 pom 的 <modules>,逐个读 artifactId。

    走 <modules> 而不是扫目录:被注释掉的模块(如 z-tool-webide-spring-boot-starter,它还在
    等 z-webide 以 io.github.yuku123 发中央)天然跳过 —— 扫目录会把它当成"该发而没发"。
    """
    arts = []
    for agg in SELF_AGGREGATORS:
        p = os.path.join(REPO_ROOT, agg, "pom.xml")
        if not os.path.isfile(p):
            continue
        r = ET.fromstring(art_text(p))
        mods = r.find(NS + "modules")
        if mods is None:
            continue
        for m in mods.findall(NS + "module"):
            d = (m.text or "").strip()
            mp = os.path.join(REPO_ROOT, agg, d, "pom.xml")
            if not os.path.isfile(mp):
                sys.stderr.write("WARN <module>%s</module> 在 %s 下没有 pom.xml\n" % (d, agg))
                continue
            mr = ET.fromstring(art_text(mp))
            aid = (mr.findtext(NS + "artifactId", "") or "").strip()
            pk = (mr.findtext(NS + "packaging", "jar") or "jar").strip()
            if aid and pk == "jar":
                arts.append(aid)
    return sorted(set(arts))


def write_parent(report_only=True):
    """重算 z-boot-parent 的自家 starter 段。守卫与 fleet 同一套:发不出去的坐标不钉版本。"""
    pp = os.path.join(REPO_ROOT, "z-boot-parent", "pom.xml")
    if not os.path.isfile(pp):
        sys.stderr.write("找不到 %s\n" % pp)
        return 2
    root = ET.fromstring(art_text(pp))
    parent_ver = (root.findtext(NS + "version", "") or "").strip()
    props = root.find(NS + "properties")
    prop_ver = (props.findtext(NS + "z-boot.version", "") or "").strip() if props is not None else ""
    if parent_ver != prop_ver:
        sys.stderr.write("✗ z-boot-parent 的 <version>(%s) 与 <z-boot.version>(%s) 不同格 —— "
                         "自家 starter 只能和 parent 一起发版,这两处必须同值。\n"
                         % (parent_ver, prop_ver))
        return 2

    arts = self_starter_artifacts()
    with cf.ThreadPoolExecutor(24) as ex:
        rows = list(zip(arts, ex.map(lambda a: exists(a, parent_ver), arts)))
    keep = [a for a, s in rows if s in ("OK", "PENDING")]
    pend = [a for a, s in rows if s == "PENDING"]
    drop = [(a, s) for a, s in rows if s == "MISSING"]
    print("z-boot-parent 自家 starter @%s:盘上 %d 个 / 收 %d 个" % (parent_ver, len(arts), len(keep)))
    if pend:
        print("  PENDING(本地有、repo1 还没进索引): %s" % ",".join(pend))
    if drop:
        print("  丢弃(repo1 取不到): %s" % drop)

    if report_only:
        print("(dry-run;--write-parent 才落盘)")
        return 0
    if pend and "--allow-pending" not in sys.argv:
        sys.stderr.write("✗ 拒绝落盘:上面这些 PENDING 坐标在 repo1 上还取不到(通常是那个文件夹还没发),"
                         "钉进 parent 就是让外部消费方 404,而 Central 不许覆盖 —— 只能作废整格重发。\n"
                         "   先把 z-boot-integration-starters 发出去、ranged GET 见 200,再重跑。\n")
        return 2

    block = ["            <!-- z-boot %s:清单取自 %s 的 <modules>,版本逐件核过 repo1 -->"
             % (parent_ver, " + ".join(SELF_AGGREGATORS))]
    for a in keep:
        block += ['            <dependency>',
                  '                <groupId>io.github.yuku123</groupId>',
                  '                <artifactId>%s</artifactId>' % a,
                  '                <version>${z-boot.version}</version>',
                  '            </dependency>']

    lines = open(pp, encoding="utf-8").read().split("\n")
    try:
        i = next(n for n, l in enumerate(lines) if PARENT_BEGIN in l)
        j = next(n for n, l in enumerate(lines) if PARENT_END in l)
    except StopIteration:
        sys.stderr.write("✗ %s 里找不到 %r / %r 标记,不敢乱写。\n" % (pp, PARENT_BEGIN, PARENT_END))
        return 2
    out = lines[:i + 1] + block + lines[j:]
    open(pp, "w", encoding="utf-8").write("\n".join(out))
    validate_pom(pp)
    print("written: %s(%d 条)" % (pp, len(keep)))
    return 0


def live_on_central(aid, ver):
    """只对 repo1 量"这一格是不是已经被占"，不吃 ~/.m2 兜底。

    为什么单独一支:exists() 会把"本地 install 过"报成 PENDING —— 对受管坐标是对的(内容能用)，
    但对"这个版本号还能不能发"是错的。实测 z-boot-fleet:1.0.0 在 ~/.m2 里躺着(上一轮 install 的)，
    repo1 却是 404 ⇒ 拿 exists() 量会把一次合法的首发拦死。
    """
    for ext in (".jar", ".pom"):
        code = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                               "-r", "0-0", "--max-time", "25", f"{BASE}{aid}/{ver}/{aid}-{ver}{ext}"],
                              capture_output=True, text=True).stdout.strip()
        if code in ("200", "206"):
            return True
    return False


def validate_pom(path):
    """落盘后立刻用 XML 解析器复量一遍。

    为什么必须有:注释里出现两个连字符是**非法 XML**,而本脚本的注释爱写命令行开关
    (`--write-parent` 这种)—— 2026-09-28 就这么把 z-boot-parent/pom.xml 写成了
    "Non-parseable POM ... next character must be > not w",mvn 连模型都读不起来。
    报告里写得再漂亮,文件解析不了就是零。
    """
    try:
        ET.parse(path)
    except ET.ParseError as ex:
        sys.stderr.write("✗ %s 写完解析不了(%s)—— 十有八九是注释里出现了 --，XML 注释非法。"
                         "把措辞改成'的 write-parent'这类写法再来。\n" % (path, ex))
        sys.exit(4)


def main():
    if "--parent" in sys.argv or "--write-parent" in sys.argv:
        sys.exit(write_parent(report_only="--write-parent" not in sys.argv))
    write = "--write" in sys.argv
    families, report = {}, []
    with cf.ThreadPoolExecutor(24) as ex:
        jobs = [(repo, aid, ver) for repo, (_, ver) in FAMILIES.items() for aid in sibling_artifacts(repo)]
        results = list(ex.map(lambda j: (j[0], j[1], j[2], exists(j[1], j[2])), jobs))
    for repo, (prop, ver) in FAMILIES.items():
        rows = [r for r in results if r[0] == repo]
        keep = [r[1] for r in rows if r[3] in ("OK", "PENDING")]
        drop = [(r[1], r[3]) for r in rows if r[3] == "MISSING"]
        families[repo] = (prop, ver, keep)
        pend = [r[1] for r in rows if r[3] == "PENDING"]
        report.append(f"{repo:16s} {prop}.version={ver:8s} 收 {len(keep):2d} 件"
                      + (f"  PENDING(已上传未进索引): {','.join(pend)}" if pend else "")
                      + (f"  丢弃: {drop}" if drop else ""))

    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<project xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
           '         xmlns="http://maven.apache.org/POM/4.0.0"',
           '         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">',
           '    <modelVersion>4.0.0</modelVersion>',
           '    <parent>',
           '        <groupId>io.github.yuku123</groupId>',
           '        <artifactId>z-boot</artifactId>',
           '        <version>1.0.19</version>',
           '        <relativePath>../pom.xml</relativePath>',
           '    </parent>',
           '',
           '    <artifactId>z-boot-fleet</artifactId>',
           '    <version>%s</version>' % FLEET_VERSION,
           '    <packaging>pom</packaging>',
           '    <name>z-boot-fleet (L3 Sibling Version Authority)</name>',
           '    <description>',
           '        z-opc-foundation 兄弟仓 (z-config / z-cache / z-mq / z-gw / z-kb / z-vector / z-graph /',
           '        z-rpc / z-oss / z-schedule / z-msg / z-script / z-ctc / z-util / L3 Agent-AI 7 仓) 的版本权威。',
           '        与 z-boot-dependencies (第三方地板) 分家:抬任何一格兄弟仓版本只需要重发本 pom 一个文件夹,',
           '        不牵动第三方地板。z-boot 自家的 z-boot-*-starter 不在这里 —— 它们只能和 z-boot 同版本,',
           '        所以钉在 z-boot-parent。本文件由 _doc/003_script/gen_fleet_bom.py',
           '        生成 —— 坐标清单取自兄弟仓盘上的 pom,版本逐件对 repo1 复核过,别手改。',
           '    </description>',
           '',
           '    <properties>',
           '        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>',
           '        <maven.compiler.source>8</maven.compiler.source>',
           '        <maven.compiler.target>8</maven.compiler.target>',
           '        <!-- 对账基准 = repo1 每个 L3 坐标的 maven-metadata(<latest> 与 <versions> 最大值都算,',
           '             因为 Central 的 <latest> 是"最后部署"不是"版本号最大")。',
           '             ⚠ 抬任何一格都先重跑本脚本:它逐件 HEAD repo1,发不出去/没索引的坐标一律不写进 BOM,',
           '             手抄清单当分叉账在 1.0.16 上翻过车(README 少记 llm/skill 两格)。',
           '             PENDING = 已上传但 Central 尚未进索引,发布 fleet 前必须回看成 200。 -->']
    for repo, (prop, ver, arts) in families.items():
        if not arts:
            continue
        xml.append(f'        <{prop}.version>{ver}</{prop}.version>')
    xml.append('    </properties>')
    xml.append('')
    xml.append('    <dependencyManagement>')
    xml.append('        <dependencies>')
    for repo, (prop, ver, arts) in families.items():
        if not arts:
            continue
        xml.append(f'            <!-- {repo} {ver} -->')
        for aid in arts:
            xml += ['            <dependency>',
                    '                <groupId>io.github.yuku123</groupId>',
                    f'                <artifactId>{aid}</artifactId>',
                    f'                <version>${{{prop}.version}}</version>',
                    '            </dependency>']
    xml += ['        </dependencies>', '    </dependencyManagement>', '']
    # BOM 必须用 resolveCiFriendliesOnly:oss 模式会把整个 dependencyManagement 剥掉
    # (同一个坑见 z-boot-dependencies/pom.xml 尾注),剥掉之后叶子 import 不到任何兄弟仓版本。
    xml += ['    <build>', '        <plugins>', '            <plugin>',
            '                <groupId>org.codehaus.mojo</groupId>',
            '                <artifactId>flatten-maven-plugin</artifactId>',
            '                <configuration>',
            '                    <flattenMode>resolveCiFriendliesOnly</flattenMode>',
            '                </configuration>',
            '            </plugin>', '        </plugins>', '    </build>', '', '</project>', '']
    text = "\n".join(xml)

    print("\n".join(report))
    total = sum(len(v[2]) for v in families.values())
    print(f"\nfleet 合计 {total} 个受管坐标 / {len(FAMILIES)} 个版本格")
    target = os.path.join(REPO_ROOT, "z-boot-fleet", "pom.xml")
    if write:
        # 守卫零:fleet 自己那一格还空着吗?Central 不许覆盖,拿一个已发布的版本号重发只会 400,
        # 而 400 之前你已经把这份"发不出去"的清单当权威用了一轮。
        if live_on_central("z-boot-fleet", FLEET_VERSION):
            sys.stderr.write("✗ z-boot-fleet:%s 在 repo1 上已经占用了(或刚上传)。内容变了要抬版本 ⇒ 改本脚本顶部的 "
                             "FLEET_VERSION,同时把 z-boot-parent 的 <z-boot-fleet.version> 一起改;"
                             "抬上去的那一格还要重跑 gen_fleet_bom.py --write-parent 之外的 publish 顺序。\n"
                             % FLEET_VERSION)
            sys.exit(3)
        # 守卫〇bis:parent 引用的是哪一格 fleet?两边不一致就是"parent 导进来一份没人维护的旧权威"
        pp = os.path.join(REPO_ROOT, "z-boot-parent", "pom.xml")
        if os.path.isfile(pp):
            prow = ET.fromstring(art_text(pp))
            pprops = prow.find(NS + "properties")
            pref = (pprops.findtext(NS + "z-boot-fleet.version", "") or "").strip() if pprops is not None else ""
            if pref != FLEET_VERSION:
                sys.stderr.write("✗ z-boot-parent 的 <z-boot-fleet.version>(%s) 与 fleet 自己要发的版本(%s)不同格。\n"
                                 % (pref or "(缺)", FLEET_VERSION))
                sys.exit(3)
        # 守卫〇ter:每一份 starter pom 里那句字面 `import z-boot-fleet:<号>`。
        #
        # 为什么必须有这条 —— 守卫〇bis 只看 parent，漏掉了 starter，而**绝大多数消费者走的是
        # starter**（z-boot-kb-starter / z-boot-cache-starter / … 23 份）。
        # 实测踩过：cd3cfea 把 fleet 抬到 1.0.2，只改了 fleet 自己的 pom 和
        # z-boot-web-starter 一处，其余 22 份 starter 字面 import 仍是 1.0.1。
        # 抬号传播不上去 = 消费方拿到的还是旧权威，而"fleet 已发布"这件事在闸门里是绿的
        # （它只验该坐标该版本能不能拉到，不验该版本内容新不新）。
        # 于是只抬 FLEET_VERSION 就能让两道守卫全过、原样把同一个 bug 重演一遍。
        stale = []
        for container in ("z-boot-integration-starters", "z-boot-starter"):
            cdir = os.path.join(REPO_ROOT, container)
            if not os.path.isdir(cdir):
                continue
            # ⚠ starter 的 pom 在 <container>/<starter>/pom.xml，**比 container 深一层**。
            #   第一版这里只判 os.path.basename(d) in (container,...)，
            #   于是 22 份 starter 一个都没进循环、守卫静默空转放行（实测撞到）。
            for d, _sub, files in os.walk(cdir):
                if "pom.xml" not in files:
                    continue
                sp = os.path.join(d, "pom.xml")
                sroot = ET.fromstring(art_text(sp))
                sdm = sroot.find(NS + "dependencyManagement")
                if sdm is None:
                    continue
                for dnode in sdm.iter(NS + "dependency"):
                    a = dnode.find(NS + "artifactId")
                    v = dnode.find(NS + "version")
                    if (a is not None and v is not None
                            and (a.text or "").strip() == "z-boot-fleet"):
                        lit = (v.text or "").strip()
                        if lit != FLEET_VERSION:
                            stale.append("%s  import z-boot-fleet:%s" % (os.path.relpath(sp, REPO_ROOT), lit))
        if stale:
            sys.stderr.write(
                "✗ 有 %d 份 starter pom 里的字面 import 还停在别的版本，与 fleet 要发的 %s 不同格。\n"
                "  抬 fleet 传播不到走 starter 的消费者（那才是大多数）⇒ 这些字面量必须一起改。\n"
                % (len(stale), FLEET_VERSION)
                + "".join("    %s\n" % x for x in sorted(stale))
                + "  改完再跑一次。\n")
            sys.exit(3)
        # 守卫〇quater:每份 starter 的 **<parent> 版本必须等于它自己的 <version>**。
        #
        # 为什么要独立一条 —— 同一条不变式("starter 与聚合件同版本")有**三个可观测面**:
        # 字面 import(fleet 那格)、<parent><version>、自身 <version>。守卫〇ter 只断第一个。
        # 实测 2026-10-06 踩到的就是后两个:23 份 starter 自身全抬到 1.0.23,<parent> 全停在 1.0.22。
        #
        # 后果比"版本号没同步"重得多:relativePath 与 <parent> 版本不符时,Maven 会**放弃相对路径**、
        # 转去仓库解析旧聚合件,子件因此继承到上一版的 dependencyManagement。症状是
        # "'dependencies.dependency.version' for z-boot-jackson-starter is missing" ——
        # 跟"版本没同步"看不出任何关系,当年就是这么绕了很久。
        misparent = []
        for container in ("z-boot-integration-starters", "z-boot-starter"):
            cdir = os.path.join(REPO_ROOT, container)
            if not os.path.isdir(cdir):
                continue
            for d, _sub, files in os.walk(cdir):
                if "pom.xml" not in files:
                    continue
                sp = os.path.join(d, "pom.xml")
                sroot = ET.fromstring(art_text(sp))
                own = (sroot.findtext(NS + "version", "") or "").strip()
                par = sroot.find(NS + "parent")
                if not own or par is None:
                    continue
                pa = (par.findtext(NS + "artifactId", "") or "").strip()
                pv = (par.findtext(NS + "version", "") or "").strip()
                # 只管 parent 指向本仓两个聚合件的;z-tool-webide 那类外来件不在其列
                if pa != container or pv == own:
                    continue
                misparent.append("%s  <parent>%s:%s  自身 %s"
                                 % (os.path.relpath(sp, REPO_ROOT), pa, pv, own))
        if misparent:
            sys.stderr.write(
                "✗ 有 %d 份 starter 的 <parent> 版本与自身版本不同格。\n"
                "  relativePath 与 <parent> 版本不符时 Maven 会放弃相对路径、去仓库解析旧聚合件,\n"
                "  子件于是继承到上一版的 dependencyManagement(症状是某个依赖 version is missing)。\n"
                % len(misparent)
                + "".join("    %s\n" % x for x in sorted(misparent))
                + "  改成同格再跑一次。\n")
            sys.exit(3)
        pending = {}
        for r in results:
            if r[3] == "PENDING":
                pending.setdefault(r[0], []).append(r[1])
        if pending and "--allow-pending" not in sys.argv:
            print("\n✗ 拒绝落盘:下面这些格在 repo1 上还取不到(已上传未进索引,或压根没发出去),"
                  "写进 fleet 就是钉一个不存在的版本 —— 消费方解析失败,而 Central 不许覆盖已发布版本,"
                  "作废这一格只能靠抬版本号重发。\n"
                  + "\n".join(f"    {k}: {','.join(v)}" for k, v in pending.items())
                  + "\n  等索引(用 ranged GET 复核 200)后重跑;确认承担风险才加 --allow-pending。")
            sys.exit(2)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        open(target, "w", encoding="utf-8").write(text)
        validate_pom(target)
        print(f"written: {target}")
    else:
        print(f"(dry-run;--write 才落盘,目标 {target})")


if __name__ == "__main__":
    main()
