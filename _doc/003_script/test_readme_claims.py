#!/usr/bin/env python3
"""z-boot README 定量主张自守卫 —— 口径 §5「能力可追溯」在本仓的落地形态。

为什么要有这一层：本仓 README 把「当前发行 / 根版本 / parent 版本 / 地板 155 /
接入面 79 / 自家 22 格 / 火车 22 个全 1.1.2 / 19 个聚合 starter / Spring Boot
2.7.18 / FAMILIES 25 族」写成了硬数字。每次抬号、每加一个 starter、每调一次
gen_train_bom.py 的 FAMILIES 都会让这些数字漂一次。没有任何尺子去问盘面
「现在还是吗」，那这些数字的保质期就是上一次编辑的时刻。

口径：
- 缺一条主张 = 红（不许「正则没匹配上就跳过」，那正是空跑）；
- 数值不等 = 红，且报错必须把**重算值**打进去（红了要知道真数是多少）；
- **README 侧的数字一律在核对当下现解析**（本文件不缓存 README 侧数值），
  事实对象里只装盘面事实 —— 否则尺子退化成恒等式比较，改了 README 也不红。

⚠ 本仓是纯 POM 仓（无 Java 源码、无测试框架），故本文件用 Python unittest，
**零新增依赖**，只读 pom/XML/文本，不联网。运行：
    python3 _doc/003_script/test_readme_claims.py
"""
import ast
import os
import re
import unittest
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))            # z-boot/_doc/003_script
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))   # z-boot
WORKSPACE = os.path.abspath(os.path.join(REPO_ROOT, ".."))     # 工作区根
README = os.path.join(REPO_ROOT, "README.md")
ROOT_POM = os.path.join(REPO_ROOT, "pom.xml")
PARENT_POM = os.path.join(REPO_ROOT, "z-boot-parent", "pom.xml")
GEN_SCRIPT = os.path.join(HERE, "gen_train_bom.py")
AGG_DIRS = ["z-boot-starter", "z-boot-integration-starters"]

NS = {"m": "http://maven.apache.org/POM/4.0.0"}
YUKU = "io.github.yuku123"


def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def strip_comments(text):
    """剥 XML 注释 —— 根 pom 的历史说明全在注释里，不剥会读到幻影坐标。"""
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def parse_pom(path):
    return ET.fromstring(strip_comments(read_text(path)))


def text_of(node, path):
    found = node.find(path, NS)
    if found is None or found.text is None:
        return None
    return found.text.strip()


def flatten(text):
    """换行劈行安全：连续空白压成一个空格。"""
    return re.sub(r"\s+", " ", text)


def starter_dirs():
    """两个聚合器下的叶子 starter 目录（按相对仓根路径定位，不按目录名统计）。"""
    out = []
    for agg in AGG_DIRS:
        base = os.path.join(REPO_ROOT, agg)
        for name in sorted(os.listdir(base)):
            d = os.path.join(base, name)
            if os.path.isdir(d) and os.path.exists(os.path.join(d, "pom.xml")):
                out.append((agg, name, os.path.join(d, "pom.xml")))
    return out


