#!/usr/bin/env bash
# ============================================================
# verify_central.sh — 校验本仓发布件在 Maven Central 上真的可拉
#
# 用法:
#   ./verify_central.sh                 # 自动模式：每个构件用自己 pom 里的 <version>
#   ./verify_central.sh 1.0.6           # 显式模式：全部构件按这个版本验
#   VERIFY_SKIP_SIGNATURE=1 ./verify_central.sh   # 跳过签名检查
#
# ⚠ 为什么默认要「按构件解析版本」，不能只解析一次仓级版本：
#   z-boot 没有 <modules>，每个子目录都是独立发版的工程，版本线各不相同
#   （根 1.0.19 / dependencies 1.0.20 / fleet 1.0.2 / integration-starters 1.0.22）。
#   套仓级版本会让 fleet 被按 1.0.19 查而 404；更隐蔽的是 dependencies 本地
#   已经是 1.0.20，却按 1.0.19 查成 200 —— 「抬了号忘了发」这种欠账就永远看不见。
#   有 <modules> 的仓（如 z-kb）全仓共用一个版本，按构件解析得到的也是同一个值，
#   两种模式等价，所以这个改法对它们是安全的。
#   显式传参时全仓按传入版本验，保留「我想验某个历史版本」的能力。
#
# 校验项（与原 z-middleware-integration-test 的 IT 等价）:
#   1. 每个构件的 .pom 可达
#   2. jar 构件额外要求 .jar / -sources.jar / -javadoc.jar / .asc 签名
#   3. 聚合 POM（packaging=pom）只要 .pom + .asc
#   4. 抽样构件的 POM metadata 完整（groupId/artifactId/version/name/license/scm/developers）
#   5. 抽样 jar 的 sources.jar 里含指定类
#
# 退出码: 0 全绿 / 1 有 FAIL
# ============================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 仓根 = 从本脚本所在目录向上找第一个带 pom.xml 的目录。
# 不用固定的 ../.. —— 脚本目录深度各仓不同（_doc/003_script 是两层，z-mcp/tools 是一层）。
REPO_ROOT="$SCRIPT_DIR"
while [ ! -f "$REPO_ROOT/pom.xml" ] && [ "$REPO_ROOT" != "/" ]; do
    REPO_ROOT="$(dirname "$REPO_ROOT")"
done
[ -f "$REPO_ROOT/pom.xml" ] || { echo "[verify] 找不到仓根 pom.xml（从 $SCRIPT_DIR 向上）"; exit 1; }
GROUP_ID="${VERIFY_GROUP_ID:-io.github.yuku123}"
CENTRAL="${CENTRAL_BASE:-https://repo1.maven.org/maven2}"
SKIP_SIG="${VERIFY_SKIP_SIGNATURE:-0}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[verify]${NC} $1"; }
warn() { echo -e "${YELLOW}[verify]${NC} $1"; }
err()  { echo -e "${RED}[verify]${NC} $1"; FAIL=$((FAIL+1)); }

cd "$REPO_ROOT"

