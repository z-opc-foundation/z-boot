#!/usr/bin/env bash
#
# deploy_maven_center.sh — z-boot 一键发布到 Maven Central
#
# 子命令：
#   publish [folder...]   按文件夹发布;不带参数=按依赖顺序全发
#                         folder 可用短名 parent / deps / fleet / starter / integration
#   verify     验证 Maven Central 上能否搜到 io.github.yuku123
#   gpg-init   首次发布前生成 GPG 密钥并写 .env
#   readme     打印 z-boot 发布摘要（前置凭证 + 按文件夹发布）
#   help       显示此帮助
#
# 用法：
#   ./deploy_maven_center.sh                       # 全发（按序）
#   ./deploy_maven_center.sh publish fleet          # 只发兄弟仓版本权威（抬一格 L3 版本的日常动作）
#   ./deploy_maven_center.sh publish --dry fleet    # 只 verify 不上传
#   ./deploy_maven_center.sh gpg-init          # 首次必须先跑
#   ./deploy_maven_center.sh verify
#   ./deploy_maven_center.sh readme            # 看发布指引摘要
#
# 设计原则：
#   - 所有凭证从 ./.env 读，.env 已被 .gitignore 排除
#   - GPG 密钥环用 GNUPGHOME=./.gnupg，不污染 ~/.gnupg
#   - 不带参数 = 按 FLEET_ORDER 全发，且是不可撤销的对外发布 ⇒ 只在明确要发版时裸跑
#   - 先验不发用 publish --dry <folder>（只 mvn verify，不签名不上传）
#   - 已发布的版本 Central 不允许覆盖，脚本对每个文件夹先回读 repo1，已 200 的直接跳过
#
# 详细口径见仓根 README 的「发布」一节（1.0.19 起 z-boot 无 ${revision}，按文件夹字面版本发）。
#
set -eo pipefail

# 自动给自己加执行权限（应对 sandbox 写出来的文件没有 +x）
chmod +x "$0" 2>/dev/null || true

# ---------- 颜色 ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1.33m'; NC='\033[0m'
log()  { printf "${GREEN}[deploy]${NC} %s\n" "$*"; }
warn() { printf "${YELLOW}[deploy]${NC} %s\n" "$*"; }
err()  { printf "${RED}[deploy]${NC} %s\n" "$*" >&2; }
die()  { err "$*"; exit 1; }

# ---------- 帮助 ----------
print_help() {
    sed -n '2,16p' "$0"
}

# ---------- 切到 z-boot 根目录(本脚本住在 _doc/003_script/,别在原地跑 mvn) ----------
cd "$(dirname "$0")"
while [[ ! -f pom.xml && "$PWD" != "/" ]]; do cd ..; done
[[ -f pom.xml ]] || die "找不到 z-boot 根 pom(应在 z-boot 仓库内运行此脚本)"
grep -q "<artifactId>z-boot</artifactId>" pom.xml || die "$PWD 不是 z-boot 根目录"

# ---------- 加载 .env ----------
load_env() {
    [[ -f .env ]] || die ".env 不存在。首次发布请先跑：./deploy_maven_center.sh gpg-init"
    # shellcheck disable=SC1091
    set -a; source .env; set +a

    [[ -n "${CENTRAL_USERNAME:-}"    ]] || die ".env 缺 CENTRAL_USERNAME"
    [[ -n "${CENTRAL_TOKEN:-}"       ]] || die ".env 缺 CENTRAL_TOKEN"
    [[ -n "${CENTRAL_GPG_PASSPHRASE:-}" ]] || die ".env 缺 CENTRAL_GPG_PASSPHRASE（先跑 gpg-init）"

    export CENTRAL_USERNAME CENTRAL_TOKEN CENTRAL_GPG_PASSPHRASE
}

# ---------- 依赖检查 ----------
check_deps() {
    command -v mvn >/dev/null 2>&1 || die "mvn 未安装"
    command -v gpg >/dev/null 2>&1 || die "gpg 未安装（brew install gnupg）"

    [[ -f ~/.m2/settings.xml ]] || die "~/.m2/settings.xml 不存在"
    grep -q '<id>central</id>' ~/.m2/settings.xml || die "~/.m2/settings.xml 缺 <server id=\"central\">"

    if [[ -d ./.gnupg ]]; then
        export GNUPGHOME="$PWD/.gnupg"
    else
        warn "未找到 ./.gnupg，请先跑 ./deploy_maven_center.sh gpg-init"
        exit 1
    fi
}

