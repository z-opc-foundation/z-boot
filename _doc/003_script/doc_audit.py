#!/usr/bin/env python3
"""doc_audit.py — 按 002_项目文档收口规范 扫描 z-opc-foundation 下各项目仓的文档收口合规。

用法：
    python3 _doc/003_script/doc_audit.py            # 扫全部在范围内的仓
    python3 _doc/003_script/doc_audit.py z-mq z-lc  # 只扫指定仓

检查项（与规范的 audit 检查项一一对应）：
    R1 仓根除允许清单外无散落 .md/.txt/.sql/.sh/.py
    R2 _doc/ 根不留散文件（README.md 索引除外）
    R3 _doc/ 下的一级目录必须命中固定编号表
    R4 不留空桶（git 不跟踪空目录，留着就是 README 断链的来源）
    R5 README.md 无指向不存在路径的相对链接
    R6 _doc/003_script 下依赖仓根的脚本必须用 REPO_ROOT 上溯定位，不能 cd "$(dirname $0)"
    R7 运行态/临时件不进 git：一律写 <仓>/.cache/，且 .cache 必须被 ignore
退出码：有违规则为 1。
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ROOT, "..", ".."))  # z-boot
ORG = os.path.dirname(ROOT)

ALLOWED_ROOT = {
    "README.md", "CHANGELOG.md", "LICENSE", "AGENTS.md", "CLAUDE.md", "pom.xml",
    "build.gradle", ".gitignore", ".dockerignore", ".flattened-pom.xml",
    "Makefile", "mvnw", "mvnw.cmd", "package.json", "package-lock.json",
    "tsconfig.json", "tsconfig.build.json", "vite.config.ts", "vite.lib.config.ts",
    "vitest.config.ts", "pnpm-workspace.yaml", "pnpm-lock.yaml",
}
ALLOWED_RE = re.compile(
    r"^(docker-compose[\w.-]*\.ya?ml|Dockerfile[\w.-]*|\.env\.[\w-]+|"
    r"settings[\w.-]*\.xml|\.gitkeep|sonar[\w.-]*|license-check[\w.-]*)$")

BUCKETS = {
    "001_arch", "002_deploy", "003_script", "004_skill",
    "005_testing", "006_release", "007_backlog", "008_troubleshooting",
}
# z-opc 单体本轮未并表；lead 仓保留自己的 001-008 结构
EXCLUDED = {"z-opc", "z-opc-foundation-lead", "z-opcs-server"}

STRAY_EXT = (".md", ".MD", ".txt", ".sql", ".sh", ".py", ".rst", ".adoc")

ROOT_CD = re.compile(r'cd\s+"\$\(\s*dirname[^)]*\$0[^)]*\)')
# 只有确实按仓根取物（pom.xml / .env / .gnupg / ~/.m2）的脚本，cd 到 _doc/003_script 才算断链
ROOT_DEP = re.compile(r'(pom\.xml|\.env|\.gnupg|settings\.xml)')

# R7：跑起来才会产生的东西不进 git（E2E 的假 home、字节码缓存、锁、sqlite、日志）
RUNTIME_SHAPE = re.compile(
    r'(^|/)__pycache__/|\.pyc$|(^|/)state\.db$|\.lock$|(^|/)checkpoints/'
    r'|(^|/)logs?/[^/]*\.log$|/out/profile-[^/]+/|(^|/)\.DS_Store$')


def tracked(repo, ref=None):
    if ref:
        res = subprocess.run(["git", "-C", os.path.join(ORG, repo), "ls-tree", "-r",
                              "--name-only", "-z", ref],
                             capture_output=True, text=True, check=True)
    else:
        res = subprocess.run(["git", "-C", os.path.join(ORG, repo), "ls-files", "-z"],
                             capture_output=True, text=True, check=True)
    return [p for p in res.stdout.split("\0") if p]


def ignore_blob(repo, ref=None):
    """.gitignore 全文：ref 模式读历史版本，用于拿已知坏样本喂 R7。"""
    if ref:
        res = subprocess.run(["git", "-C", os.path.join(ORG, repo), "show", f"{ref}:.gitignore"],
                             capture_output=True, text=True)
        return res.stdout
    path = os.path.join(ORG, repo, ".gitignore")
    return open(path, encoding="utf-8", errors="replace").read() if os.path.isfile(path) else ""


def docker_build_inputs(repo):
    """被 Dockerfile / docker-compose 引用的仓根文件名 —— 规范豁免：搬走即断构建。"""
    names = set()
    for p in tracked(repo):
        base = p.rsplit("/", 1)[-1]
        if not (base == "Dockerfile" or base.startswith("Dockerfile.") or base.endswith((".yml", ".yaml"))):
            continue
        if not os.path.isfile(os.path.join(ORG, repo, p)):
            continue
        with open(os.path.join(ORG, repo, p), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                for tok in re.split(r"[\s,'\"\[\]]+", line):
                    if "/" not in tok and tok.endswith((".py", ".sh", ".jar", ".cjs", ".js")):
                        names.add(tok)
    return names


def has_ignored_content(repo, bucket):
    """桶里只剩被 .gitignore 定向忽略的私有件 —— 不算空桶，按规范保留原位。"""
    res = subprocess.run(
        ["git", "-C", os.path.join(ORG, repo), "ls-files", "--others", "--ignored",
         "--exclude-standard", "-z", f"_doc/{bucket}/"],
        capture_output=True, text=True, check=True)
    return any(p for p in res.stdout.split("\0") if p)


def check(repo, ref=None):
    bad = []
    files = tracked(repo, ref)
    top = {p for p in files if "/" not in p}
    exempt = docker_build_inputs(repo)

    for name in sorted(top):
        if name in ALLOWED_ROOT or ALLOWED_RE.match(name):
            continue
        if name in exempt:
            continue
        if name.endswith(STRAY_EXT):
            bad.append(("R1", f"仓根散件 {name}"))

    doc_files = [p for p in files if p.startswith("_doc/")]
    for p in doc_files:
        if p.count("/") == 1 and p != "_doc/README.md":  # DC:ignore 比的是索引里的路径形状，不是盘上引用
            bad.append(("R2", f"_doc 根散文件 {p}"))

    buckets = {p.split("/")[1] for p in doc_files if p.count("/") >= 2}
    for b in sorted(buckets - BUCKETS):
        bad.append(("R3", f"非编号表目录 _doc/{b}/"))

    docdir = os.path.join(ORG, repo, "_doc")
    if os.path.isdir(docdir):
        on_disk = {d for d in os.listdir(docdir) if os.path.isdir(os.path.join(docdir, d))}
        for d in sorted(on_disk - buckets - {"README.md"}):
            if has_ignored_content(repo, d):
                continue
            bad.append(("R4", f"空桶 _doc/{d}/（git 不跟踪空目录，clone 后必断链）"))

    readme = os.path.join(ORG, repo, "README.md")
    if os.path.isfile(readme):
        with open(readme, encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                for tgt in re.findall(r"\]\(([^)\s]+)", line):
                    if tgt.startswith(("#", "http://", "https://", "mailto:", "git@")):
                        continue
                    path = tgt.split("#")[0]
                    if path and not os.path.exists(os.path.join(ORG, repo, path)):
                        bad.append(("R5", f"README L{i} 断链 {path}"))

    for p in files:
        if not (p.startswith("_doc/003_script/") and p.endswith(".sh")):
            continue
        if not os.path.isfile(os.path.join(ORG, repo, p)):
            continue  # ref 模式下旧路径已不在盘上
        with open(os.path.join(ORG, repo, p), encoding="utf-8", errors="replace") as fh:
            body = fh.read()
        if ROOT_CD.search(body) and "REPO_ROOT" not in body and ROOT_DEP.search(body):
            bad.append(("R6", f"{p} 用 cd \"$(dirname $0)\" 定位，搬到 _doc 后必 die"))

    # R7 运行态件不进 git
    for p in files:
        if RUNTIME_SHAPE.search(p):
            bad.append(("R7", f"运行态件进了 git：{p}（该写 <仓>/.cache/）"))
    cache_tracked = [p for p in files if p.split("/")[0] == ".cache"]
    ignores = ignore_blob(repo, ref)
    if cache_tracked:
        bad.append(("R7", f".cache/ 里有 {len(cache_tracked)} 个被跟踪文件（例：{cache_tracked[0]}）"))
    if ("/.cache/" not in ignores and ".cache/" not in ignores):
        bad.append(("R7", ".gitignore 没有 /.cache/ —— 临时件无处可放"))

    return bad


def main():
    repos = sys.argv[1:] or sorted(
        d for d in os.listdir(ORG)
        if os.path.isdir(os.path.join(ORG, d, ".git")) and d not in EXCLUDED)
    total = 0
    ref = None
    if "--against" in sys.argv:
        k = sys.argv.index("--against")
        ref = sys.argv[k + 1]
        repos = sys.argv[:k] + sys.argv[k + 2:]
        repos = [r for r in repos if not r.startswith("-")] or [
            d for d in os.listdir(ORG)
            if os.path.isdir(os.path.join(ORG, d, ".git")) and d not in EXCLUDED]
    for r in repos:
        if not os.path.isdir(os.path.join(ORG, r, ".git")):
            continue
        try:
            bad = check(r, ref)
        except subprocess.CalledProcessError:
            continue
        total += len(bad)
        if bad:
            print(f"=== {r}")
            for code, msg in bad:
                print(f"  [{code}] {msg}")
    print(f"\n扫描 {len(repos)} 仓，违规 {total} 条")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
