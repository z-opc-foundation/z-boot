#!/usr/bin/env bash
# mvn_gate.sh —— 把"同一时刻只有一遍带测试的 mvn"变成机器保证，不是靠人记住。
#
# 为什么要它：这台机器上多个会话/代理会并行跑构建，而组织里有**写死端口**的测试
# （z-vector 的 6334、平台常驻进程占的 6379/8888/9085/9090/12888/18180/20880 等）。
# 两边同时在跑就会互相踩掉，并且**两边报一模一样的错** —— 2026-09-29 那一轮就把它
# 误读成"这仓本来就红"，白查了一次。见 z-boot README「消费模型」判据第 3 条。
#
# 用法：把原来的 mvn 命令前面换成/加上本脚本，参数原样透传：
#   z-boot/_doc/003_script/mvn_gate.sh -B -s z-boot/_doc/003_script/repo1-settings.xml \
#       -Dmaven.repo.local=/tmp/m2-<仓>-clean clean package -f <仓>/pom.xml
# 纯 dependency:tree、-DskipTests 的构建也走它（无副作用，只是排队更规整）。
#
# 只建目录锁，不 kill 任何进程；超时/被拒时**不改别人的锁**。
set -u

LOCK_ROOT="${ZOPC_MVN_LOCK:-/tmp/z-opc-mvn.lock}"
MAX_WAIT="${ZOPC_MVN_LOCK_WAIT:-2400}"   # 秒；等不到就非 0 退出，让人重来
SLEEP=5

waited=0
acquired=0
while [ "$waited" -lt "$MAX_WAIT" ]; do
    if mkdir "$LOCK_ROOT" 2>/dev/null; then
        acquired=1
        break
    fi
    # 持有者已经不在了（被 SIGKILL、没走到 trap）⇒ 清掉残留锁，否则这道闸会永久卡死
    holder=$(sed -n 's/^pid=//p' "$LOCK_ROOT/owner.txt" 2>/dev/null | head -1)
    if [ -n "${holder:-}" ] && ! kill -0 "$holder" 2>/dev/null; then
        echo "[mvn_gate] 发现残留锁（pid=$holder 已退出），清理后重试" >&2
        rm -rf "$LOCK_ROOT"
        continue
    fi
    if [ "$waited" -eq 0 ]; then
        echo "[mvn_gate] 有别的构建在跑，排队（锁 $LOCK_ROOT；持有者见 owner.txt）" >&2
    fi
    sleep "$SLEEP"
    waited=$((waited + SLEEP))
done

if [ "$acquired" -ne 1 ]; then
    echo "[mvn_gate] 等锁 ${MAX_WAIT}s 超时，拒绝启动（别人的构建还占着，不抢锁）" >&2
    [ -f "$LOCK_ROOT/owner.txt" ] && sed 's/^/[mvn_gate]   持有者: /' "$LOCK_ROOT/owner.txt" >&2
    exit 75
fi

printf 'pid=%s\nuser=%s\npwd=%s\ncmd=mvn %s\nstart=%s\n' \
    "$$" "$(id -un)" "$PWD" "$*" "$(date '+%F %T')" > "$LOCK_ROOT/owner.txt"
trap 'rm -rf "$LOCK_ROOT"' EXIT INT TERM
[ "$waited" -gt 0 ] && echo "[mvn_gate] 排队 ${waited}s 后取得锁" >&2

# 不能 exec：exec 会替换掉本进程，trap 就没了，锁永远还不回来。
mvn "$@"
rc=$?
if [ "$rc" -eq 0 ]; then
    echo "[mvn_gate] 构建结束 rc=0，锁已释放" >&2
else
    echo "[mvn_gate] 构建结束 rc=$rc（锁照样释放，红不红自己看上面）" >&2
fi
exit "$rc"