# ---------- 版本 ----------
FAIL=0   # 先初始化：报错路径上也要能记账，否则 set -u 直接崩、连「失败」都报不出来
TOTAL=0
VERSION="${1:-}"
EXPLICIT=""
[ -n "$VERSION" ] && EXPLICIT=1
if [ -z "$VERSION" ]; then
    VERSION=$(python3 - <<'PY'
import re, sys
try:
    s = open('pom.xml', encoding='utf-8').read()
except Exception:
    sys.exit(1)
# 优先 properties/revision，其次根 pom 的字面 <version>
m = re.search(r'<revision>([^<]+)</revision>', s)
if m:
    print(m.group(1).strip()); sys.exit(0)
# 无 ${revision} 的仓：取**根工程自己的** <version>，也就是 <artifactId>本工程</> 紧跟的那个。
# ⚠ 三个坑，逐个都真实踩过：
#   ① 不能取第一个 <version> —— 那会命中 <parent> 里的（z-graph: parent 1.0.21 /
#      根工程 1.0.8，误取 parent ⇒ 全表 404）
#   ② 有的仓根 pom 的 <version> 字面就是自引用 ${project.version}（z-graph / z-gw / z-kb
#      三个都是），字面解析到此为止 ⇒ 交给 mvn help:evaluate 兜底
#   ③ 解析结果若仍含 ${ 就不算版本，直接报，不让它去 Central 探一圈 404 回来
root_artifact = re.search(r'</parent>.*?<artifactId>([^<]+)</artifactId>', s, re.S)
if root_artifact:
    aid = re.escape(root_artifact.group(1).strip())
    m = re.search(r'</parent>.*?<artifactId>' + aid + r'</artifactId>\s*<version>([^<]+)</version>', s, re.S)
    if m and '${' not in m.group(1):
        print(m.group(1).strip()); sys.exit(0)
print('')   # 空 ⇒ 交给调用方走 mvn 兜底
PY
)
    # 字面解析不出来（自引用 ${project.version}）⇒ 问 Maven 自己要
    if [ -z "$VERSION" ]; then
        VERSION=$(mvn -q help:evaluate -Dexpression=project.version -DforceStdout 2>/dev/null | tail -1 | tr -d '[:space:]')
    fi
fi
[ -z "$VERSION" ] && { err "无法解析本仓版本（pom 字面与 mvn 都问不出），请显式传参：./verify_central.sh <version>"; exit 1; }
case "$VERSION" in
    *'${'*) err "版本解析得到的是未展开的串 ${VERSION}；请显式传参 ./verify_central.sh <version>"; exit 1 ;;
esac
log "仓: $(basename "$REPO_ROOT")  groupId: $GROUP_ID"
if [ -n "$EXPLICIT" ]; then
    log "模式: 显式指定版本 ${VERSION}（全部构件按此版本验）"
else
    log "模式: 自动解析（各构件用自己 pom 里的 <version>；仓级 $VERSION 仅作兜底）"
fi

# ---------- 构件清单 + packaging + 各构件自己的版本 ----------
# 聚合 POM（packaging=pom）没有 jar；其余按 jar 处理。
SPEC=$(python3 - "$VERSION" "$EXPLICIT" <<'PY'
import os, re, sys
import xml.etree.ElementTree as ET
NS = '{http://maven.apache.org/POM/4.0.0}'
fallback = sys.argv[1]
explicit = sys.argv[2] == '1'

def t(e, tag):
    x = e.find(NS + tag)
    return (x.text or '').strip() if x is not None else ''

def own_version(r):
    """本 pom 声明的版本。拿不到就返回 None，让调用方回退到继承来的。
    ⚠ 用 ET 的 root.find('version') 而不是正则：它只取 <project> 的直接子节点，
    天然跳过 <parent> 里那个 —— 仓级解析踩过的「误取 parent」在这里不会再犯。"""
    props = r.find(NS + 'properties')
    if props is not None:
        rev = props.find(NS + 'revision')
        if rev is not None and rev.text and '${' not in rev.text:
            return rev.text.strip()
    v = r.find(NS + 'version')
    if v is not None and v.text and '${' not in v.text:
        return v.text.strip()
    return None

out = []
seen = set()
def scan(pom_path, module_hint, inherited, allow_dir_scan=True):
    rp = os.path.realpath(pom_path)
    if rp in seen:          # 防环 + 防重复
        return
    seen.add(rp)
    r = ET.parse(pom_path).getroot()
    aid = t(r, 'artifactId')
    pack = t(r, 'packaging') or 'jar'
    mine = own_version(r)
    # 显式传参时全仓按那个版本验（保持 verify_central.sh <version> 的既有语义）；
    # 自动模式下每个构件用自己 pom 里的版本 —— z-boot 每个子目录是独立发版工程，
    # 套仓级版本会让 z-boot-fleet(1.0.2) 被按 1.0.19 查而 404，
    # 更糟的是 dependencies 本地 1.0.20 会被按 1.0.19 查成 200 ⇒ 抬号未发也看不出来。
    ver = fallback if explicit else (mine or inherited or fallback)
    # ⚠ 原先这里有一条 `not aid.endswith('-parent')` 的排除，把 `z-boot-parent` 整个排掉了 ——
    #   而它正是本仓的**消费入口**（中央上确实发布，1.0.23 实测 200），从来没被第 1 段验过。
    #   本仓不需要「parent 一律不发」这条例外：根件 artifactId 是 `z-boot`（不带该后缀），
    #   带上后缀的只有 z-boot-parent 这一个，而它是发的。去掉。
    if aid:
        out.append((aid, pack, ver))
    mods = [ (m.text or '').strip() for m in r.iter(NS + 'module') ]
    if mods:
        for m in mods:
            p = os.path.join(os.path.dirname(pom_path), m, 'pom.xml')
            if os.path.isfile(p):
                scan(p, m, ver, allow_dir_scan=False)
    elif allow_dir_scan:
        # 无 <modules> 的仓（如 z-boot：每个子目录是独立可发工程）。
        # 只向下扫一层，且跳过 _ 前缀目录，避免顺着嵌套结构无限下钻。
        for name in sorted(os.listdir('.')):
            if name.startswith('.') or name.startswith('_') or name in ('target', 'node_modules'):
                continue
            p = os.path.join(name, 'pom.xml')
            if os.path.isdir(name) and os.path.isfile(p):
                scan(p, name, ver, allow_dir_scan=False)
root_ver = own_version(ET.parse('pom.xml').getroot()) or fallback
scan('pom.xml', '', root_ver)
for aid, pack, ver in sorted(set(out)):
    print(f"{aid}\t{pack}\t{ver}")
PY
)
[ -z "$SPEC" ] && { err "未能从 pom.xml 解析出构件清单"; exit 1; }

