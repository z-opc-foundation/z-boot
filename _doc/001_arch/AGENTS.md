# AGENTS.md — z-boot 仓 AI 协作入口

## 是什么

z-opc-foundation 的 Spring Boot Starter 仓。版本权威分两层（1.0.19 起）：

- `z-boot-dependencies` — **第三方**版本地板（156 条受管项，`io.github.yuku123` 坐标 0 条）
- `z-boot-fleet` — **兄弟仓 `z-*`** 版本格（163 条受管项，由脚本生成，勿手改）

这两层的**消费入口**是第三个文件夹：

- `z-boot-parent` — 各仓统一 `<parent>`：继承地板 + import fleet + 钉 z-boot 自家 23 个 starter
  （`${z-boot.version}`，与本 pom 同一次发行）+ 下发 Java 8 的 `pluginManagement`。使用方一行
  `<parent>` 就够了，不必再各自起版本属性名（历史上是 `z-util.version` / `util.version` /
  `zutil.version` 三套名字混用）。

1.0.19 起根 pom 只是发布用 parent，**没有 `<modules>`**：五个文件夹各自是独立 Maven 工程，
`<parent>` 与自身 `<version>` 都写字面量（不再有 `${revision}`），所以能只发一个文件夹。

## 快速开始

```bash
# 根没有 <modules>，全量构建 = 按依赖顺序逐文件夹
for d in . z-boot-dependencies z-boot-fleet z-boot-parent z-boot-starter z-boot-integration-starters; do
  mvn -B -f "$d/pom.xml" clean install -DskipTests
done

mvn -B -f z-boot-integration-starters/pom.xml package -DskipTests   # 只验 20 个集成 starter
```

⚠ `install` 会把本机 `~/.m2` 刷成未发布版本，后续构建就分叉于 repo1 的已发布件——
判"对外可见"只认 repo1 回读，别拿本机 install 的结果当账。

## 新增 starter

1. 决定归类: 基础 (`z-boot-starter/`) / 集成 (`z-boot-integration-starters/`)
2. 在对应聚合模块下新建子目录，并在那个子目录的 pom 里加 `<module>`
3. 子 pom 的 `<parent>` 指向**聚合模块**（字面版本），自己那份 `<version>` 也写字面量；
   `<dependencyManagement>` 里**并列 import** `z-boot-dependencies` + `z-boot-fleet`（都写字面版本）
4. 依赖 L3 坐标不写 version，由 fleet 下发；写 `AutoConfiguration.java` + `META-INF/spring.factories`
5. z-opc 主后端集成验证，再按文件夹发布

## 抬版本

- 第三方 → 改 `z-boot-dependencies/pom.xml`，发 `publish deps`（引它的 starter 要跟着重发）
- z-boot 自家 starter → 版本键在 `z-boot-parent` 的 `<z-boot.version>`，与 parent 自己的
  `<version>` 必须同格。别手抄清单：`gen_fleet_bom.py --parent` 看账、`--write-parent` 落笔
  （清单取两个聚合 pom 的 `<modules>`，逐件核 repo1，有 PENDING 就拒绝落盘）。
  ⚠ `${project.version}` 在这里**不能用** —— flatten 的 `resolveCiFriendliesOnly` 只解
  `${revision}` 那一组，剩下的 `${project.version}` 原样发出去，消费方按它自己的版本解析（实测 404）。
- 兄弟仓 `z-*` → **不手改 pom**：改 `_doc/003_script/gen_fleet_bom.py` 的 `FAMILIES` 表 →
  `--write` 重算 → `publish fleet`。脚本只收 repo1 实测存在的版本，所以 fleet 允许滞后于兄弟仓 HEAD；
  有格还是 PENDING（本地装过、repo1 取不到）时 `--write` 直接 exit 2 拒绝落盘 —— 钉一个不存在的版本
  等于烧格子，Central 不许覆盖，只能抬版本号重发收拾。
- fleet **自己**那一格也要一起管：`gen_fleet_bom.py` 顶部的 `FLEET_VERSION` 与 `z-boot-parent`
  的 `<z-boot-fleet.version>` 必须同值，`--write` 两边不一致或那一格已被 repo1 占用就直接拒绝。

## 不要做的事

- **不要手改 `z-boot-fleet/pom.xml`**——它是脚本产物，手改下次重算就没了，而且没人能验证那格版本真的存在
- **不要在 z-boot 里加 z-msg/z-ctc/z-log 等业务模块**——那些业务 starter 跟着业务仓走
- **不要在根 pom 加第三方 `<dependencyManagement>`**——第三方由 `z-boot-dependencies` 锁，兄弟仓由 `z-boot-fleet` 锁
- **不要直接依赖 `com.zifang:z-opc` parent**——z-boot 必须自给自足
- 别把 flatten 的 `flattenMode` 在 fleet 上改成 `oss`：`oss` 会删掉整个 `<dependencyManagement>`，
  发出去的 fleet 就成了空 BOM（本机永远看不出来，只有外部 import 会炸）

## 发布

```bash
./_doc/003_script/deploy_maven_center.sh publish --dry fleet     # 只 verify（编译+sources+javadoc+gpg，不打包不上传）
./_doc/003_script/deploy_maven_center.sh publish --bundle fleet  # 打包照打，上传掐死：看 bundle 真实内容
./_doc/003_script/deploy_maven_center.sh publish fleet           # 只发一个文件夹
./_doc/003_script/deploy_maven_center.sh publish                 # 按 root→deps→fleet→parent→starter→integration 全发
```

短名 `root`/`.` 是根 pom，`parent` 是 **z-boot-parent 文件夹**（1.0.19 之前 `parent` 指根 pom，
现在让给了真叫这个名字的文件夹）。发 `integration` 或 `parent` 时脚本会自动前置 `fleet` —— 那两批
的 `<dependencyManagement>` 按字面 import `z-boot-fleet:1.0.0`，fleet 不在 repo1 上就是
`Non-resolvable import POM`，而这在台装上看不出来（`~/.m2` 里躺着装过的 fleet）。

凭证在仓根 `.env`，密钥环在仓根 `.gnupg`（两者都被 `.gitignore` 排除）。
已发布版本 Central 不允许覆盖，脚本对每个文件夹先回读 repo1，同版本已上线就跳过。
`BUILD SUCCESS` ≠ 已可见：判发布只认 repo1 回读，且探活要用 ranged GET（repo1 对 HEAD 不给 200）。
`上传成功` 也 ≠ 收下：Central 会异步校验整批，一个 pom 不合格整批 FAILED 而 mvn 侧看不出来 ——
用 `curl -u "$CENTRAL_USERNAME:$CENTRAL_TOKEN" 'https://central.sonatype.com/api/v1/publisher/deployments?page=1&size=5'`
读 `deploymentComponents[].errors`（清单有一小时量级滞后）。
`maven.deploy.skip` 挡不住这个插件，"永不发布"的模块要用 `excludeArtifacts` 排，改完用 `--bundle` 验。
详细口径见仓根 `README.md` 的「发布」一节。
