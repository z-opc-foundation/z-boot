#!/usr/bin/env bash
#
# deploy_maven_center.sh — z-boot 一键发布到 Maven Central
#
# 子命令：
#   publish [folder...]   按文件夹发布;不带参数=按依赖顺序全发
#                         folder 可用短名 root / deps / fleet / parent / starter / integration
#   verify     验证 Maven Central 上能否搜到 io.github.yuku123
#   gpg-init   首次发布前生成 GPG 密钥并写 .env
#   bundle     点件：<path>/central-bundle.zip 逐坐标核 pom/jar/sources/javadoc + .asc
#   readme     打印 z-boot 发布摘要（前置凭证 + 按文件夹发布）
#   help       显示此帮助
#
# 用法：
#   bash _doc/003_script/deploy_maven_center.sh                       # 全发（按序）
#   bash _doc/003_script/deploy_maven_center.sh publish fleet          # 只发兄弟仓版本权威（抬一格 L3 版本的日常动作）
#   bash _doc/003_script/deploy_maven_center.sh publish --dry fleet    # 只 mvn verify：编译+sources+javadoc+gpg 签名，不打包不上传
#   bash _doc/003_script/deploy_maven_center.sh publish --bundle fleet # bundle 演练：按发布态打包，只把上传掐死，逐坐标点件
#   bash _doc/003_script/deploy_maven_center.sh bundle /tmp/xxx/central-publishing/central-bundle.zip  # 点别的仓的包
#   bash _doc/003_script/deploy_maven_center.sh gpg-init          # 首次必须先跑
#   bash _doc/003_script/deploy_maven_center.sh verify
#   bash _doc/003_script/deploy_maven_center.sh readme            # 看发布指引摘要
#
# 设计原则：
#   - 所有凭证从 ./.env 读，.env 已被 .gitignore 排除
#   - GPG 密钥环用仓库根的 .gnupg（load_env 里 export GNUPGHOME），不污染 ~/.gnupg
#   - 不带参数 = 按 FLEET_ORDER 全发，且是不可撤销的对外发布 ⇒ 只在明确要发版时裸跑
#   - 先验不发用 publish --dry <folder>（到 verify 为止）；要看 bundle 的真实内容用 --bundle
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
    sed -n '2,22p' "$0"
}

# ---------- 切到 z-boot 根目录(本脚本住在 _doc/003_script/,别在原地跑 mvn) ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"
while [[ ! -f pom.xml && "$PWD" != "/" ]]; do cd ..; done
[[ -f pom.xml ]] || die "找不到 z-boot 根 pom(应在 z-boot 仓库内运行此脚本)"
grep -q "<artifactId>z-boot</artifactId>" pom.xml || die "$PWD 不是 z-boot 根目录"

# ---------- 加载 .env ----------
load_env() {
    [[ -f .env ]] || die ".env 不存在。首次发布请先跑：bash _doc/003_script/deploy_maven_center.sh gpg-init"
    # shellcheck disable=SC1091
    set -a; source .env; set +a

    [[ -n "${CENTRAL_USERNAME:-}"    ]] || die ".env 缺 CENTRAL_USERNAME"
    [[ -n "${CENTRAL_TOKEN:-}"       ]] || die ".env 缺 CENTRAL_TOKEN"
    [[ -n "${CENTRAL_GPG_PASSPHRASE:-}" ]] || die ".env 缺 CENTRAL_GPG_PASSPHRASE（先跑 gpg-init）"

    export CENTRAL_USERNAME CENTRAL_TOKEN CENTRAL_GPG_PASSPHRASE

    # 密钥环在本仓的 .gnupg 里（~/.gnupg 实测 0 把私钥，不导就直接 gpg 签名失败）
    [[ -d "$PWD/.gnupg" ]] && export GNUPGHOME="$PWD/.gnupg"
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
        warn "未找到 ./.gnupg，请先跑 bash _doc/003_script/deploy_maven_center.sh gpg-init"
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
    log "下一步：跑 bash _doc/003_script/deploy_maven_center.sh publish"
}