# ---------- 探测 ----------
probe() {  # $1=url → http code
    # 只取 curl 的 %{http_code}。curl 自身失败（非 0 退出）时 stdout 可能仍带残缺输出，
    # 早期写法 `curl ... || echo 000` 会把两者粘在一起（真出现过 "200000" 这种 6 位码）
    # ⇒ 统一在这里收口，并把结果规整成 3 位。
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$1" 2>/dev/null)
    code=$(printf '%s' "$code" | grep -oE '^[0-9]{3}$' || true)
    printf '%s' "${code:-000}"
}
fetch() { curl -s --max-time 30 "$1" 2>/dev/null; }

FAIL=0; TOTAL=0
# 不发 Central 的构件（独立部署应用等）。用 verify-exclude.txt 逐行写 artifactId。
EXCLUDE_FILE="verify-exclude.txt"
is_excluded() {
    [ -f "$SCRIPT_DIR/$EXCLUDE_FILE" ] || return 1
    grep -qx "$1" "$SCRIPT_DIR/$EXCLUDE_FILE"
}
echo ""
echo "──────── 1. 构件可达性 ────────"
while IFS=$'\t' read -r aid pack av; do
    [ -z "$aid" ] && continue
    if is_excluded "$aid"; then
        warn "⏭  $aid — 按 $EXCLUDE_FILE 声明不发 Central，跳过"
        continue
    fi
    TOTAL=$((TOTAL+1))
    base="$CENTRAL/${GROUP_ID//.//}/$aid/$av/$aid-$av"
    code=$(probe "$base.pom")
    if [ "$code" = "200" ]; then
        extra=""
        if [ "$pack" = "jar" ]; then
            for suf in .jar -sources.jar -javadoc.jar; do
                c=$(probe "$base$suf")
                [ "$c" = "200" ] || { extra="$extra $suf:$c"; }
            done
        fi
        if [ "$SKIP_SIG" != "1" ]; then
            c=$(probe "$base.pom.asc")
            [ "$c" = "200" ] || extra="$extra .pom.asc:$c"
        fi
        if [ -n "$extra" ]; then
            err "$aid $av — 缺失:$extra"
        elif [ "$av" != "$VERSION" ]; then
            # 版本与仓级不同的构件（无 <modules>、子工程独立发版的仓，如 z-boot）
            log "✅ $aid ($pack) @ $av"
        else
            log "✅ $aid ($pack)"
        fi
    else
        err "$aid $av — .pom HTTP $code"
    fi
