#!/bin/sh
# 薄壳：按文件夹发版时，maven.multiModuleProjectDirectory = 本文件夹，
# 真脚本在**仓根**的 _doc/003_script/ 下 ⇒ 这里逐级向上找并转发。
set -e
here="$(cd "$(dirname "$0")" && pwd)"
d="$here"
while [ "$d" != "/" ]; do
    if [ -f "$d/_doc/003_script/gpg-with-passphrase.sh" ] && [ "$d/_doc/003_script/gpg-with-passphrase.sh" != "$0" ]; then
        exec "$d/_doc/003_script/gpg-with-passphrase.sh" "$@"
    fi
    d="$(dirname "$d")"
done
echo "[gpg-thin] 向上找不到仓根的 gpg-with-passphrase.sh" >&2
exit 2