def facts():
    """事实对象：只装盘面事实，README 一个字都不参与。"""
    root = parse_pom(ROOT_POM)
    parent = parse_pom(PARENT_POM)

    dm = parent.find("m:dependencyManagement/m:dependencies", NS)
    entries = list(dm) if dm is not None else []
    floor, client, own = [], [], []
    for e in entries:
        g = text_of(e, "m:groupId")
        a = text_of(e, "m:artifactId")
        v = text_of(e, "m:version")
        if g != YUKU:
            floor.append((a, v))
        elif a.startswith("z-boot-"):
            own.append((a, v))
        else:
            client.append((a, v))

    starters = []
    for agg, name, pom in starter_dirs():
        node = parse_pom(pom)
        raw = strip_comments(read_text(pom))
        m = re.search(
            r"<artifactId>z-boot-parent</artifactId>\s*<version>([^<]+)</version>", raw)
        starters.append({
            "agg": agg, "name": name,
            "version": text_of(node, "m:version"),
            "parent_import": m.group(1).strip() if m else None,
        })

    props = {}
    pnode = parent.find("m:properties", NS)
    if pnode is not None:
        for p in pnode:
            props[p.tag.split("}")[-1]] = (p.text or "").strip()

    # FAMILIES 族数：用 AST 取字面量，不执行脚本（脚本 import 即无副作用，但更稳）
    families = {}
    tree = ast.parse(read_text(GEN_SCRIPT))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) == "FAMILIES" for t in node.targets):
            families = ast.literal_eval(node.value)

    return {
        "root_version": text_of(root, "m:version"),
        "root_group": text_of(root, "m:groupId"),
        "root_packaging": text_of(root, "m:packaging"),
        "root_compiler": text_of(root, "m:properties/m:maven.compiler.source"),
        "parent_version": text_of(parent, "m:version"),
        "parent_parent_artifact": text_of(parent, "m:parent/m:artifactId"),
        "parent_parent_version": text_of(parent, "m:parent/m:version"),
        "dm_total": len(entries),
        "dm_floor": len(floor),
        "dm_client": len(client),
        "dm_own": len(own),
        "dm_own_all_property": all("${z-boot.version}" in v for _, v in own),
        "dm_z_util_core": (lambda v: (re.search(r"\$\{([^}]+)\}", v).group(1)
                                      if v and "${" in v else v))(
            next((v for a, v in client if a == "z-util-core"), None)),
        "props": props,
        "starters": starters,
        "starter_count": len(starters),
        "starter_versions": sorted({s["version"] for s in starters}),
        "starter_imports": sorted({s["parent_import"] for s in starters}),
        "integration_count": len([s for s in starters if s["agg"] == "z-boot-integration-starters"]),
        "agg_versions": sorted({
            text_of(parse_pom(os.path.join(REPO_ROOT, agg, "pom.xml")), "m:version")
            for agg in AGG_DIRS}),
        "families": len(families),
    }