# ---------- 子命令：gpg-init ----------
cmd_gpg_init() {
    command -v gpg >/dev/null 2>&1 || die "gpg 未安装（brew install gnupg）"

    if [[ ! -f .env ]]; then
        cat > .env <<'EOF'
# CentOS Portal User Token（去 Profile → User Token 生成后填入）
CENTRAL_USERNAME=
CENTRAL_TOKEN=

# GPG 私钥 passphrase（gpg-init 自动写入下方 GPG 字段）
CENTRAL_GPG_PASSPHRASE=
GPG_KEY_ID=
GPG_USER_NAME=yuku123 <1340947819@qq.com>
EOF
        die ".env 模板已创建。请填入 CENTRAL_USERNAME 和 CENTRAL_TOKEN 后重跑 gpg-init"
    fi

    # 加载（如果 .env 已填好中央凭证）
    load_env 2>/dev/null || warn ".env 中央凭证未填，但 gpg-init 仍可继续"

    log "生成 GPG RSA 4096 密钥..."
    mkdir -p .gnupg && chmod 700 .gnupg
    cat > .gnupg/gpg.conf <<EOF
pinentry-mode loopback
EOF
    chmod 600 .gnupg/gpg.conf

    export GNUPGHOME="$PWD/.gnupg"
    export GPG_PASSPHRASE="$CENTRAL_GPG_PASSPHRASE"

    gpg --batch --pinentry-mode loopback --passphrase "$GPG_PASSPHRASE" \
        --quick-generate-key "$GPG_USER_NAME" default default 4096

    KEY_ID=$(gpg --list-secret-keys --keyid-format LONG "$GPG_USER_NAME" 2>/dev/null \
             | grep -oE '[A-F0-9]{16}' | head -1)
    [[ -n "$KEY_ID" ]] || die "无法解析 KEY_ID"

    # 把 key id / user name 写回 .env（不动中央凭证）
    sed -i.bak \
        -e "s|^GPG_KEY_ID=.*|GPG_KEY_ID=$KEY_ID|" \
        -e "s|^GPG_USER_NAME=.*|GPG_USER_NAME=$GPG_USER_NAME|" \
        .env && rm -f .env.bak

    log "GPG 密钥生成成功："
    log "  KEY_ID = $KEY_ID"
    log "  公钥指纹 = $(gpg --fingerprint "$KEY_ID" 2>/dev/null | grep -A1 'pub' | tail -1 | tr -s ' ')"

    log "上传公钥到 keys.openpgp.org（Central Portal 从这里拉公钥校验签名）"
    gpg --keyserver hkps://keys.openpgp.org --send-keys "$KEY_ID" 2>&1 || \
        warn "keyserver 上传失败，可手动跑：gpg --keyserver hkps://keys.openpgp.org --send-keys $KEY_ID"

    log "完成。.env 已写入 GPG_KEY_ID=$KEY_ID"
    log "下一步：跑 ./deploy_maven_center.sh publish"
}

