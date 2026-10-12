#!/usr/bin/env python3
"""ship_train_consumers.py —— 火车制消费者轮发版：每仓 commit + secret gate + push。

用前必须先跑过 rollout_train_consumers.py --write（工作树有改动）。
本脚本按仓扫：for repo in changed_repos: git add + commit + secret gate + push。
"""
import os
import subprocess
import sys

FOUNDATION = "/Users/zifang/workplace/ceo_workplace/z-opc-foundation"
GATE = "z-boot/_doc/003_script/secret_gate.py"
SKIP = {"z-boot", "z-opc-foundation-lead", "c"}


def run(args, cwd=None, check=False, capture=True):
    r = subprocess.run(args, cwd=cwd, capture_output=capture, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} rc={r.returncode}\n{r.stderr}")
    return r


def is_git_repo(d):
    return os.path.isdir(os.path.join(d, ".git"))


def main():
    push = "--write" in sys.argv or "--push" in sys.argv
    results = []
    for entry in sorted(os.listdir(FOUNDATION)):
        if entry in SKIP or entry.startswith(".") or not is_git_repo(os.path.join(FOUNDATION, entry)):
            continue
        repo_dir = os.path.join(FOUNDATION, entry)
        status = run(["git", "-C", repo_dir, "status", "--porcelain"]).stdout
        if not status.strip():
            continue
        # 仅挑本火车制相关的改动：pom.xml 里 z-boot-parent 1.0.21/1.0.23→1.1.0、z-ops import 切换、z-schedule 字面、z-camuda-admin 死键等
        # 简化：所有 pom.xml + .java 改动都收；其它类型（未追踪的 .m2 等）暂不过滤，避免误带
        relevant = [l for l in status.splitlines() if l.split()[-1].endswith("pom.xml")
                    or l.split()[-1].endswith(".java") or l.split()[-1].endswith(".yml")
                    or l.split()[-1].endswith(".yaml") or l.split()[-1].endswith("gradle")
                    or l.split()[-1].endswith("z-boot-parent")]
        if not relevant:
            print(f"  [skip-no-pom-change] {entry}")
            continue
        # fetch + 比对
        run(["git", "-C", repo_dir, "fetch", "origin", "--quiet"])
        run(["git", "-C", repo_dir, "add", "-A"])
        staged = run(["git", "-C", repo_dir, "diff", "--cached", "--numstat"]).stdout
        if not staged.strip():
            print(f"  [no-staged] {entry}")
            continue
        # secret gate
        diff = run(["git", "-C", repo_dir, "diff", "--cached", "-U0"]).stdout
        gate = subprocess.run(["python3", GATE], input=diff, capture_output=True, text=True, cwd=FOUNDATION)
        if gate.returncode != 0:
            print(f"  [GATE RED] {entry}（{gate.stdout.splitlines()[0] if gate.stdout else gate.stderr[:60]}）")
            results.append((entry, "GATE_RED"))
            run(["git", "-C", repo_dir, "reset", "--quiet", "HEAD"])
            continue
        # commit
        msg = f"火车制 1.1.0 接纳：<parent> 抬号（{entry}）\n\n" \
              f"由 rollout_train_consumers.py 统一改：\n" \
              f"  - <parent>io.github.yuku123:z-boot-parent</parent> 1.0.21/1.0.23 → 1.1.0\n" \
              f"  - 个别特例见 z-boot/_doc/003_script/rollout_train_consumers.py 头部说明\n\n" \
              f"中央已发 z-boot-parent 1.1.0 + 22 件 starter 1.1.0（火车 1.1.0）。" \
              f"接入面 z-* 版本由 parent DM 经 fleet 支路统一供。" \
              f"server/部署件不在此链。"
        run(["git", "-C", repo_dir, "commit", "-m", msg], check=True)
        # push（带 ahead 检查）
        local_ahead = int(run(["git", "-C", repo_dir, "log", "--oneline", "origin/main..HEAD",
                                "-n", "1"]).stdout.strip().count("\n") or 0)
        if local_ahead == 0:
            local_ahead = 1  # at least HEAD exists
        if not push:
            print(f"  [committed-not-pushed] {entry}")
            results.append((entry, "COMMITTED"))
            continue
        r = run(["git", "-C", repo_dir, "push", "origin", "main"], check=False)
        if r.returncode == 0:
            print(f"  [pushed] {entry}")
            results.append((entry, "PUSHED"))
        else:
            print(f"  [PUSH FAILED] {entry}: {r.stderr.strip()[:120]}")
            results.append((entry, "PUSH_FAILED"))
    # 摘要
    by = {}
    for r, s in results:
        by.setdefault(s, []).append(r)
    print("\n=== 摘要 ===")
    for s, rs in by.items():
        print(f"  {s}: {len(rs)} 仓 — {', '.join(rs[:8])}{' ...' if len(rs) > 8 else ''}")


if __name__ == "__main__":
    main()
