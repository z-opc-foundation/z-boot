#!/usr/bin/env bash
# tierA_matrix.sh —— 消费者轮（parent 抬到 1.0.21）的逐仓构建矩阵。
#
# 为什么逐仓跑而不是只看 tree：这一轮动的是"面值来源"（33 个仓根的 <parent>、z-opc 的
# z-boot-floor.version、三仓撤掉的 simpleclient 压法、z-report/z-schedule-admin 删掉的
# z-boot.version 直接条目、z-camuda-admin 抬的 fleet import）。删格子的失败方式是"属性悬空"
# 和"编译期找不到类"，只有真构建会露出来；tree 只证明解析得到。
#
# 口径：`clean package -DskipTests`，串行（每仓一次 mvn_gate 取锁），远端只认 repo1
# （-s repo1-settings.xml，绕开 mvn.seenew.info 那个会缓存 404 的滞后镜像）。
# 本地仓用默认 ~/.m2 —— z-ext/z-meta/z-task/z-lc/z-webide/z-llm 还靠本机 1.0.0-SNAPSHOT
# 的 phantom 件编得过（见记忆 internal-repos-phantom-deps），净室跑它们必红且是假红。
# 净室那一遍单独跑（tierA_cleanroom.sh / dependency:tree）。
#
# 用法：
#   LOG=/tmp/f21-matrix z-boot/_doc/003_script/tierA_matrix.sh [仓名 ...]
# 不传仓名 = 全部 33 个带 z-boot-parent:1.0.21 的仓根。
set -u

ROOT=/Users/zifang/workplace/ceo_workplace/z-opc-foundation
GATE="$ROOT/z-boot/_doc/003_script/mvn_gate.sh"
SETTINGS=z-boot/_doc/003_script/repo1-settings.xml
J8=/Users/zifang/Library/Java/JavaVirtualMachines/corretto-1.8.0_492/Contents/Home
J17=/Users/zifang/Library/Java/JavaVirtualMachines/amazon-corretto-17.jdk/Contents/Home
LOG="${LOG:-/tmp/f21-matrix}"
mkdir -p "$LOG"
SUM="$LOG/summary.txt"
: > "$SUM"

ALL="z-agent z-agent-kernel z-agent-proxy z-bot z-cache z-camuda z-config z-ctc z-ext z-graph z-gw z-indexer z-kb z-lc z-llm z-mcp z-meta z-mist z-mq z-msg z-opc z-opcs z-oss z-qa z-report z-rpc z-schedule z-script z-skill z-task z-util z-vector z-webide"
REPOS="${*:-$ALL}"

cd "$ROOT" || exit 2
for r in $REPOS; do
    # z-lc 上游已用 Java 11 API，JDK 8 编不过（记忆 feedback-java8-runtime）
    case "$r" in
        z-lc) export JAVA_HOME="$J17" ;;
        *)    export JAVA_HOME="$J8" ;;
    esac
    t0=$(date +%s)
    if "$GATE" -B -s "$SETTINGS" clean package -DskipTests -f "$r/pom.xml" > "$LOG/$r.log" 2>&1; then
        echo "PASS  $r  $(( $(date +%s) - t0 ))s" | tee -a "$SUM"
    else
        rc=$?
        echo "FAIL  $r  $(( $(date +%s) - t0 ))s  rc=$rc  末行:$(grep -m3 -E '\[ERROR\]' "$LOG/$r.log" | tr '\n' ' ' | cut -c1-160)" | tee -a "$SUM"
    fi
done
echo "== 汇总：$(grep -c '^PASS' "$SUM") PASS / $(grep -c '^FAIL' "$SUM") FAIL" | tee -a "$SUM"