done <<< "$SPEC"

# ---------- 抽样 POM metadata ----------
echo ""
echo "──────── 2. POM metadata ────────"
SAMPLE=$(echo "$SPEC" | awk -F'\t' '$2=="jar"{print $1"\t"$3}' | while IFS=$'\t' read -r a v; do
    is_excluded "$a" || printf '%s\t%s\n' "$a" "$v"
done | head -1)
if [ -n "$SAMPLE" ]; then
    SAMPLE_AID=$(echo "$SAMPLE" | cut -f1)
    SAMPLE_VER=$(echo "$SAMPLE" | cut -f2)
    content=$(fetch "$CENTRAL/${GROUP_ID//.//}/$SAMPLE_AID/$SAMPLE_VER/$SAMPLE_AID-$SAMPLE_VER.pom")
    for tag in groupId artifactId version name license scm developers; do
        if echo "$content" | grep -q "<$tag>"; then
            log "✅ $SAMPLE_AID 含 <$tag>"
        else
            err "$SAMPLE_AID 缺 <$tag>（Central Portal 强制要求）"
        fi
    done
    # ⚠ ${VAR} 不能写成 $VAR：后面紧跟的全角标点（如「）」）在非 UTF-8 locale 下
    #   会被 bash 吞进变量名，报 "SAMPLE_VER?: unbound variable"。
    echo "$content" | grep -q "<version>${SAMPLE_VER}</version>" \
        && log "✅ ${SAMPLE_AID} version 与验的版本一致（${SAMPLE_VER}）" \
        || err "${SAMPLE_AID} version 与 ${SAMPLE_VER} 不一致"
else
    warn "无 jar 构件，跳过 POM metadata 抽检"
fi

# ---------- 抽样 sources.jar 含类 ----------
# 用 <artifactId>verify-classes.txt</> 声明要抽检的类（相对 sources.jar 内路径）。
CLASSPICK="verify-classes.txt"
SRCJAR=""
LISTING=""
CANDIDATE=""
CANDIDATE_VER=""
# artifactId → 它自己的版本（自动模式下各构件版本可能不同，如 z-boot 的 fleet 1.0.2）。
# ⚠ 用 awk 查表而不是 `declare -A` 关联数组：macOS 自带 bash 是 3.2，没有关联数组，
#   写了会直接 "declare: -A: invalid option" 把整个脚本打断。
ver_of() {  # $1=artifactId
    printf '%s\n' "$SPEC" | awk -F'\t' -v a="$1" '$1==a {print $3; exit}'
}
if [ -f "$SCRIPT_DIR/$CLASSPICK" ]; then
    echo ""
    echo "──────── 3. sources.jar 内容抽检 ────────"
    # 逐行：跳过空行与 # 注释；每行必须能 cut 出 artifactId 与路径两段。
    while IFS= read -r cls || [ -n "$cls" ]; do
        cls="${cls%%$'\r'}"                 # 兼容 CRLF
        case "$cls" in
            ""|\#*) continue ;;
        esac
        aid=$(echo "$cls" | cut -d: -f1)
        path=$(echo "$cls" | cut -d: -f2-)
        aid="$(echo "$aid" | tr -d '[:space:]')"
        path="$(echo "$path" | tr -d '[:space:]')"
        if [ -z "$aid" ] || [ -z "$path" ] || [ "$aid" = "$cls" ]; then
            err "无法解析 $CLASSPICK 的一行（需为 <artifactId>:<类路径>）：$cls"
            continue
        fi
        av=$(ver_of "$aid"); av="${av:-$VERSION}"
        if [ "$aid" != "$CANDIDATE" ]; then
            # 换了 artifactId ⇒ 换一份 sources.jar
            [ -n "$SRCJAR" ] && rm -f "$SRCJAR" 2>/dev/null
            CANDIDATE="$aid"
            CANDIDATE_VER="$av"
            # unzip -l 要求可 seek 的文件，进程替换（/dev/fd/N）会报
            # "End-of-central-directory signature not found" ⇒ 先落临时文件。
            SRCJAR=$(mktemp -t verify-sources.XXXXXX.jar)
            curl -s --max-time 60 -o "$SRCJAR" \
                "$CENTRAL/${GROUP_ID//.//}/$CANDIDATE/$av/$CANDIDATE-$av-sources.jar"
            LISTING=$(unzip -l "$SRCJAR" 2>/dev/null)
            if [ -z "$LISTING" ]; then
                err "$CANDIDATE $av sources.jar 下载或读取失败（判据本身坏了，该结论不作数）"
                SRCJAR=""; LISTING=""
            fi
        fi
        [ -z "$SRCJAR" ] && continue
        if echo "$LISTING" | grep -q " $path\$"; then
            log "✅ $path 在 $aid sources.jar 中"
        else
            err "$path 不在 $aid sources.jar 中（改名后包路径可能未同步）"
        fi
    done < "$SCRIPT_DIR/$CLASSPICK"
    [ -n "$SRCJAR" ] && rm -f "$SRCJAR" 2>/dev/null