# ---------- 子命令：publish ----------
# 1.0.19 起 z-boot 根 pom 只是发布用 pom（没有 <modules>），发版按文件夹为单位：
#   publish                 = 按依赖顺序全发
#   publish fleet           = 只发 z-boot-fleet（根 pom 若 repo1 已有就跳过）
#   publish parent          = 只发 z-boot-parent（消费入口；fleet 未发时自动前置）
#   publish deps starter    = 发地板 + 3 个基础 starter
#   publish --dry fleet     = 只 mvn verify 不 deploy（不签名不上传，验 flatten/受管项形状）
# 抬一格兄弟仓版本 = gen_fleet_bom.py --write + publish fleet，其余文件夹不动。
#
# 顺序不是审美问题，是硬依赖：fleet 1.0.0 被 20 个叶子 starter 的 <dependencyManagement>
# 按字面版本 import（z-boot-integration-starters/*/pom.xml:64），而 z-boot-parent 也 import 它。
# Central 上 fleet 一个版本都没有 ⇒ integration/parent 从干净机器发必然 "Non-resolvable import POM"
# —— 1.0.19 那次 integration 整文件夹没落进 Central（repo1 只到 1.0.18），本机 ~/.m2 装过就看不出来。
# 所以 fleet 一旦发出去就是 immutable：发之前必须 `gen_fleet_bom.py --write` 重算 + 逐件复核。
FLEET_ORDER=( "." "z-boot-dependencies" "z-boot-fleet" "z-boot-parent" "z-boot-starter" "z-boot-integration-starters" )
alias_folder() {
    case "$1" in
        .|root)             echo "." ;;
        # "parent" 这里指 z-boot-parent 这个文件夹（消费入口），不是根 pom —— 根 pom 用 root 或 "."。
        # 1.0.19 之前短名 parent 是给根 pom 用的，文档里那几处已经一起改成 root。
        parent)             echo "z-boot-parent" ;;
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

# 逐坐标点 4 件套（pom/jar/sources.jar/javadoc.jar + 各自 .asc）。
# 为什么必须有这一步：零源码模块会让 source/javadoc 插件静默不产件，mvn 依然 BUILD
# SUCCESS，只数 bundle 总文件数看不见 —— 而 Central 是按坐标逐个数件的，缺一件整批判
# FAILED，且这一步只在上传之后才暴露，等于把失败推到一小时滞后的队列里去发现。
bundle_audit() {
    python3 - "$1" <<'PY'
import sys, zipfile
from collections import defaultdict

P = "io/github/yuku123/"
coords = defaultdict(set)
with zipfile.ZipFile(sys.argv[1]) as z:
    for n in z.namelist():
        if n.endswith("/") or not n.startswith(P):
            continue
        q = n[len(P):].split("/")
        if len(q) >= 3:
            coords[(q[0], q[1])].add("/".join(q[2:]))

bad = 0
for key in sorted(coords):
    a, v = key
    files, out = coords[key], []
    b = a + "-" + v
    need = [b + ".pom"]
    if b + ".jar" in files:
        need += [b + "-sources.jar", b + "-javadoc.jar"]
    out += ["缺 " + x[len(b):].lstrip("-.") for x in need if x not in files]
    out += ["缺 .asc: " + x for x in need if x + ".asc" not in files]
    out += ["多出 maven-metadata"] if any("maven-metadata" in x for x in files) else []
    if out:
        bad += 1
        print("      ✗ %s/%s  %s" % (a, v, "; ".join(out)))
    else:
        print("      ✅ %s/%s  %s 齐" % (a, v,
              "pom" if b + ".jar" not in files else "pom+jar+sources+javadoc"))
print("   坐标 %d 个 / 缺件 %d 个" % (len(coords), bad))
sys.exit(1 if bad or not coords else 0)
PY
}