def verify_claims(readme, f):
    """README 侧数字现解析 → 与盘面重算值逐条对账；不一致就抛（带重算值）。"""
    flat = flatten(readme)
    problems = []

    def claim(pattern, what, source=None):
        m = re.search(pattern, source if source is not None else flat)
        if not m:
            problems.append(f"README 里找不到「{what}」这条主张 —— 要么写法变了（尺子要跟着改），"
                            f"要么它被删了（那就不该再声称这个数）")
            return None
        # 多组正则返回全部捕获组，单组返回字符串
        return m.groups() if len(m.groups()) > 1 else m.group(1)

    def check(what, readme_val, fact_val):
        if readme_val is None:
            return
        if str(readme_val) != str(fact_val):
            problems.append(f"{what}：README 写 {readme_val!r}，盘面重算 {fact_val!r}")

    # 1. 根 z-boot 的坐标与版本
    check("根 z-boot 版本", claim(r"根 `z-boot:([0-9]+\.[0-9]+\.[0-9]+)`", "根 `z-boot:X.Y.Z`"),
          f["root_version"])
    check("根 z-boot groupId", claim(r"\| \*\*groupId\*\* \| `([^`]+)`", "groupId"), f["root_group"])

    # 2. 消费入口 z-boot-parent 的版本 + 它的 parent（根）
    check("z-boot-parent 版本", claim(r"消费入口 `z-boot-parent:([0-9]+\.[0-9]+\.[0-9]+)`",
                                       "消费入口 `z-boot-parent:X.Y.Z`"), f["parent_version"])
    check("z-boot-parent 的 parent", claim(r"`z-boot-parent` 的 `<parent>` = 根 `z-boot:([0-9]+\.[0-9]+\.[0-9]+)`",
                                           "z-boot-parent 的 parent 是根 z-boot"), f["parent_parent_version"])
    check("z-boot-parent 的 parent 坐标", claim(r"根 `(z-boot):[0-9]", "根 z-boot 坐标"),
          f["parent_parent_artifact"])

    # 3. parent 的 DM 三段分解：地板 / 接入面 / 自家（三个数都在同一句里）
    dm = claim(r"内含地板 (\d+) \+ 接入面 pin (\d+) \+ 自家 starter (\d+) 格", "DM 三段分解")
    if dm:
        check("地板条数", dm[0], f["dm_floor"])
        check("接入面 pin 条数", dm[1], f["dm_client"])
        check("自家 starter 格数", dm[2], f["dm_own"])
    check("接入面条数（火车制表）", claim(r"接入面 (\d+) 条 client 坐标 pin 进 parent DM",
                                          "接入面 N 条 client 坐标 pin 进 parent DM"), f["dm_client"])

    # 4. 自家 22 格：另一处说法（版本键 ${z-boot.version}）
    own_rows = claim(r"里的 (\d+) 条 `z-boot-\*` 自家 starter/base", "自家 starter/base 条数")
    check("自家 starter/base 条数", own_rows, f["dm_own"])
    check("自家版本键", claim(r"版本键 `\$\{z-boot\.version\}` = `([0-9]+\.[0-9]+\.[0-9]+)`",
                              "版本键 ${z-boot.version}"), f["parent_version"])
    if not f["dm_own_all_property"]:
        problems.append("自家 starter/base 的版本键不是统一的 ${z-boot.version}（盘面不符）")

    # 5. 火车：22 个 starter/聚合器全 1.1.2
    train = claim(r"火车 = (\d+) 个 starter/聚合器全 `([0-9]+\.[0-9]+\.[0-9]+)`", "火车 starter 数与版本")
    if train:
        check("火车 starter 数", train[0], f["starter_count"])
        check("火车版本", train[1], f["starter_versions"][0] if len(f["starter_versions"]) == 1 else f["starter_versions"])
    if len(f["starter_versions"]) != 1:
        problems.append(f"starter 版本不齐：{f['starter_versions']}")
    if len(f["agg_versions"]) != 1:
        problems.append(f"两个聚合器版本不齐：{f['agg_versions']}")
    if f["agg_versions"] and f["starter_versions"] and f["agg_versions"][0] != f["starter_versions"][0]:
        problems.append("聚合器版本与叶子 starter 版本不同号（火车制要求同号）")

    # 6. 19 个 L3 聚合 starter
    check("L3 聚合 starter 数", claim(r"### z-boot-\* 聚合 starter（(\d+) 个", "聚合 starter（19 个）"),
          f["integration_count"])

    # 7. starter 的 DM = 单条 import z-boot-parent:X.Y.Z
    imp = claim(r"starter 的 DM = 单条 `import z-boot-parent:([0-9]+\.[0-9]+\.[0-9]+)`",
                "starter 的 DM import 版本")
    check("starter import 版本", imp, f["starter_imports"][0] if len(f["starter_imports"]) == 1
          else f["starter_imports"])
    if len(f["starter_imports"]) != 1:
        problems.append(f"starter 的 parent import 版本不齐：{f['starter_imports']}")

    # 8. 运行口径：Java 8 + Spring Boot 2.7.18
    check("Java 口径", claim(r"\*\*运行口径\*\* \| Java (\d+)", "运行口径 Java N"), f["root_compiler"])
    check("Spring Boot 版本", claim(r"Spring Boot \*\*([0-9]+\.[0-9]+\.[0-9]+)\*\*", "Spring Boot X.Y.Z"),
          f["props"].get("spring-boot.version"))

    # 9. FAMILIES 族数
    check("FAMILIES 族数", claim(r"\*\*FAMILIES 表\*\*（(\d+) 族）", "FAMILIES 表（N 族）"), f["families"])

    # 10. 接入示例里 z-util-core 的版本键（parent 下发，不写死字面号）
    check("z-util-core 版本键", claim(r"<!-- parent 下发（\$\{(z-util\.version)\}） -->",
                                      "z-util-core 的 parent 下发注释"), f["dm_z_util_core"])

    # 11. 接入示例里的当前火车号：README 里每个 z-boot-parent / z-boot-*-starter 的
    #     XML 版本号都必须等于盘面 train 号（这正是 1.0.21 那处漂移的判据）
    train_no = f["parent_version"]
    train_ids = {"z-boot-parent"} | {s["name"] for s in f["starters"]}
    pairs = re.findall(r"<artifactId>(z-boot-[a-z0-9-]*)</artifactId>\s*<version>([^<]+)</version>", flat)
    current = [(a, v) for a, v in pairs if a in train_ids]
    if not current:
        problems.append("README 里找不到任何 z-boot-parent / z-boot-*-starter 的 XML 版本号"
                        "（接入示例被删了，或写法变了）")
    for a, v in current:
        if v != train_no:
            problems.append(f"接入示例里 {a} 的版本 {v} != 当前火车号 {train_no}")
    # 退役件（dependencies / fleet）走自己的最后发布版本，README 内部要自洽
    m_ret = re.search(r"退役件 `z-boot-dependencies:([0-9.]+)` / `z-boot-fleet:([0-9.]+)`", flat)
    if m_ret:
        for art, ver in (("z-boot-dependencies", m_ret.group(1)), ("z-boot-fleet", m_ret.group(2))):
            used = [v for a, v in pairs if a == art]
            if not used:
                problems.append(f"README 的退役路径里没有 {art} 的 XML 版本号（写法变了？）")
            for v in used:
                if v != ver:
                    problems.append(f"退役件 {art}：火车制表写 {ver}，接入示例写 {v}")

    if problems:
        raise AssertionError("README 主张与盘面不一致（%d 条）：\n  - %s"
                             % (len(problems), "\n  - ".join(problems)))


