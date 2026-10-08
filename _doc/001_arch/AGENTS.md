# AGENTS.md — z-boot 仓 AI 协作入口

## 是什么（2026-10-08 火车制拓扑）

z-opc-foundation 的 Spring Boot Starter 仓。**唯一慢层权威 = `z-boot-parent`，唯一快层动线 = `gen_train_bom.py`**：

- `z-boot-parent` — 唯一消费入口。内部三段（全部脚本管，别手改）：
  第三方地板 155 条（自原 `z-boot-dependencies` 逐字搬运，那个文件夹已退役删除）+
  接入面 pin 76 条（被跨仓真实声明的 z-* 坐标 + 19 个 starter 的 client，机械口径现算）+
  自家 22 格 starter（`${z-boot.version}`，与 parent 自己的 `<version>` 同火车同号）。
  另带 Java 8 `pluginManagement`（compiler `-parameters` / surefire 2.22.2 / boot 2.7.18）。
- `z-boot-*-starter`（3 基础 + 19 集成）— 产品层：DM 只 import parent-as-BOM 一条；
  集成 starter 的 client 依赖写字面版本（值 = FAMILIES 表，脚本写入，发布件经 flatten 内联）。
- `z-boot-fleet` / `z-boot-dependencies` **已删除**（Central 上旧件永久在架，迁移中的消费方不受影响）。
- 根 pom `z-boot:1.0.19` 照旧只是发布用 parent（central profile / flatten），无 `<modules>`。

**消费者世界 = 一行 `<parent>` + 若干条无版本依赖。** 两个版本旋钮并成一个（火车号）；
提前尝鲜某个 client 新版：本仓 dependencyManagement 写直接条目覆盖，等下一班火车再回归。

## 快速开始

```bash
# 根没有 <modules>，全量构建 = 按依赖顺序逐文件夹
for d in z-boot-parent z-boot-starter z-boot-integration-starters; do
  mvn -B -f "$d/pom.xml" clean install -DskipTests
done

mvn -B -f z-boot-integration-starters/pom.xml package -DskipTests   # 只验 19 个集成 starter
```

⚠ `install` 会把本机 `~/.m2` 刷成未发布版本，后续构建就分叉于 repo1 的已发布件——
判"对外可见"只认 repo1 回读，别拿本机 install 的结果当账。
starter 的 DM import z-boot-parent:<火车号>，所以**本地构建 starter 前必须先 install parent**。

## 改版本（只有一条动线：跑生成器）

```bash
python3 _doc/003_script/gen_train_bom.py          # 只算不发：守卫 G1-G5 + 接入面现算
python3 _doc/003_script/gen_train_bom.py --write  # 落盘（repo1 逐格探活，取不到即拒绝）
bash _doc/003_script/deploy_maven_center.sh publish   # 整列火车：root(跳过)→parent→starter→integration
```

- **FAMILIES 表**（`gen_train_bom.py` 顶部）是唯一真源：改一格版本 = 改表 → `--write` → 发整列火车。
  守卫：G2 逐格 repo1 探活（防烧格子）、G5 starter 火车号 == parent 版本号。
- **接入面**自动现算：坐标被非所属仓的真实 `<dependencies>` 声明过 ⇒ 进 parent 的 pin。
  新出现跨仓声明而 FAMILIES 没这族 ⇒ 脚本报警，登记族名再 `--write`。
- **generator 从 `git HEAD` 读模板输入**（pristine()），可从任何工作树状态重放，产物逐字节幂等。
- 抬第三方（druid/jackson…）→ 也在 parent 的地板段（脚本搬运自 floor），改 floor 历史已不存在。

## 不要做的事

- **不要手改 `z-boot-parent/pom.xml` 的三段脚本管辖区**（地板段 / 接入面 pin / `BEGIN z-boot-self` 段）——
  下次 `--write` 会被 HEAD 输入重算覆盖。
- **不要手改 starter 的 client 字面版本**——同上，`gen_train_bom.py --write` 管。
- **不要复活 `z-boot-fleet` / `z-boot-dependencies` 文件夹**——它们的职能已各有新家（见上）。
- **不要让 starter 的版本脱离火车**（一 starter 一号是上一版提案，被 CEO 裁定否掉，现行为整列同号）。
- **不要把 server/部署件的版本牵进这条链**——部署版本是部署侧（z-opc 等）自己的字面号。
- 不要直接依赖 `com.zifang:*` 幻影坐标——z-boot 必须自给自足。

## 发布

```bash
./_doc/003_script/deploy_maven_center.sh publish --dry parent     # 只 verify（编译+sources+javadoc+gpg，不打包不上传）
./_doc/003_script/deploy_maven_center.sh publish --bundle integration  # 打包照打，上传掐死：看 bundle 真实内容
./_doc/003_script/deploy_maven_center.sh publish parent           # 只发消费入口
./_doc/003_script/deploy_maven_center.sh publish                  # 整列火车 root→parent→starter→integration
```

短名 `root`/`.` 是根 pom，`parent` 是 **z-boot-parent 文件夹**。`deps` / `fleet` 两个短名已随文件夹退役。

凭证在仓根 `.env`，密钥环在仓根 `.gnupg`（两者都被 `.gitignore` 排除）。
已发布版本 Central 不允许覆盖，脚本对每个文件夹先回读 repo1，同版本已上线就跳过。
`BUILD SUCCESS` ≠ 已可见：判发布只认 repo1 回读，且探活要用 ranged GET（repo1 对 HEAD 不给 200）。
`上传成功` 也 ≠ 收下：Central 会异步校验整批，一个 pom 不合格整批 FAILED 而 mvn 侧看不出来——
用 `curl -u "$CENTRAL_USERNAME:$CENTRAL_TOKEN" 'https://central.sonatype.com/api/v1/publisher/deployments?page=1&size=5'`
读 `deploymentComponents[].errors`（清单有一小时量级滞后）。
详细口径见仓根 `README.md` 的「发布」一节与「2026-10-08 火车制重构」一节。