else
    warn "无 ${CLASSPICK}，跳过 sources.jar 抽检；可新建该文件逐行写 <artifactId>:<类路径>"
fi

# ---------- 发布件内容比对（版本可达 ≠ 内容是最新的） ----------
# 上面三段验的都是「这个坐标这个版本能不能拉到」。拉得到 200 就绿，但那个版本的 pom 里
# 装的是什么没人看 —— 于是「改了没发 / 坐标族改名 / 版本格抬了没发」这三类一律漏。
# 本段把线上 pom 拉下来，与本地源码 pom 做**结构性**比对：
#   ① dependencyManagement 里受管的 <artifactId> 集合（抓改名、增删）
#   ② <properties> 各键的值（抓抬号没发）
# 清单见 verify-content.txt，逐行一个 artifactId。
CONTENTPICK="verify-content.txt"
if [ -f "$SCRIPT_DIR/$CONTENTPICK" ]; then
    echo ""
    echo "──────── 4. 发布件内容比对 ────────"
    while IFS= read -r caid || [ -n "$caid" ]; do
        caid="${caid%%$'\r'}"
        case "$caid" in ""|\#*) continue ;; esac
        caid="$(echo "$caid" | tr -d '[:space:]')"
        [ -z "$caid" ] && continue

        # ① 该构件在仓里是哪个 pom（构建清单时记过 module_hint，这里重新定位）
        cpom=$(find "$REPO_ROOT" -maxdepth 3 -name pom.xml -not -path "*/target/*" -not -path "*/.*" \
               -print0 2>/dev/null | xargs -0 grep -l "<artifactId>${caid}</artifactId>" 2>/dev/null | head -1)
        if [ -z "$cpom" ]; then
            err "${caid} — 仓里找不到它的 pom.xml（清单与仓不同步？）"
            continue
        fi
        cav=$(ver_of "$caid"); cav="${cav:-$VERSION}"

        livep=$(mktemp -t verify-live.XXXXXX.pom)
        curl -s --max-time 40 -o "$livep" \
            "$CENTRAL/${GROUP_ID//.//}/$caid/$cav/$caid-$cav.pom"
        # ⚠ 判据必须是"能不能解析成 pom 的根元素"，不是看首行含不含 project：
        #   pom 首行是 `<?xml version="1.0" ...?>`，不含 project ⇒ 早先那版判据恒不成立，
        #   两个构件都被报成"取不到"，而真相是判据坏了。交给解析器判最稳。
        if ! python3 -c "
import sys
import xml.etree.ElementTree as ET
try:
    r = ET.parse(sys.argv[1]).getroot()
