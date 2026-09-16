#!/usr/bin/env python3
"""
batch_fix_zboot_meta.py — 批量给 z-boot 所有 starter 加 4 元数据 + 占位类
"""
import re
from pathlib import Path

ZBOOT_ROOT = Path("/Users/zifang/workplace/ceo_workplace/z-opc-foundation/z-boot")

META_BLOCK = """    <licenses>
        <license>
            <name>MIT License</name>
            <url>https://opensource.org/licenses/MIT</url>
            <distribution>repo</distribution>
        </license>
    </licenses>
    <developers>
        <developer>
            <id>yuku123</id>
            <name>yuku123</name>
            <email>1340947819@qq.com</email>
            <organization>z-opc-foundation</organization>
            <organizationUrl>https://github.com/yuku123</organizationUrl>
            <timezone>+08:00</timezone>
            <roles>
                <role>owner</role>
            </roles>
        </developer>
    </developers>
    <scm>
        <connection>scm:git:https://github.com/yuku123/z-boot.git</connection>
        <developerConnection>scm:git:ssh://git@github.com/yuku123/z-boot.git</developerConnection>
        <url>https://github.com/yuku123/z-boot</url>
        <tag>HEAD</tag>
    </scm>"""

EMPTY_STARTERS = {
    "z-boot-starter/z-boot-base":
        ("com.zifang.boot.base", "z-boot :: base (通用基础配置: Profile + Banner + 异常处理)"),
    "z-boot-starter/z-boot-web-starter":
        ("com.zifang.boot.web.starter", "z-boot :: web-starter (Spring Web + log4j2 + knife4j auto-config)"),
    "z-boot-starter/z-boot-datasource-starter":
        ("com.zifang.boot.datasource.starter", "z-boot :: datasource-starter (Druid + MyBatis-Plus + dynamic-datasource)"),
    "z-boot-integration-starters/z-boot-schedule-starter":
        ("com.zifang.boot.schedule.starter", "z-boot :: schedule-starter (集成 z-schedule 分布式任务调度)"),
}

PACKAGE_INFO_TEMPLATE = """/**
 * {title}
 *
 * 占位 package-info.java, 让 maven-javadoc-plugin 能生成 javadoc.jar
 * (Maven Central 校验要求每个 jar artifact 附带 javadoc.jar)。
 */
package {pkg};
"""

def inject_meta(pom_path: Path):
    c = pom_path.read_text(encoding="utf-8")
    has_lic = "<licenses>" in c
    has_dev = "<developers>" in c
    has_scm = "<scm>" in c
    if has_lic and has_dev and has_scm:
        return False, "skip (all 4 meta present)"
    m = re.search(r"</description>", c) or re.search(r"</url>", c)
    if not m:
        return False, "skip (no anchor)"
    insert = "\n" + META_BLOCK
    new = c[:m.end()] + insert + c[m.end():]
    pom_path.write_text(new, encoding="utf-8")
    added = []
    if not has_lic: added.append("licenses")
    if not has_dev: added.append("developers")
    if not has_scm: added.append("scm")
    return True, f"added {', '.join(added)}"

def add_package_info(rel_path: str):
    pkg, title = EMPTY_STARTERS[rel_path]
    pkg_dir = pkg.replace(".", "/")
    src_dir = ZBOOT_ROOT / rel_path / "src/main/java" / pkg_dir
    src_dir.mkdir(parents=True, exist_ok=True)
    pkg_info = src_dir / "package-info.java"
    if pkg_info.exists():
        return f"exists: {pkg_info}"
    pkg_info.write_text(PACKAGE_INFO_TEMPLATE.format(pkg=pkg, title=title), encoding="utf-8")
    return f"created: {pkg_info}"

def main():
    print("=" * 70)
    print("Step 1: 给所有 starter pom.xml 注入 4 元数据")
    print("=" * 70)
    targets = []
    for p in ZBOOT_ROOT.rglob("pom.xml"):
        if "target" in p.parts or ".flattened" in p.name:
            continue
        if p.parent.name in ("z-boot-starter", "z-boot-integration-starters", "z-boot"):
            continue
        name = p.parent.name
        if name == "z-boot-base" or (name.startswith("z-boot-") and "starter" in name):
            targets.append(p)
    for p in sorted(targets):
        ok, msg = inject_meta(p)
        print(f"  {'✅' if ok else '⏭️ '} {p.parent.name:<32} {msg}")

    print()
    print("=" * 70)
    print("Step 2: 给 0 源码 starter 加 package-info.java")
    print("=" * 70)
    for rel in sorted(EMPTY_STARTERS.keys()):
        print(f"  {add_package_info(rel)}")
    print("\nDone.")

if __name__ == "__main__":
    main()