class ReadmeClaimsTest(unittest.TestCase):
    def test_readme_claims_match_disk(self):
        """用例 A：真实 README 的所有主张与盘面重算值逐条对账 —— 必须全绿。"""
        verify_claims(read_text(README), facts())

    def test_healthy_readme_not_rejected(self):
        """用例 C：不许冤枉健康页 —— 真实 README 不得被判红。"""
        verify_claims(read_text(README), facts())

    def test_tooth_wrong_numbers(self):
        """用例 B：牙口 —— 把 README 的数改错，判定必须判红。"""
        real = read_text(README)
        f = facts()
        mutations = [
            ("根版本", lambda s: s.replace("根 `z-boot:1.0.19`", "根 `z-boot:9.9.9`")),
            ("parent 版本", lambda s: s.replace("消费入口 `z-boot-parent:1.1.2`",
                                                "消费入口 `z-boot-parent:0.0.1`")),
            ("地板条数", lambda s: s.replace("内含地板 155", "内含地板 150")),
            ("接入面条数", lambda s: s.replace("接入面 pin 79", "接入面 pin 70")),
            ("自家格数", lambda s: s.replace("自家 starter 22 格", "自家 starter 20 格")),
            ("火车 starter 数", lambda s: s.replace("火车 = 22 个 starter/聚合器", "火车 = 20 个 starter/聚合器")),
            ("Spring Boot 版本", lambda s: s.replace("Spring Boot **2.7.18**", "Spring Boot **2.7.17**")),
            ("FAMILIES 族数", lambda s: s.replace("**FAMILIES 表**（25 族）", "**FAMILIES 表**（24 族）")),
        ]
        for what, mutate in mutations:
            broken = mutate(real)
            self.assertNotEqual(broken, real, f"变异「{what}」没改动 README（尺子测不到自己）")
            with self.assertRaises(AssertionError, msg=f"变异「{what}」竟然没被判红"):
                verify_claims(broken, f)

    def test_tooth_deleted_claims(self):
        """用例 B'：删掉主张必须判红 —— 不许静默跳过。"""
        real = read_text(README)
        f = facts()
        deletions = [
            ("根版本", lambda s: s.replace("根 `z-boot:1.0.19`", "根 `z-boot`")),
            ("DM 分解", lambda s: s.replace("内含地板 155 + 接入面 pin 79 + 自家 starter 22 格", "内含若干")),
            ("Spring Boot 版本", lambda s: s.replace("Spring Boot **2.7.18**", "Spring Boot")),
        ]
        for what, mutate in deletions:
            broken = mutate(real)
            self.assertNotEqual(broken, real, f"删除「{what}」没改动 README（尺子测不到自己）")
            with self.assertRaises(AssertionError, msg=f"删除「{what}」竟然没被判红"):
                verify_claims(broken, f)


if __name__ == "__main__":
    unittest.main(verbosity=2)