cmd_publish() {
    load_env
    check_deps

    local dry=0 bundle=0 want=()
    for a in "$@"; do
        case "$a" in
            --dry) dry=1 ;;
            --bundle) bundle=1 ;;
            *) want+=("$(alias_folder "$a")") ;;
        esac
    done
    [[ ${#want[@]} -eq 0 ]] && want=("${FLEET_ORDER[@]}")

    # 根 pom 不在发布清单里时，若 repo1 还没有当版根 pom，也必须先把它发出去
    if [[ " ${want[*]} " != *" . "* ]]; then
        already_live "." || { log "根 pom 未发布 → 前置 ."; want=( "." "${want[@]}" ); }
    fi
    # fleet 是 integration / parent 的 import 目标：它不在清单里而当版没上线时，自动前置，
    # 否则那 20 个 starter（或 parent）在 Central 上是一条解不开的 import。
    if [[ " ${want[*]} " == *" z-boot-integration-starters "* || " ${want[*]} " == *" z-boot-parent "* ]]; then
        if [[ " ${want[*]} " != *" z-boot-fleet "* ]] && ! already_live "z-boot-fleet"; then
            log "z-boot-fleet 当版未发布 → 前置 fleet（integration/parent 的 <dependencyManagement> import 它）"
            want=( "z-boot-fleet" "${want[@]}" )
        fi
    fi

    local mode=deploy
    # 上面两个前置是在清单两头插队，顺序可能已经乱 ⇒ 按 FLEET_ORDER 重排一次
    # （根 → deps → fleet → parent → starter → integration；发出去的东西只能引用更早发出去的）
    local sorted=() fo wi
    for fo in "${FLEET_ORDER[@]}"; do
        for wi in "${want[@]}"; do [[ "$wi" == "$fo" ]] && sorted+=("$fo"); done
    done
    want=("${sorted[@]}")
    [[ $dry == 1 ]] && mode='dry-run(verify)'
    [[ $bundle == 1 ]] && mode='bundle 演练(不上传)'
    log "═══════════════════════════════════════════════════════════════"
    log " 即将发布 z-boot 到 Maven Central   mode=$mode"
    log "  groupId : io.github.yuku123"
    log "  folders : ${want[*]}"
    log "  GPG KEY : ${GPG_KEY_ID:-?}"
    log "═══════════════════════════════════════════════════════════════"

    local goal=deploy rc=0 f logf
    [[ $dry == 1 ]] && goal=verify
    # --bundle 把上传目标指到一个解析不了的域名：staging / 签名 / 打包全按发布态真跑，
    # 只有一件不发出去 —— 上传。这是唯一能"不上传就验掉 bundle 内容"的路子
    # （excludeArtifacts 有没有生效、pom-only 模块少没少件，肉眼在 verify 里都看不见）。
    local extra=()
    [[ $bundle == 1 ]] && extra=(-DcentralBaseUrl=https://central-rehearsal.invalid)
    for f in "${want[@]}"; do
        [[ -f "$f/pom.xml" ]] || die "找不到 $f/pom.xml（可用名：root deps fleet parent starter integration）"
        # 根文件夹是 "."，basename 出来是一个点，日志名会成 z-boot-deploy-..log
        logf="/tmp/z-boot-deploy-$( [[ "$f" == "." ]] && echo root || basename "$f" ).log"
        if [[ $dry == 0 && $bundle == 0 ]] && already_live "$f"; then
            warn "跳过 $f —— 该版本已在 repo1（Central 不允许覆盖已发布版本）"
            continue
        fi
        rm -rf "$f/target/central-staging" "$f/target/central-publishing" "$f/target/central-deferred" 2>/dev/null
        log "── $f : mvn -B $goal -Pcentral${extra:+ ${extra[*]}}"
        mvn -B -U -Dmaven.legacyLocalRepo=true "$goal" \
            -Pcentral \
            -DskipTests \
            -Dgpg.passphrase="$CENTRAL_GPG_PASSPHRASE" \
            ${extra[@]+"${extra[@]}"} \
            -f "$f/pom.xml" > "$logf" 2>&1 || true
        if [[ $bundle == 1 ]]; then
            # 这一模式里 mvn 必然非 0（上传被 DNS 掐死），判成功只认 bundle 有没有打出来
            local zip="$f/target/central-publishing/central-bundle.zip"
            if [[ -f "$zip" ]]; then
                log "   📦 $f bundle = $(unzip -l "$zip" | tail -1 | awk '{print $2}') 个文件 / $(du -h "$zip" | cut -f1)"
                bundle_audit "$zip" || { rc=1; err "   ✗ $f bundle 有点件缺口，见上"; }
            else
                rc=1; err "   ✗ $f 没打出 bundle —— tail -30 of $logf:"; tail -30 "$logf" | sed 's/^/      /'
            fi
        elif grep -q "BUILD SUCCESS" "$logf"; then
            log "   ✅ $f SUCCESS"
        else
            rc=1
            err "   ✗ $f FAILURE —— tail -30 of $logf:"
            tail -30 "$logf" | sed 's/^/      /'
            log "   查 Central 收下没有（有约一小时滞后，看不到不等于没进队列）:"
            log "   curl -u \"\$CENTRAL_USERNAME:\$CENTRAL_TOKEN\" 'https://central.sonatype.com/api/v1/publisher/deployments?page=1&size=5'"
        fi
    done
    [[ $rc == 0 ]] || die "有文件夹失败，见 /tmp/z-boot-deploy-*.log"
    [[ $dry == 1 ]] && { log "dry-run 完成（跑了编译 + sources + javadoc + gpg 签名，未上传）"; return 0; }
    [[ $bundle == 1 ]] && { log "bundle 演练完成（按发布态打了包，一件都没上传）"; return 0; }
    log ""
    log "✅ 全部文件夹发布流程结束"
    log "Central Portal 控制台：https://central.sonatype.com/publishing/deployments"
    log "逐坐标复核：bash _doc/003_script/deploy_maven_center.sh verify   或   python3 _doc/003_script/gen_fleet_bom.py"
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
  3. brew install gnupg；首次跑 bash _doc/003_script/deploy_maven_center.sh gpg-init（密钥环 ./gnupg，不碰 ~/.gnupg）

【z-boot 没有 ${revision}】

  五个文件夹 + 根都是独立工程，pom 里写的是字面版本：
    .                        z-boot 根 pom（只带 plugin/profile/flatten 配置，无 <modules>；短名 root）
    z-boot-dependencies      第三方地板 BOM
    z-boot-fleet             兄弟仓 z-* 版本 BOM（gen_fleet_bom.py 生成，勿手改）
    z-boot-parent            消费入口 parent：继承地板 + import fleet + 下发 Java 8 构建口径（短名 parent）
    z-boot-starter           base / web / datasource
    z-boot-integration-starters   20 个 L3 聚合 starter
  所以发版 = 选文件夹，不是全仓重发：

    bash _doc/003_script/deploy_maven_center.sh publish --dry fleet     # 只 mvn verify：编译+sources+javadoc+gpg 签名都跑，不打包不上传
    bash _doc/003_script/deploy_maven_center.sh publish --bundle fleet  # bundle 演练：连打包都跑，只把上传目标指到不可达域名
    bash _doc/003_script/deploy_maven_center.sh publish fleet           # 真发一个文件夹
    bash _doc/003_script/deploy_maven_center.sh publish                 # 全发（按 root→deps→fleet→parent→starter→integration）

  --dry 看不出 bundle 里到底有什么（pom-only 模块少件、admin 这类"永不发布"模块混进来，
  都要到打包那步才现形）⇒ 改了 flatten / excludeArtifacts / 新加文件夹时先 --bundle 再真发。

  脚本会：逐文件夹回读 repo1，同版本已上线的直接跳过（Central 不可覆盖，重发只会 400）；
  若根 pom 当版还没上线而你要发子文件夹，自动把根前置；fleet 同理对 integration/parent 前置。
  日志落 /tmp/z-boot-deploy-<folder>.log。

【抬一格兄弟仓版本（日常）】

  python3 _doc/003_script/gen_fleet_bom.py            # 只看账：每个坐标 repo1 是 OK / PENDING / MISSING
  python3 _doc/003_script/gen_fleet_bom.py --write    # 重算 z-boot-fleet/pom.xml
  bash _doc/003_script/deploy_maven_center.sh publish --dry fleet && bash _doc/003_script/deploy_maven_center.sh publish fleet

【判据】

  ✓ 动手发之前先静态点伤，一条命令扫 ../ 下所有带 central profile 的仓：
      python3 _doc/003_script/central_pom_scan.py        # B/C/D/E 四类，退出码非 0 就有缺陷
    它按 Maven 自己的口径解析 reactor（注释掉的 module 不误报），z-boot 的"根无 <modules>、
    按文件夹独立成工程"也认。实测口径：25 仓 / 0 缺陷，z-boot 28 个 pom 全覆盖。
  ✗ BUILD SUCCESS ≠ 已可见。repo1 有 5~50 分钟无 SLA 的索引期，判发布只认 repo1 回读。
  ✗ 上传成功 ≠ 收下。"Uploaded bundle successfully … Deployment will publish automatically"
    之后 Central 还会异步校验整批组件，任何一个 pom 不合格就整批 FAILED，而 mvn 侧已经
    BUILD SUCCESS 收工了 —— 404 挂了很久时先查校验结果，别当成索引慢：
      curl -u "$CENTRAL_USERNAME:$CENTRAL_TOKEN" \
        'https://central.sonatype.com/api/v1/publisher/deployments?page=1&size=5'
    逐件看 deploymentState / deploymentComponents[].errors（实测 1.0.2 那批就是这么定位到
    z-ctc-admin 的 "Project name is missing"）。注意这份清单有一小时量级的滞后，
    刚发的那几条不在里面；/publisher/status?key= 现在一律返 500，别指望它。
  ✗ maven.deploy.skip 拦不住 Central。central-publishing-maven-plugin 不认这个属性，
    admin/bootstrap 类"永不发布"模块照样进 bundle（还捎带 exec fat jar）。要挡就用它自己的
    excludeArtifacts（按 artifactId 精确匹配），并且先拿不可达的 centralBaseUrl 演练一次，
    unzip -l target/central-publishing/central-bundle.zip 看命中数是否为 0 —— 这是唯一
    不打真实上传就能验排除生效的路子。
  ✗ 零源码模块（纯聚合 starter，src 下连 package-info 都没有）会让 maven-source-plugin /
    maven-javadoc-plugin 静默不产 -sources.jar / -javadoc.jar，BUILD SUCCESS 照样绿，
    bundle 里却只有 pom+jar —— 只有逐坐标数 4 件套才看得见，所以 publish --bundle 已经
    内置点件（bundle_audit），缺件直接 rc=1；拿到别人的包也能点：
      bash _doc/003_script/deploy_maven_center.sh bundle <path>/central-bundle.zip
    repo1 上 1.0.17/1.0.18 的 z-boot-agent-starter 就是这个形状（被收下了），
    但别把"这次被收下"当"规则允许"。
  ✗ 探活不能用 HEAD —— repo1/Fastly 对 HEAD 不给 200，用 curl -r 0-0（200/206 才算活着）。
  ✗ 上传返 500/errorCode 10500 别急着怀疑自己的包。差分实测：错凭证 → 401 "Invalid token"，
    空 body → 同一个 500。也就是说 10500 出现在鉴权之后、与负载无关，是 Sonatype 侧故障；
    这种时候把 bundle 造好放着一件一件重试就行，别去改 pom 或重签名。
    （deployments 清单的顶层键是 deployments，不是 results。）
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
    bundle)
        [[ -f "${1:-}" ]] || die "用法：bash _doc/003_script/deploy_maven_center.sh bundle <central-bundle.zip>"
        bundle_audit "$1" ;;
    gpg-init)  cmd_gpg_init ;;
    readme)    cmd_readme ;;
    help|-h|--help) print_help ;;
    *) die "未知子命令：$SUBCMD（用 help 看用法）" ;;
esac