# ---------- 子命令：publish ----------
# 1.0.19 起 z-boot 根 pom 只是 parent（没有 <modules>），发版按文件夹为单位：
#   publish                 = 按依赖顺序全发
#   publish fleet           = 只发 z-boot-fleet（parent 若 repo1 已有就跳过）
#   publish deps starter    = 发地板 + 3 个基础 starter
#   publish --dry fleet     = 只 mvn verify 不 deploy（不签名不上传，验 flatten/受管项形状）
# 抬一格兄弟仓版本 = gen_fleet_bom.py --write + publish fleet，其余文件夹不动。
FLEET_ORDER=( "." "z-boot-dependencies" "z-boot-fleet" "z-boot-starter" "z-boot-integration-starters" )
alias_folder() {
    case "$1" in
        .|parent|root)      echo "." ;;
        deps|dependencies)  echo "z-boot-dependencies" ;;
        fleet)              echo "z-boot-fleet" ;;
        starter|starters)   echo "z-boot-starter" ;;
        integration|it)     echo "z-boot-integration-starters" ;;
        *)                  echo "$1" ;;
    esac
}
# 该文件夹对应的 pom 是否已经在 Central 上（同版本不可重发，Central 会 400）
already_live() {
    local folder=$1 aid ver
    [[ -f "$folder/pom.xml" ]] || return 1
    aid=$(python3 -c "
import xml.etree.ElementTree as ET,sys
NS='{http://maven.apache.org/POM/4.0.0}'
r=ET.parse('$folder/pom.xml').getroot()
print(r.findtext(NS+'artifactId',''))")
    ver=$(python3 -c "
import xml.etree.ElementTree as ET
NS='{http://maven.apache.org/POM/4.0.0}'
r=ET.parse('$folder/pom.xml').getroot()
v=r.findtext(NS+'version')
if v is None: v=r.find(NS+'parent').findtext(NS+'version')
print(v)")
    [[ -z "$aid" || -z "$ver" ]] && return 1
    local code
    code=$(curl -s -o /dev/null -w '%{http_code}' -r 0-0 --max-time 25 \
        "https://repo1.maven.org/maven2/io/github/yuku123/$aid/$ver/$aid-$ver.pom")
    [[ "$code" == "200" || "$code" == "206" ]]
}

cmd_publish() {
    load_env
    check_deps

    local dry=0 want=()
    for a in "$@"; do
        case "$a" in
            --dry) dry=1 ;;
            *) want+=("$(alias_folder "$a")") ;;
        esac
    done
    [[ ${#want[@]} -eq 0 ]] && want=("${FLEET_ORDER[@]}")

    # parent 不在发布清单里时，若 repo1 还没有当版 parent，也必须先把它发出去
    if [[ " ${want[*]} " != *" . "* ]]; then
        already_live "." || { log "parent 未发布 → 前置 ."; want=( "." "${want[@]}" ); }
    fi

    log "═══════════════════════════════════════════════════════════════"
    log " 即将发布 z-boot 到 Maven Central   mode=$([[ $dry == 1 ]] && echo dry-run(verify) || echo deploy)"
    log "  groupId : io.github.yuku123"
    log "  folders : ${want[*]}"
    log "  GPG KEY : ${GPG_KEY_ID:-?}"
    log "═══════════════════════════════════════════════════════════════"

    local goal=deploy rc=0 f
    [[ $dry == 1 ]] && goal=verify
    for f in "${want[@]}"; do
        [[ -f "$f/pom.xml" ]] || die "找不到 $f/pom.xml（可用名：parent deps fleet starter integration）"
        if [[ $dry == 0 ]] && already_live "$f"; then
            warn "跳过 $f —— 该版本已在 repo1（Central 不允许覆盖已发布版本）"
            continue
        fi
        rm -rf "$f/target/central-staging" "$f/target/central-publishing" "$f/target/central-deferred" 2>/dev/null
        log "── $f : mvn -B $goal -Pcentral"
        mvn -B -U -Dmaven.legacyLocalRepo=true "$goal" \
            -Pcentral \
            -DskipTests \
            -Dgpg.passphrase="$CENTRAL_GPG_PASSPHRASE" \
            -f "$f/pom.xml" > "/tmp/z-boot-deploy-$(basename "$f").log" 2>&1 || rc=1
        if grep -q "BUILD SUCCESS" "/tmp/z-boot-deploy-$(basename "$f").log"; then
            log "   ✅ $f SUCCESS"
        else
            err "   ✗ $f FAILURE —— tail -30 of /tmp/z-boot-deploy-$(basename "$f").log:"
            tail -30 "/tmp/z-boot-deploy-$(basename "$f").log" | sed 's/^/      /'
        fi
    done
    [[ $rc == 0 ]] || die "有文件夹发布失败，见 /tmp/z-boot-deploy-*.log"
    [[ $dry == 1 ]] && { log "dry-run 完成（未签名、未上传）"; return 0; }
    log ""
    log "✅ 全部文件夹发布流程结束"
    log "Central Portal 控制台：https://central.sonatype.com/publishing/deployments"
    log "逐坐标复核：./deploy_maven_center.sh verify   或   python3 _doc/003_script/gen_fleet_bom.py"
}

# ---------- 子命令：verify ----------
cmd_verify() {
    log "搜索 Maven Central：g:io.github.yuku123"
    sleep 30  # 等 Central Portal 同步
    HTTP=$(curl -s -o /tmp/z-boot-verify.json -w "%{http_code}" \
        "https://search.maven.org/solrsearch/select?q=g:io.github.yuku123&rows=5&wt=json")
    if [[ "$HTTP" == "200" ]]; then
        NUM=$(python3 -c "import json; print(json.load(open('/tmp/z-boot-verify.json'))['response']['numFound'])" 2>/dev/null || echo "?")
        log "Maven Central 上 io.github.yuku123 命名空间有 $NUM 个 artifact"
        [[ "$NUM" != "?" && "$NUM" -gt 0 ]] && log "✅ 发布成功" || warn "⚠️  还没同步完，再等等"
    else
        warn "验证请求 HTTP=$HTTP"
    fi
    log "中央部署状态：https://central.sonatype.com/publishing/deployments"
}

# ---------- 子命令：readme ----------
cmd_readme() {
    cat <<'EOF'
═══════════════════════════════════════════════════════════════
  z-boot 发布到 Maven Central — 摘要（1.0.19 起的按文件夹拓扑）
═══════════════════════════════════════════════════════════════

【前置（人工，一次）】

  1. https://central.sonatype.com/ → Sign in with GitHub → Profile → Generate User Token
     Username + Secret 写到 ./ 的 .env（CENTRAL_USERNAME / CENTRAL_TOKEN /
     CENTRAL_GPG_PASSPHRASE / GPG_KEY_ID）—— **不要贴到对话里**
  2. namespace io.github.yuku123 已验证（GitHub Pages 那条 txt），不用重复做
  3. brew install gnupg；首次跑 ./deploy_maven_center.sh gpg-init（密钥环 ./gnupg，不碰 ~/.gnupg）

【z-boot 没有 ${revision}】

  四个文件夹 + 根都是独立工程，pom 里写的是字面版本：
    .                        z-boot (parent，只带 plugin/profile/flatten 配置，无 <modules>)
    z-boot-dependencies      第三方地板 BOM
    z-boot-fleet             兄弟仓 z-* 版本 BOM（gen_fleet_bom.py 生成，勿手改）
    z-boot-starter           base / web / datasource
    z-boot-integration-starters   20 个 L3 聚合 starter
  所以发版 = 选文件夹，不是全仓重发：

    ./deploy_maven_center.sh publish --dry fleet   # 先只 mvn verify（不签名不上传）
    ./deploy_maven_center.sh publish fleet         # 真发一个文件夹
    ./deploy_maven_center.sh publish               # 全发（按 parent→deps→fleet→starter→integration）

  脚本会：逐文件夹回读 repo1，同版本已上线的直接跳过（Central 不可覆盖，重发只会 400）；
  若 parent 当版还没上线而你要发子文件夹，自动把 parent 前置。日志落 /tmp/z-boot-deploy-<folder>.log。

【抬一格兄弟仓版本（日常）】

  python3 _doc/003_script/gen_fleet_bom.py            # 只看账：每个坐标 repo1 是 OK / PENDING / MISSING
  python3 _doc/003_script/gen_fleet_bom.py --write    # 重算 z-boot-fleet/pom.xml
  ./deploy_maven_center.sh publish --dry fleet && ./deploy_maven_center.sh publish fleet

【判据】

  ✗ BUILD SUCCESS ≠ 已可见。repo1 有 5~50 分钟无 SLA 的索引期，判发布只认 repo1 回读。
  ✗ 探活不能用 HEAD —— repo1/Fastly 对 HEAD 不给 200，用 curl -r 0-0（200/206 才算活着）。
  ✗ 不要把 CENTRAL_TOKEN / GPG passphrase 贴到对话或提交进仓。
  ✓ z-boot-fleet 的 flatten 必须 override 成 resolveCiFriendliesOnly；oss 模式会把整个
    <dependencyManagement> 删掉，发出去的 fleet 就成了空 BOM（本机看不出来，只有外部 import 会炸）。
  ✓ 根 pom 的 <pomElements><properties>keep</properties></pomElements> 不是可选项：
    删了它，外部工程 import z-boot-dependencies 时那些 ${z-*.version} 直接是模型错误。
  ✓ javadoc/sources/GPG 三件套不能跳（Central 硬要求）。

【详细口径】

  仓根 README.md：「🏗️ 项目结构」「🔧 高级 → 升级 z-boot / L3 中间件版本」「发布」

═══════════════════════════════════════════════════════════════
EOF
}

# ---------- 路由 ----------
SUBCMD="${1:-publish}"
shift 2>/dev/null || true
case "$SUBCMD" in
    publish)   cmd_publish "$@" ;;
    verify)    cmd_verify ;;
    gpg-init)  cmd_gpg_init ;;
    readme)    cmd_readme ;;
    help|-h|--help) print_help ;;
    *) die "未知子命令：$SUBCMD（用 help 看用法）" ;;
esac