except Exception:
    sys.exit(1)
sys.exit(0 if r.tag.endswith('project') else 1)
" "$livep" 2>/dev/null; then
            err "${caid} ${cav} 线上 pom 取不到或不是 pom（判据本身坏了，该结论不作数）"
            rm -f "$livep" 2>/dev/null
            continue
        fi

        out=$(python3 - "$cpom" "$livep" <<'PY'
import sys
import xml.etree.ElementTree as ET
NS = '{http://maven.apache.org/POM/4.0.0}'

def load(p):
    return ET.parse(p).getroot()

def managed(root):
    dm = root.find(NS + 'dependencyManagement')
    out = set()
    if dm is None:
        return out
    for d in dm.iter(NS + 'dependency'):
        a = d.find(NS + 'artifactId')
        if a is not None and (a.text or '').strip():
            out.add((a.text or '').strip())
    return out

def props(root):
    e = root.find(NS + 'properties')
    return {c.tag.replace(NS, ''): (c.text or '').strip() for c in e} if e is not None else {}

loc, live = load(sys.argv[1]), load(sys.argv[2])
lm, vm = managed(loc), managed(live)
lp, vp = props(loc), props(live)

# 只报「同族」差异：受管坐标是纯版本格（${...}）或兄弟仓坐标，逐个列会淹掉真信号
lines = []
only_live = sorted(vm - lm)
only_local = sorted(lm - vm)
if only_live:
    lines.append("  受管坐标只在线上有（改名/下线未传播）: " + ", ".join(only_live[:8])
                 + (" ..." if len(only_live) > 8 else ""))
if only_local:
    lines.append("  受管坐标只在本地有（新增/改名未发布）: " + ", ".join(only_local[:8])
                 + (" ..." if len(only_local) > 8 else ""))
for k in sorted(set(lp) & set(vp)):
    if lp[k] != vp[k]:
        lines.append("  %s: 线上=%s  本地=%s" % (k, vp[k], lp[k]))
for k in sorted(set(vp) - set(lp)):
    lines.append("  %s: 只在线上有（线上=%s，本地已删）" % (k, vp[k]))
for k in sorted(set(lp) - set(vp)):
    lines.append("  %s: 只在本地有（本地=%s，线上没有 ⇒ 没发）" % (k, lp[k]))
if not lines:
    print("SAME")
else:
    print("DIFF")
    print("\n".join(lines))
PY
)
        rm -f "$livep" 2>/dev/null
        if [ "$out" = "SAME" ]; then
            log "✅ ${caid} ${cav} 发布件内容与本地源码一致"
        elif [ -z "$out" ]; then
            err "${caid} ${cav} 内容比对没跑出结果（判据坏了，该结论不作数）"
        else
            err "${caid} ${cav} 发布件内容与本地源码不一致 —— 改了没抬版本，或抬了没发："
            printf '%s\n' "$out" | tail -n +2 | while IFS= read -r l; do warn "  ${l}"; done
        fi
        sleep 2
    done < "$SCRIPT_DIR/$CONTENTPICK"
else
    warn "无 ${CONTENTPICK}，跳过发布件内容比对；可新建该文件逐行写 <artifactId>"
fi

# ---------- 收口 ----------
echo ""
if [ "$FAIL" -eq 0 ]; then
    if [ -n "$EXPLICIT" ]; then
        log "✅ 全绿：$TOTAL 个构件在 Central 上均可拉，版本 ${VERSION}（显式指定）"
    else
        # 自动模式下各构件版本可能不同，把实际验的版本组合列出来，
        # 免得"全绿"看不出到底验了哪些号
        VERSIONS=$(echo "$SPEC" | awk -F'\t' '{print $3}' | sort -u | tr '\n' ' ')
        log "✅ 全绿：$TOTAL 个构件在 Central 上均可拉（各构件用自己 pom 的版本：${VERSIONS% }）"
    fi
    exit 0
else
    err "❌ $FAIL 项失败 / 共 $TOTAL 个构件"
    exit 1
fi
