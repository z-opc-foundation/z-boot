#!/usr/bin/env python3
"""
secret_gate.py — 推之前扫本次要推的 diff，只报**计数**，绝不打印命中行。

用法（把要推的那一次提交喂进来，别喂整条历史）：
    git -C <repo> show HEAD --format='' -U0 | python3 z-boot/_doc/003_script/secret_gate.py
    git -C <repo> diff --cached -U0            | python3 z-boot/_doc/003_script/secret_gate.py
退出码：0=无命中，1=有命中（⇒ 人工看过命中行之前不推）。

为什么长这样（都是付过学费的）：
  · **先自证作用域**。"零命中"和"零输入"输出长得一模一样，2026-09-28 就因为把仓路径写错
    一层，让一个根本不存在的目录"通过"了全部检查。所以第一行永远印吃进了多少行。
  · **只印计数**。任何把命中行（哪怕截断版）打进会话记录的做法都泄露过一次真实 token：
    当时 `-` 行开头、前 40 个字符正好盖住 token 的 39 位。要证据就印 文件+行号+sha256[:8]+长度。
  · **只看新增行**。`+` 行才是新增暴露；`-` 行是删除动作，值本来就在远端历史里（那种情况
    该轮换凭证，不是改写历史）。
  · 高熵特征必须**同时含字母与数字**：早期版本用 `[A-Za-z0-9+/]{28,}`，被中文注释里
    `compiler/surefire/jar/resources/` 这种斜杠连接的插件名清单稳定误判（2026-09-29 z-task）。
"""
import re
import sys

PATTERNS = {
    "凭证字样": r"(?i)(password|passwd|secret|token|api[_-]?key|private[_-]?key|credential)",
    "私钥块": r"BEGIN [A-Z ]*PRIVATE KEY",
    "GitHub PAT": r"(ghp_|gho_|github_pat_|xox[baprs]-)[A-Za-z0-9]{8,}",
    "npm/AKJS 形状": r"(npm_[A-Za-z0-9]{8,}|AKIA[0-9A-Z]{16}|LTAI[A-Za-z0-9]{8,})",
    "JWT": r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{6,}",
    "高熵串": r"(?=[A-Za-z0-9]{20,}(?![A-Za-z0-9]))(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*[0-9])[A-Za-z0-9]{20,}={0,2}",
    "键值赋值": r"(?i)^\s*[A-Z][A-Z0-9_]{3,}\s*=\s*[A-Za-z0-9+/_-]{12,}",
}

SENSITIVE_NAMES = re.compile(r"(^|/)(\.env|[^/]*\.(p12|p8|pem|mobileprovision|keystore|jks))$|/secrets?/|AuthKey_|keys\.md", re.I)


def main():
    lines = sys.stdin.read().splitlines()
    if not lines:
        print("✗ stdin 为空 —— 这是『没读到东西』，不是『没有密钥』。检查上一条 git 命令是否真的失败")
        return 1

    added = [l[1:] for l in lines if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:] for l in lines if l.startswith("-") and not l.startswith("---")]
    new_files = [l[6:] for l in lines if l.startswith("diff --git") or l.startswith("+++ b/")]
    print(f"输入自证：diff 行={len(lines)} 新增行={len(added)} 删除行={len(removed)}（新增行为 0 ⇒ 下面的零命中不代表安全）")

    hits = 0
    for name, pat in PATTERNS.items():
        n = sum(1 for l in added if re.search(pat, l))
        hits += n
        if n:
            # 只定位，不印内容：文件名 + 第几条 + 命中串的 sha256 前 8 位与长度
            import hashlib
            for i, l in enumerate(filter(lambda x: re.search(pat, x), added), 1):
                m = re.search(pat, l).group(0)
                print(f"  {name}: #{i} sha256={hashlib.sha256(m.encode()).hexdigest()[:8]} len={len(m)}")
        else:
            print(f"  {name}: 0")

    named = [f for f in new_files if SENSITIVE_NAMES.search(f)]
    if named:
        hits += len(named)
        print(f"  ⚠ 敏感文件名 {len(named)} 个（只印文件名，这些本来就不该进提交）：{named}")
    print("判定：" + ("✗ 有命中 ⇒ 人工确认命中行内容之前不要 push" if hits else "✓ 0 命中"))
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
