#!/usr/bin/env python3
"""生成 z-boot-fleet/pom.xml —— 兄弟仓(z-* L3)版本权威 BOM。

为什么要有这支脚本:fleet 的每一格都必须"repo1 上真的有这个坐标+这个版本"才写得进去。
手抄清单会漂(1.0.16 那阵子 README 少记两格就是手抄的账),所以坐标清单从兄弟仓盘上
的 pom 现取,版本逐件 HEAD repo1 复核;取不到的一律不进 BOM,只在报告里列出来。

用法:
    python3 _doc/003_script/gen_fleet_bom.py            # 只打印报告,不写文件
    python3 _doc/003_script/gen_fleet_bom.py --write     # 写 z-boot-fleet/pom.xml
                                                       # 有 PENDING 格时拒绝落盘,除非加 --allow-pending
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
FAMILIES = {
    "z-config":  ("z-config",  "1.0.8"),
    # 1.0.2 在 z-ctc 仓的 pom 里是 <revision>,但 repo1 实测 404(z-ctc-1.0.2.pom 与
    # z-ctc-core-1.0.2.pom 都是;1.0.1 探活 206) ⇒ 那一版没落进 Central。fleet 只能钉实测存在的
    # 版本,等 z-ctc 真发出 1.0.2/1.0.3 再重算抬格。
    "z-ctc":     ("z-ctc",     "1.0.1"),
    "z-cache":   ("z-cache",   "1.3.5"),
    "z-mq":      ("z-mq",      "1.3.0"),
    "z-gw":      ("z-gw",       "1.0.4"),
    "z-kb":      ("z-kb",       "1.0.3"),
    "z-vector":  ("z-vector",   "1.0.4"),
    # 1.0.6 是"移植中途发出去的半成品"(api/protocol=52 而 core/bolt/starter=61),Central 不许覆盖
    # ⇒ 永久作废。1.0.7 是 Java 8 线的那一版,z-graph 仓 2026-09-28 发到 repo1(实测 200),已抬。
    "z-graph":   ("z-graph",    "1.0.7"),
    "z-rpc":     ("z-rpc",      "1.0.3"),
    "z-oss":     ("z-oss",      "1.0.3"),
    "z-schedule":("z-schedule", "1.0.5"),
    "z-msg":     ("z-msg",      "1.2.1"),
    "z-script":  ("z-script",   "1.0.0"),
    "z-util":    ("z-util",     "1.0.13"),
    "z-agent-kernel": ("z-agent-kernel", "0.1.1"),
    "z-llm":     ("z-llm",      "0.1.6"),
    "z-mcp":     ("z-mcp",      "0.1.2"),
    "z-skill":   ("z-skill",    "0.2.0"),
    "z-agent":   ("z-agent",    "0.1.2"),
    "z-bot":     ("z-bot",      "0.1.0"),
    "z-agent-proxy": ("z-agent-proxy", "0.1.0"),
}
# 这些仓不是"目录=模块"的形状,坐标由人工登记(单模块仓或 artifactId 与仓名不同)。
EXTRA = {
    "z-agent-proxy": ["z-agent-proxy"],
    "z-bot": ["z-bot-core"],
}
# 不作为受管坐标发布的模块后缀(示例/引导/前端)
# z-msg-example 是示例工程(兄弟仓自己 install 过所以本地能查到),从来不上 Central —— 留在清单里
# 只会永久挂一个 PENDING,把 --write 的守卫变成噪音。
# z-ctc-admin 同理:2026-09-28 起被 z-ctc 的 excludeArtifacts 挡在 bundle 外,永不发布。
# (其余 *-admin / *-examples 是 repo1 上 MISSING,天然被丢掉了 —— 写明白省得下回靠运气)
SKIP_ARTIFACTS = {"z-gw-examples", "z-rpc-examples", "bootstrap-gennerate",
                  "z-msg-example", "z-ctc-admin"}


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


def main():
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
           '    <version>1.0.0</version>',
           '    <packaging>pom</packaging>',
           '    <name>z-boot-fleet (L3 Sibling Version Authority)</name>',
           '    <description>',
           '        z-opc-foundation 兄弟仓 (z-config / z-cache / z-mq / z-gw / z-kb / z-vector / z-graph /',
           '        z-rpc / z-oss / z-schedule / z-msg / z-script / z-ctc / z-util / L3 Agent-AI 7 仓) 的版本权威。',
           '        与 z-boot-dependencies (第三方地板) 分家:抬任何一格兄弟仓版本只需要重发本 pom 一个文件夹,',
           '        不牵动第三方地板,也不牵动 19 个 z-boot-*-starter。本文件由 _doc/003_script/gen_fleet_bom.py',
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
        print(f"written: {target}")
    else:
        print(f"(dry-run;--write 才落盘,目标 {target})")


if __name__ == "__main__":
    main()
