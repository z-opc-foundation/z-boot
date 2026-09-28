# z-boot

> **Spring Boot Starter 聚合仓 + 第三方依赖版本权威 (BOM)**
> 把所有 z-* L3 中间件 + 通用 starter 收成"开箱即用"系列, 业务模块一行 import 一个能力

[![Maven Central](https://img.shields.io/badge/Maven%20Central-1.0.19-blue?logo=apache-maven)](https://central.sonatype.com/search?q=g:io.github.yuku123+a:z-boot*)
[![License](https://img.shields.io/license/MIT-green)](LICENSE)
[![Java](https://img.shields.io/badge/Java-8%2B-orange)](https://openjdk.org)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-2.7.x-6DB33F)](https://spring.io)

---

## 🚀 5 分钟接入

### 方式零：把 z-boot-parent 当 `<parent>`（1.0.19 起推荐，各仓统一这么做）

```xml
<parent>
    <groupId>io.github.yuku123</groupId>
    <artifactId>z-boot-parent</artifactId>
    <version>1.0.19</version>
</parent>

<groupId>com.example</groupId>
<artifactId>my-module</artifactId>
<version>1.0.0</version>
```

**这一行就是全部**。它继承了 `z-boot-dependencies`（156 条第三方地板）、import 了 `z-boot-fleet`
（163 条兄弟仓 `z-*`），再加上自己 `<dependencyManagement>` 里的 24 条 `z-boot-*` 自家 starter，
还顺带下发 Java 8 的 `pluginManagement`（compiler `-parameters` / surefire / jar / resources /
spring-boot 插件版本）。于是依赖一律不写 `<version>`：

```xml
<dependencies>
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-util-core</artifactId>          <!-- fleet 下发 → 1.0.13 -->
    </dependency>
    <dependency>
        <groupId>org.apache.commons</groupId>
        <artifactId>commons-lang3</artifactId>        <!-- 地板下发 → 3.18.0 -->
    </dependency>
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-web-starter</artifactId>    <!-- 只有 parent 这条路能拿到版本 -->
    </dependency>
</dependencies>
```

> 判据是**干净机器实测**，不是本机 `~/.m2`：用一个全新的 localRepository、只指 repo1，
> 上面这份 pom 能解析出 `z-util-core 1.0.13 / z-cache-client 1.3.5 / commons-lang3 3.18.0 /
> netty 4.1.138.Final / z-boot-web-starter 1.0.19`，产物 class-file **major 52**。

> ⚠ 自家 starter 的版本键必须是**字面 property** `<z-boot.version>`，不能照 c2f 那样写
> `${project.version}`：`flatten` 在这里是 `resolveCiFriendliesOnly`，它只解 `${revision}` 那一组，
> `${project.version}` 会原样发出去，由**消费方**自己的模型来插值 —— 实测把消费方版本（`9.9.9-PROBE`）
> 填进 `z-boot-web-starter`，repo1 404。

### 方式一：只 import BOM（不给 `<parent>`，比如它已经有别的 parent）

```xml
<!-- 1. 引入 z-boot-dependencies BOM —— 它只锁第三方版本 -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>io.github.yuku123</groupId>
            <artifactId>z-boot-dependencies</artifactId>
            <version>1.0.17</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
        <!-- 1.0.19 起再加这一条：兄弟仓 z-*（z-cache/z-mq/z-llm/…）的版本格在 z-boot-fleet 里，
             不在地板 BOM 里。想直接写 `io.github.yuku123:z-cache-spring-boot-starter` 而不经
             z-boot-*-starter 的消费者，没有这条就一条版本约束都拿不到。 -->
        <dependency>
            <groupId>io.github.yuku123</groupId>
            <artifactId>z-boot-fleet</artifactId>
            <version>1.0.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<!-- 2. 引入 starter —— 走这条"纯 import"的路时 version 必须自己写：两份 BOM 都不管 z-boot-* 坐标。
     不写版本的唯一路子是方式零（把 z-boot-parent 当 <parent>），版本在那 24 条里。 -->
<dependencies>
    <!-- 基础能力 -->
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-web-starter</artifactId>
        <version>1.0.17</version>
    </dependency>
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-datasource-starter</artifactId>
        <version>1.0.17</version>
    </dependency>

    <!-- L3 中间件 (一行 import 一个) -->
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-cache-starter</artifactId>
        <version>1.0.17</version>
    </dependency>
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-mq-starter</artifactId>
        <version>1.0.17</version>
    </dependency>
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-rpc-starter</artifactId>
        <version>1.0.17</version>
    </dependency>
</dependencies>
```

> ⚠ **"starter 不写 version、由 BOM 锁"这条在纯 import 的路上是错的，实测证伪**（2026-09-26 在 **1.0.15** 发布件上复测）：
> 拿一个只 import `z-boot-dependencies:1.0.15` 的干净 pom 声明无版本的 `z-boot-web-starter`，
> Maven 直接拒绝读项目 ——
> `'dependencies.dependency.version' for io.github.yuku123:z-boot-web-starter:jar is missing`；
> 同一份 pom 补上 `<version>1.0.15</version>` 才 `BUILD SUCCESS`（树里读到 `z-boot-web-starter:jar:1.0.15:compile`）。
> 原因见下面「第三方版本权威（BOM）」：这份 BOM 里 `z-boot-*` 坐标 **0 条**——1.0.16 复测仍是 0 条
> （逐条解析 repo1 的 `z-boot-dependencies-1.0.16.pom`：132 条受管项里 `z-boot-*` 0 条、
> `io.github.yuku123` 只有 3 条且全在 BOM 里，那条"import BOM 就不用写 version"的路**从来没通过**）。
> 现网消费者（如 `z-opc/pom.xml:455-458`）也正是自己钉 `<version>` 的。
> **1.0.19 起这句话要收窄**：`z-boot-dependencies`（第三方 156 条，`io.github.yuku123` **0 条**）和
> `z-boot-fleet`（兄弟仓 163 条，`z-boot-*` **0 条**）加在一起仍然锁不到 z-boot 自家 starter ——
> 那 24 条只在 **`z-boot-parent`** 的 `<dependencyManagement>` 里（实测：floor dm 156 条 / yuku 0，
> fleet dm 163 条 / yuku 163，parent dm 24 条 / yuku 24，三处都无一条缺 `<version>`）。
> 所以"零 version"要靠 parent，不靠 BOM；1.0.19 之前的仓全是自己钉 version 的，迁移见下面「消费模型」。

`application.yml`:

```yaml
z:
  cache:
    enabled: true        # z-cache 的闸：无 matchIfMissing ⇒ 不写这行就不装配
    host: localhost
    port: 6379           # = ZCacheProperties 里 port 的默认值（示例写默认值，别照抄某个环境的端口）
  rpc:
    enabled: true        # z-rpc 是 matchIfMissing=true（默认开），这行写不写都开
    port: 20880          # = z-rpc 里 port 的实测默认值
```

```java
@SpringBootApplication
public class App { public static void main(String[] args) { SpringApplication.run(App.class, args); } }
```

启动后 `z.cache.*` 和 `z.rpc.*` 会自动装配（按 `enabled=true` 触发）。

### 方式二：外部开发者（直接用单个 starter）

```xml
<dependency>
    <groupId>io.github.yuku123</groupId>
    <artifactId>z-boot-cache-starter</artifactId>
    <version>1.0.17</version>
</dependency>
```

---

## 📦 已发布到 Maven Central 的所有模块

> groupId: `io.github.yuku123` · 最新 release: **1.0.19**（2026-09-28）· **29 个坐标**
> （28 个走 `1.0.19`，`z-boot-fleet` 单独一格 `1.0.0`——它是脚本产物、版本节奏与 z-boot 发行无关，
> 抬兄弟仓那一格只需重发这一个文件夹）
>
> **1.0.19 这一轮做了两件事**：
> 1. **补发**：1.0.19 原本是**半发状态**——20 个集成 starter 停在 1.0.18，因为它们的 pom 里
>    `import z-boot-fleet:1.0.0` 是按字面版本写死的，而 fleet 1.0.0 从来没上过 Central。
>    本机看不出来（`~/.m2` 里有本地 install），干净机器上直接 `Non-resolvable import POM`。
>    发布顺序因此固定为 root→deps→**fleet**→**parent**→starter→integration。
> 2. **新增消费入口 `z-boot-parent`**（上面「方式零」）。
>
> 判据（2026-09-28 23:17 现跑，日志 `/tmp/zbp-live-test.log`；尺已进仓
> `_doc/003_script/repo1_census.py`，现跑 `python3 _doc/003_script/repo1_census.py`）：
> 坐标清单**机械取自磁盘 pom**（根 + 4 个独立工程 + 两个聚合器及其 active `<module>`，注释掉的
> `z-tool-webide-spring-boot-starter` 不算），逐件对 repo1 发 ranged GET ⇒
> **98 件（29 pom + 23 主 jar + 23 sources + 23 javadoc）全部 200/206，对应 `.asc` 98 件同样全数在**；
> 对比 1.0.17 那轮的 84 件 —— 多出的正是 6 个零源文件 starter 的 sources/javadoc，`--bundle` 的
> `bundle_audit` 按坐标点四件齐之后才补齐的。
> 另跑一次**干净消费者**验证：全新 localRepository、单一仓库源（日志里 534 次 Downloading 全部来自
> `repo1-direct`，零本机件），pom 里只写 `<parent>io.github.yuku123:z-boot-parent:1.0.19</parent>`
> 加三条**不带 version** 的依赖 ⇒ `BUILD SUCCESS`（13:16 min），读到 `z-util-core 1.0.13`、
> `z-cache-client 1.3.5`、`z-boot-web-starter 1.0.19`、`z-boot-cache-starter 1.0.19`、
> `commons-lang3 3.18.0`、`netty 4.1.138.Final`，产物 `demo.Hello` 的 class-file **major 52**
> （Java 8 口径是从 repo1 那份 parent 的 `pluginManagement` 下发的）。
> repo1 上那份 parent pom 实测还带着 `<build><pluginManagement>` 6 个插件和 14 条 `<properties>`
> （`z-boot.version=1.0.19` / `z-boot-fleet.version=1.0.0` 都在），所以 DM 里那些 `${...}` 由
> parent 自己的 properties 落地 —— 这就是"flatten 在这里不能用 `oss`"那两条字面量的实证。
>
> 下面这段是**上一轮 1.0.17 的普查记录（历史读数，原样保留）**：
> 共 **27 个坐标**（`Finished at: 2026-09-27T15:00:56+08:00`，
> 见 `~/.cache/zboot-1017/deploy-1017.log`，deploymentId `5c4474f5-9862-4ded-aa98-0c200a4367e5`）。
> **1.0.17 的发版目的**：把仓内已经抬过、对外还欠着的 L3 pin 一次兑现。尺（`~/.cache/zboot-1016/pin-fork-check.py`
> 的分类器，驱动 `~/.cache/zboot-1017/fork_for_version.py`）逐版本量出来是
> **1.0.15 分叉 8 格 → 1.0.16 分叉 7 格 → 1.0.17 分叉 0 格**（`fork-by-version.receipt`；
> 这轮新关的两格是 `z-boot-llm-starter` 0.1.4→**0.1.5**、`z-boot-skill-starter` 0.1.2→**0.2.0**）。
> 发布判据 = `~/.cache/zboot-1017/repo1-verify.sh` 15:24:17–15:28:54 那一次运行（读数
> `repo1-1017.receipt`，末行 `FAILS=0`）：分母机械取自本次 staging（27 pom + 23 主 jar + 17 sources
> + 17 javadoc = **84 件**，`.asc` 同为 84），要求每件 repo1 200 **且 md5 与上传字节逐字节同**
> ⇒ **84/84**；`.asc` **84/84 验签通过**（不抽样）；再钉住发版目的那一格：
> `z-boot-llm-starter-1.0.17.pom` 里 `z-llm-starter` = **0.1.5**、父 pom 的 `<z-llm.version>` = **0.1.5**。
> ⚠ 这支尺的牙是**注入量出来的**：拿 staging 的一份真拷贝、把 `z-boot-llm-starter-1.0.17.pom`
> 换成 1.0.16 的字节重跑，A 当场点名该件 `repo1=cee15bfa… 本地=d374437b…` 并报 `83 ≠ 84`、
> C 也拒把它当被签件（`FAILS=4`，日志 `ctrl-inject.log`）——"84/84 相同"不是空跑出来的。
> 同步期实测：上传完 15:00:56 → 首个坐标 200 是 **15:08:26**（轮询 `wait-1017.log`，约 7.5 分钟），
> 而 84 件全 200 要到 15:15 之后那次普查才成立 ⇒ 轮询要落盘，别只看第一支 200。
>
> 下面这段是**上一轮 1.0.16 的普查记录（历史读数，原样保留）**：
> 全量普查（`~/.cache/zboot-1016/census2.py`，日志 `census2-1016.log` 22:28:12 收尾）：分母不是手敲的清单，
> 是本机 `target/central-staging/io/github/yuku123` 里那 **84 个**
> `.pom`/`.jar` 文件（27 pom + 23 主 jar + 17 sources + 17 javadoc，日志里按这四类各出一行分母），
> 逐个从 repo1 下回来比 md5 ⇒
> **84/84 字节相同、0 不一致、0 非 200**；`.asc` 也是 84 个（27 pom.asc + 57 jar.asc），即每个 pom/jar 都带签名。
> ⚠ 第一版普查是 bash 写的，它打印出 `jar: 58/57`（计数串味）——**这种"分母自己都不自洽"的读数不能当账**，
> 所以换成按类分组、每类各报一条的 python 尺，并按类核到 27/23/17/17。
> 阳性对照：拿 repo1 的 **1.0.15** 父 pom 去比本机 1.0.16 的 staging 字节，尺当场判"不同"
> （`8de3f182…` vs `eec689f2…`），所以那 84 个"相同"不是空跑。
> ⚠ "上传完"到"repo1 全 200"之间有一段没有 SLA 的同步期：1.0.16 实测 ~6 分钟（21:37:57 首次 27/27 = 200，
> 那次轮询只留在终端、没落盘）、1.0.15 是 13 分钟、1.0.14 是 51 分钟 ⇒ **别拿 `BUILD SUCCESS` 当"已可见"，
> 也别拿任何一次的分钟数当承诺**，判发布只认 repo1 回读。
> 计数 = 全仓 26 条 active `<module>`（根 3 + `z-boot-starter` 3 + `z-boot-integration-starters` 20）
> + 顶层 `z-boot` 自身，其中 `z-boot` / `z-boot-starter` / `z-boot-integration-starters`
> / `z-boot-dependencies` 4 个是 pom-only，所以 jar 数 = 27 − 4 = 23；sources / javadoc 各只有 17 份，
> 少的 6 份正是「核心能力」那节点名的 6 个零源文件 starter（llm/mcp/skill/agent/bot/agent-proxy））

### 基础 starter (3 个)

| 模块 | 说明 |
|---|---|
| `z-boot-base` | Log4j2 门面 + ApplicationModuleDescription 接口 |
| `z-boot-web-starter` | Spring Web + Log4j2 + Knife4j OpenAPI 3 自动装配 |
| `z-boot-datasource-starter` | Druid + MyBatis-Plus + mysql + 多数据源 |

### 唯一不聚合 L3 的集成 starter (1 个)

| 模块 | 说明 |
|---|---|
| `z-boot-jackson-starter` | Jackson 全局配置 (Long → String 防精度丢失)；pom 里没有一条 `io.github.yuku123` 依赖，实测是 20 个集成模块里唯一的例外。它是 z-boot 里**唯一无开关的自动装配**：`META-INF/spring.factories` 注册 `com.zifang.boot.jackson.config.GlobalJacksonConfig`，没有 `@ConditionalOnProperty`，即 import 就生效（旧表里那行 `z.jackson.enabled=true` 在任何代码里都不存在） |

### z-boot-* 聚合 starter（19 个，一行 import 一个 L3）

> **版本列不是手抄的**：1.0.18 及以前的真源是 `z-boot/pom.xml` 的 `<z-*.version>` property（经
> `z-boot-integration-starters/pom.xml` 的 `<dependencyManagement>` 下发给每个 `z-boot-*-starter`）；
> **1.0.19 起真源是 `z-boot-fleet/pom.xml`**，而它是 `_doc/003_script/gen_fleet_bom.py` 从兄弟仓 pom +
> repo1 实测重算出来的，所以这张表要么按脚本回读、要么按发布件 pom 回读，**不能手填**
>（2026-09-27 那一轮就是靠尺抓出两格没跟上：`z-boot-llm-starter` 表里还写 0.1.4、
> `z-boot-skill-starter` 还写 0.1.2，而 property 早已是 0.1.5 / 0.2.0）。
>
> ✅ **"仓内 property"和"repo1 上已发布件里的 pin"是两个事实**，这条分叉在 **1.0.17 已归零**：
> `~/.cache/zboot-1016/pin-fork-check.py` 对 repo1 的 1.0.17 发布件逐行读回，19 行里
> **T 文档漂 0 / F 分叉 0 / 取不到 0**（读数 `~/.cache/zboot-1017/fork-by-version.receipt`，15:2x）。
> 分叉名单（0）：
> 上面那行不是说明文字，是尺的**输入**：它按"模块名 → `${z-<模块>.version}`"机械推 property、
> 逐行去 repo1 拉**当前 revision** 的发布件对账，要求**实测分叉集正好等于声明名单**——
> 多一格（新分叉没声明）或少一格（分叉被发布收掉了却没撤声明）都判红。
> ⚠ **声明行会烂掉，而且烂得很安静**：1.0.16 那阵子它写的是 5 格，而尺今天同一套分类器
> 对准 1.0.16 的发布件量出来是 **7 格**（1.0.15 是 8 格）——多出的两格是 09-26 之后抬的
> `z-llm` 0.1.4→0.1.5、`z-skill` 0.1.2→0.2.0，抬 property 的人没回读声明行，于是"仓内改了、
> 对外没兑现"这件事只在尺的 F 判红里现形。⇒ **抬任何一格 `<z-*.version>` 之后必须跑这支尺**，
> 别指望表格里那行快照自己更新。
> 它自己也有两支阳性对照（同一次运行内）：表里塞一个 `9.9.9` 必须判 T 红；
> 换 1.0.15 的发布件跑同一套必须报出非空分叉（实测 8 格）——证明分类器不是瞎的。
>
> **"哪 5 格落后"也不是手点的**：`~/.cache/zboot-1016/latest-census.py` 把上面 19 行的每个 L3 坐标
> 都拉一次 repo1 `maven-metadata.xml`，拿 property 值和 `<latest>`**以及** `<versions>` 里的最大值各比
> 一遍（Central 的 `<latest>` 语义是"最后部署"而不是"版本号最大"，两个都算才不被它骗）。
> 2026-09-26 23:15 实测：19 个坐标里 **5 格 LAG**（z-config 1.0.7→1.0.8、z-cache 1.3.1→1.3.5、
> z-mq 1.2.0→1.2.1、z-gw 1.0.1→1.0.3、z-vector 1.0.1→1.0.3）、0 格 AHEAD、`<latest>` 与最大值 0 处分歧；
> 抬后复跑 `LAG 0`。那把尺同样自带一支对照（把 z-cache 退回 1.3.1 必须重新出现在 LAG 名单里——
> 否则"落后 0 条"和"尺看不见落后"是同一个输出）。原始读数留档
> `~/.cache/zboot-1016/latest-census.receipt`（含 metacache 逐文件 mtime，23:15:07–23:15:32 抓完）。
> ⚠ **2026-09-27 15:2x 复跑时这把尺自己露了馅**：它取 `maven-metadata.xml` 是
> `if not 缓存文件存在: 才 curl`，于是 09-26 23:15 的快照被当成"repo1 最新"一直复用——
> 当场报 `z-llm-starter <latest>=0.1.4`（真值已是 0.1.5，artifact 早就能 200 下载）、
> `z-skill-starter <latest>=0.1.2`（真值 0.2.0），把两格正确的 property 判成 **AHEAD**。
> 这是"缓存把没量伪装成量过"，朝**看不见**的方向坏。修成每次真拉、并把每份 metadata 的
> `<lastUpdated>` 打进读数当归因；修后实测 **LAG 0 / AHEAD 0 / `<latest>`≠max 0**、
> CTRL（把 z-cache 退回 1.3.1）仍如期报出 1 格 LAG，留档 `~/.cache/zboot-1016/latest-census-1017.receipt`
> （陈旧现场归档在 `~/.cache/zboot-1016/metacache-stale-0926/`，19 份文件 mtime 全在 09-26 23:15）。
> ⚠ 只有 `maven-metadata.xml` 这类**可变**文档要禁缓存；发布件 pom/jar 在 Central 上不可变，
> `pin-fork-check.py` 那种"下过就不重下"是对的，别顺手把两边一起改。
>
> "聚合的 L3 坐标"列也是从每个 starter 的 pom 机械抽出来的（去掉 dependencyManagement 后取
> `io.github.yuku123` 直接依赖），不是照旧表抄的——所以 20 个 `<module>` 里除 `z-boot-jackson-starter`
> 全在这 19 行，最早的旧表只列了 10 行。
>
> ⚠ **旧表有两列不可信，已按实测改写**（2026-09-26）：
> - **「默认端口」列删掉了**：各 L3 的 `Z*Properties` 里 `port` 默认值实测是 cache **6379** /
>   vector **6334** / graph **8090** / rpc **20880**，旧表写的 16379 / 8182 / 9888 / 9000 / 9876 / 18086
>   在任何 `Properties` 里都找不到出处；z-boot 这层也不设端口，列留着只会制造第二个"看起来对"的数字。
> - **「启用开关」列原来全表统一写 `z.{pkg}.enabled=true`，实测 19 行里没有一行完全符合**：命名有三种
>   （`z.cache` / `zmq` / `z-msg`）、默认态两种（`matchIfMissing=true` 是**默认开**，不是旧文档说的"默认 false"）、
>   还有 4 行的开关压根不叫 `enabled`（oss 看 `oss.provider`、schedule 看 `z.base.db.schedule.disabled`、
>   vector 看 `zvector.server.auto-start`）或根本没有开关（ctc / bot / agent-proxy 全仓 `@ConditionalOnProperty` 0 命中）。

| 模块 | 聚合的 L3 坐标 | 版本（= property 实测值） | L3 侧启用条件（各仓 HEAD 实测 `@ConditionalOnProperty`） |
|---|---|---|---|
| `z-boot-config-starter` | z-config-spring-boot-starter | `${z-config.version}` = 1.0.8 | `z.config.enabled=true`，无 matchIfMissing ⇒ 默认关 |
| `z-boot-cache-starter` | z-cache-spring-boot-starter | `${z-cache.version}` = 1.3.5 | `z.cache.enabled=true`，默认关 |
| `z-boot-mq-starter` | z-mq-spring-boot-starter | `${z-mq.version}` = 1.2.1 | **`zmq.enabled`**（前缀无点），`matchIfMissing=true` ⇒ 默认开 |
| `z-boot-gw-starter` | z-gw-spring-boot-starter | `${z-gw.version}` = 1.0.3 | **`zgw.enabled`**，默认开 |
| `z-boot-kb-starter` | z-kb-spring-boot-starter | `${z-kb.version}` = 1.0.2 | **`zkb.enabled`**，默认开 |
| `z-boot-vector-starter` | z-vector-spring-boot-starter | `${z-vector.version}` = 1.0.3 | **`zvector.server.auto-start`**，没有 `z.vector.enabled` 这个键 |
| `z-boot-graph-starter` | z-graph-spring-boot-starter | `${z-graph.version}` = 1.0.5 | `z.graph.enabled=true`，默认关 |
| `z-boot-rpc-starter` | z-rpc-spring-boot-starter | `${z-rpc.version}` = 1.0.2 | `z.rpc.enabled`，`matchIfMissing=true` ⇒ 默认开 |
| `z-boot-oss-starter` | z-oss-common | `${z-oss.version}` = 1.0.2 | 按 **`oss.provider`** 分支（`local` 为 matchIfMissing），没有 enabled 开关 |
| `z-boot-schedule-starter` | z-schedule-spring-boot-starter | `${z-schedule.version}` = 1.0.4 | 按 **`z.base.db.schedule.disabled=false`** 反向开关，没有 `z.schedule.enabled` |
| `z-boot-msg-starter` | z-msg-web | `${z-msg.version}` = 1.2.0（仓内 property 与 **1.0.16 发布件**已一致；1.0.15 发布件仍是 1.1.0，那段历史见下方注） | **`z-msg.enabled`**（连字符不是点），默认开 |
| `z-boot-ctc-starter` | z-ctc-sso | `${z-ctc.version}` = 1.0.1 | **`z.boot.ctc.enabled=true`**（开关在 z-boot 这层，不在 L3；`ZBootCtcAutoConfiguration:27`），默认关 |
| `z-boot-llm-starter` | z-llm-starter | `${z-llm.version}` = 0.1.5 | `z.llm.enabled=true`，默认关 |
| `z-boot-mcp-starter` | z-mcp-starter | `${z-mcp.version}` = 0.1.2 | `z.mcp.enabled=true`，`matchIfMissing=false` ⇒ 默认关 |
| `z-boot-skill-starter` | z-skill-starter | `${z-skill.version}` = 0.2.0 | `z.skill.enabled=true`，默认关 |
| `z-boot-agent-starter` | z-agent-starter | `${z-agent.version}` = 0.1.2 | `z.agent.enabled=true`，默认关 |
| `z-boot-bot-starter` | z-bot-core | `${z-bot.version}` = 0.1.0 | 无开关（L3 全仓 `@ConditionalOnProperty` 0 命中） |
| `z-boot-agent-proxy-starter` | z-agent-proxy | `${z-agent-proxy.version}` = 0.1.0 | 无开关（同上） |
| `z-boot-script-starter` | z-script-web | `${z-script.version}` = 1.0.0 | 无开关（z-boot 侧 0 个 `@ConditionalOnProperty`；实体装配在 z-script-web 自己的 `spring.factories` → `ZScriptWebAutoConfiguration`）。1.0.15 才进反应堆，宿主前置：MySQL 建过 z-script 的 `_doc/002_deploy/init.sql`、数据源键写 `z.base.db.script.*`（写 `spring.datasource.*` 会静默回落 localhost/root） |

> **这一列的版本号已经在对外发布件里了，不只是仓内 property**：2026-09-26 逐个 curl repo1 上
> `z-boot-*-starter-1.0.16.pom`（flatten 已把 property 展开成字面量），**19/19** 抽出的
> `io.github.yuku123` 直接依赖与本表"聚合的 L3 坐标 + 版本"两列逐格一致、0 格不一致
> （量具：`~/.cache/zboot-1016/table-vs-published-1016.py` —— 期望值不手敲，整张表从本 README
> 机械解析，实测分母 19）。上一版这条对不上的是 `z-msg`
> （property 抬了但 1.0.14 发布件里还是 1.0.0）和 `z-llm`——两处都在 1.0.15 兑现了。
>
> ✅ 曾有一条**故意留着**的分叉已在 1.0.16 收掉，过程记在这里：2026-09-26 21:11 把根 pom 的
> `<z-msg.version>` 抬到 1.2.0 之后、1.0.15 发布之前，实测是 **18/19 一致 + 1 格已知分叉** ——
> repo1 的 `z-boot-msg-starter-1.0.15.pom` 当时仍写 `z-msg-web:1.1.0`（21:12 curl，`1.0.16` 404，
> `maven-metadata.xml` 的 `<version>` 列表停在 1.0.15）。仓内这一侧当时量过：`mvn -o -pl z-boot-integration-starters/z-boot-msg-starter -am package`
> 生成的 `.flattened-pom.xml` 里是字面量
> `1.2.0`。分叉确实只能靠发版收，改表格文字收不掉它——发完 1.0.16 后同一处回读：
> `z-boot-msg-starter-1.0.16.pom` = **`z-msg-web:1.2.0`**（21:58 curl，且它已不含 XML 注释、
> 多了一个 `<properties>` 块，见下面「BOM」一节），上面那条 19/19 就是对 1.0.16 重跑的结果。
>
> ⚠ **反向的账：19 个 pin 里有 5 个仍落后于 Central 的 `<latest>`**（同一张表、同一把尺，
> 但分母换成 repo1 的 **1.0.16 发布件**字面量后逐个读 `<artifact>/maven-metadata.xml`：
> **14 个 SAME / 5 个 LAG / 0 个读不到**，量具 `~/.cache/zboot-1016/latest-vs-published-1016.py`）：
> z-config 1.0.7→**1.0.8**、z-cache 1.3.1→**1.3.5**、z-mq 1.2.0→**1.2.1**、
> z-gw 1.0.1→**1.0.3**、z-vector 1.0.1→**1.0.3**。
> （1.0.15 那阵子这条尺量到的是 13 SAME / 6 LAG，第 6 格 `z-msg` 1.1.0→1.2.0 已随 1.0.16 发布兑现，
> 所以清单从 6 格缩到 5 格——这 5 格 1.0.16 **没有**顺带抬，抬号要按各仓回归单独判。）
> "落后"不等于"该抬"——每个 L3 的新版是否可用要按各仓的回归判，别照 `<latest>` 盲抬；
> 但这张表从此有了一个能自动跑的对账尺，抬号前拿它量一遍就行。

### BOM (2 个)

| 模块 | 说明 |
|---|---|
| `z-boot-dependencies` | **第三方**版本权威（spring-boot-dependencies 2.7.12 + jackson-databind 2.18.6 + druid 1.2.23 + log4j-core 2.25.4 + netty-bom）。1.0.19 实测 `<dependencyManagement>` **156 条**（字面 109 / property 42 / BOM import 5）、pom 1179 行。1.0.18 及以前它还夹带 3 条 `z-graph-*` 兄弟仓 pin，1.0.19 起全部搬进 fleet，这里只剩第三方 |
| `z-boot-fleet` | **兄弟仓（L3 `z-*`）**版本权威，1.0.19 新增。21 个版本格 property + **163 条**受管坐标（全部 `${z-*.version}` 形式，字面 0）、pom 911 行。**不手写**：由 `_doc/003_script/gen_fleet_bom.py` 从磁盘上的兄弟仓 pom + repo1 实测存在性重算，抬号 = 重跑脚本。允许滞后于兄弟仓 HEAD，但每一格都有出处。163（不是 164）是因为 `z-ctc-admin` 自 2026-09-28 起被 `excludeArtifacts` 永久挡在 Central 外，脚本把它连同 `z-msg-example` / `z-gw-examples` / `z-rpc-examples` 一起写进了 `SKIP_ARTIFACTS` |
| `z-boot-parent` | **消费入口**，1.0.19 新增，形状照 c2f-boot 的 `c2f-boot-parent`。`<parent>` = `z-boot-dependencies`（白拿地板）+ 自己 import `z-boot-fleet`（白拿兄弟仓）+ 24 条 `z-boot-*` 自家 starter（版本键 `${z-boot.version}`，与本 pom 同一次发行）+ Java 8 的 `<pluginManagement>`。用法见上面「方式零」：使用方一行 `<parent>`、依赖零 `<version>`。⚠ 这里的 flatten 必须是 `resolveCiFriendliesOnly`，不能沿用根 pom 的 `oss` —— `oss` 会剥掉整个 `<build>`，发出去的 parent 就只剩版本没有构建口径，而本机永远看不出来 |

> 两个 BOM 的坐标空间**不相交**（floor 只管第三方，fleet 只管 `io.github.yuku123:z-*`），所以消费者把它们
> 并列 import 不会有 dm 优先级打架。**代价**：每个 `z-boot-*-starter` 要显式 import 两次（见下面「项目结构」）。
> 为什么要拆：1.0.18 之前兄弟仓版本格住在**根 pom 的 `<properties>`**、经
> `z-boot-integration-starters/pom.xml` 的 36 条 `<dependencyManagement>` 下发，于是"抬一格兄弟仓版本"
> = 重发整个 z-boot（根 + floor BOM + 23 个 starter），而 floor 里那些第三方一个字都没变。
> 拆完之后：抬兄弟版只重发 `z-boot-fleet` 一个文件夹。
>
> ⚠ **"允许滞后"是有代价的，现在欠着的是 z-ctc 一格**：fleet 钉 z-ctc **1.0.1**，而 z-ctc 仓的 pom 里
> `<revision>` 已经写到 **1.0.2** —— 但 1.0.2 在 repo1 上实测 404（`z-ctc-1.0.2.pom` 与
> `z-ctc-core-1.0.2.pom` 都是；同一坐标 1.0.1 探活 206）⇒ 那一版压根没落进 Central，fleet 按"只钉实测
> 存在"的规矩不能收。z-graph 1.0.7 / z-kb 1.0.3 那两格 1.0.19 已经兑现（Java 8 移植版真上了 repo1，
> 实测 200 后 `--write` 重算收进来的），此前 class-file 61 的 1.0.5/1.0.2 会在 Java 8 运行时
> `UnsupportedClassVersionError`，靠消费者自己覆盖 dm 顶掉的那段临时账已经可以撤了。

### 消费模型：各仓统一继承 `z-boot-parent`（1.0.19 起）

z-opc-foundation 下每个仓的根 pom 从此只写一次 `<parent>`，不再自己维护版本属性表。
**下面这套步骤是 2026-09-28 拿 z-cache 当试点量出来的**，四个坑全是当场踩到、当场改掉的，
不是推演——所以照抄之前先把两把尺跑起来：`python3 _doc/003_script/parent_preflight.py --repo <仓>`
（迁前：哪些键可删/必须留/悬空，以及**每个 `${key}` 挂在哪些坐标上**，见它的第 5 节）和
`python3 _doc/003_script/central_pom_scan.py`（迁后：发布态 pom 的合法性）。

1. **先留底**：`mvn -B -DskipTests clean package dependency:tree`，把 tree 里的
   `groupId:artifactId:jar:version` 去重排序存成基线。这一步不能省：迁移的判据不是"能构建"，
   而是"**除了我明确要改的，一件版本都没漂**"。
2. `<parent>` 换成 `io.github.yuku123:z-boot-parent:1.0.19` + **`<relativePath/>` 留空**
   （parent 不在磁盘上，在 repo1）。原来是 `com.zifang:z-opc:1.0.0-SNAPSHOT` 这类
   **只在作者 `~/.m2` 里存在**的本地 parent 的仓，这一步顺带把"换台机器连 pom 都读不动"修掉
   —— z-cache 那句 `<relativePath>../pom.xml</relativePath>` 指向的是一个**不存在的路径**。
3. 删掉自家 `<properties>` 里 parent 已供给的版本键（`z-util.version`/`util.version`/
   `z-boot.version`/`maven.compiler.*`/编码…），并把子模块里引用这些键的 `<version>` 整条删掉，
   改由 DM 下发。**与地板面值不同的那一格必须留着**（z-cache 的 `log4j2.version=2.17.2`
   对地板 2.25.4 是刻意的零漂移选择，删掉就是悄悄换实现）。
   判"供不供"要按**坐标**判，不是按键名：z-vector 的 `zutil.version` 键名父链没有，但 fleet
   按坐标管着 `z-util-core/math/ml` 且面值同为 1.0.13 ⇒ 该删；而 `protobuf-java-util` 地板
   真的不管（只字面管 `protobuf-java`）⇒ 删键当场悬空。preflight 的第 5 节逐处给出这个结论。
4. 在仓根 `<dependencyManagement>` 里给**自家每个模块**补一条 `${project.version}`。
   这条不是装饰：继承来的 DM 会改写**传递依赖**的版本，而 fleet 里本仓那一格钉的是 repo1 的
   **旧发布件** ⇒ 不补这格，`z-cache-server` 的 shade fat jar 会把 `z-cache-common` 的
   **1.3.5 字节码**打进 1.3.6 的包里（迁移前被 z-opc 的 DM 压成 1.3.4，一样是错的）。
   补上后 tree 与 shaded jar 都回到 1.3.6（实测 `Including …:1.3.6 in the shaded jar`）。
5. ⚠ **dm 优先级反直觉的一处**：`<scope>import</scope>` 进来的 BOM **顶不过**从 parent
   继承来的**直接** DM 条目。z-cache 保留了 `log4j-bom:2.17.2` 的 import，实测 4 件
   log4j 仍然漂到地板的 2.25.4 ⇒ 要压回去必须按坐标逐条写**直接**条目（`log4j-api` /
   `log4j-core` / `log4j-jul` / `log4j-slf4j-impl`）。同理 `snakeyaml`：monorepo 那侧钉 2.0
   （CVE-2022-1471），地板跟 spring-boot 2.7.18 给 1.30，不显式写就静默降版本。
6. ⚠ **悬空属性**：z-cache 的 javadoc 插件写着 `${compile.version}`，全仓 11 个 pom 引用这个键、
   只有它没定义、父链里也没有 ⇒ 传进插件的是字面量 `"${compile.version}"`，而 `failOnError=false`
   把它吞了，所以这处点伤一直没现形。迁移会换掉父链，**这类借自旧 parent 的属性一定当场炸**，
   正好是一次清账：`grep -oE '\$\{[a-zA-Z0-9_.-]+\}'` 逐仓对一遍定义。
7. ⚠ **发布形状：换了 `<parent>` 就必须自己把 pom flatten 掉**，否则发出去的是"带着 org parent 的 raw pom"。
   `z-boot-parent` 那条 flatten 声明是 `<inherited>false</inherited>`（`z-boot-parent/pom.xml:257-264`，
   它自己用 `resolveCiFriendliesOnly`），**不会**把 flatten 下发给消费仓——它当初的理由是"这 30 个仓发的
   是非扁平 pom，凭空继承一条插件声明只有惊讶"，而迁移恰恰把它证伪了：加了 `<parent>` 之后
   "非扁平"就等于把发布件的依赖含义挂在那条 parent 链上。判据按**本仓现在中央上是什么形状**来定：
   - 本来发的是自包含 raw pom（`z-graph:1.0.7`、`z-rpc:1.0.3` 这种，`<parent>` 计数 0）⇒ 本仓
     `<build><plugins>` 里**常开**补 flatten `oss` + `updatePomFile`（形状照 `z-cache/pom.xml:160-193`，
     版本钉 1.5.0：门禁机 Maven 3.6.0 实测只有 1.5.0 rc=0）。**别挂 `central` profile**——不带
     `-P central` 的 `mvn install` 会把带 parent 的废 pom 装进仓里。
   - 本来就发带 `<parent>` 的扁平 pom（`z-skill` 的叶子模块 0.2.0 就带 `<parent>z-skill:0.2.0</parent>`）
     ⇒ **保持它自己的 flattenMode 不动**，链子多一级是它既有的口径，不是这次迁移引入的。
     但要清楚：`resolveCiFriendliesOnly` 只展开 `revision/sha1/changelist`，**不会**把
     `${netty.version}` 这类解析成字面量，所以这些仓的发布含义确实随 parent 链走。
   - 回读判据：每份 `.flattened-pom.xml` 的 `<parent>` 计数、`com.zifang` 计数、悬空 `${...}` 都要和
     **本仓中央上那一版**逐字对得上，而不是全组织统一成 0。
8. ⚠ **地板把 logback 从所有树里摘了**：`z-boot-dependencies/pom.xml:500-510` 对
   `spring-boot-starter-logging` 写了 `*:*` 通配 exclusion（逐字抄自 c2f 的
   `c2f-boot-third-dependencies/pom.xml:345-355`，它那一侧还配套把 log4j2 整族喂到 2.25.4）
   ⇒ 继承 parent 之后 `logback-classic`/`logback-core`/`log4j-to-slf4j`/`jul-to-slf4j` 从每棵树里消失。
   **这格按"作用域"判，不按"少了几个坐标"判**：
   - 先看这个模块自己有没有 exclusion。`z-config-admin`/`z-rpc-admin`/`order-service`/`user-service`
     从建仓那个提交就自己排掉了 starter-logging（`git log -S` 命中的是 init 提交）⇒ 它们本来就不吃
     logback，通配 exclusion 对它们是惰性的，生产日志实现（log4j2）没动。
   - 真正掉的是 **test 作用域**那一串（`z-graph` 87→83、`z-skill` 73→68 少的都是它）：后果只是测试台
     多打两行 `SLF4J: Failed to load class "org.slf4j.impl.StaticLoggerBinder"`。这两仓现读
     `find -name "logback*.xml"` = 0 个、代码里 0 处 logback/log4j 引用 ⇒ **不补**，
     别看见树里少了 logback 就每仓加一条依赖。
   - 确实要 binding 的仓按既有写法自己声明，别改地板：运行期用 slf4j-simple（`z-graph-bolt-server`、
     `z-vector`），测试期用 test 作用域的 logback-classic（`z-rpc-spring-boot-starter/pom.xml:74-89`）；
     版本都不用写——地板 import 的 `spring-boot-dependencies` 供着。
9. ⚠ **"中央上有这件"不等于"这件读得动"**：ranged GET 拿 206 只证明文件在，不证明它的 pom 解析得了。
   `io.github.yuku123:z-vector:1.0.1` 那个根 pom 写着 `<parent>com.zifang:z-opc:1.0.0-SNAPSHOT</parent>`
   （`relativePath ../pom.xml`），而这件只在作者机器的 `~/.m2` 里存在、repo1 永远没有 ⇒ 任何干净机器
   解析 `z-vector-api:1.0.1` 必挂。Central 不可覆盖 ⇒ **这种发布号是永久残次品，只能换号**
   （z-vector 第一个自包含的是 1.0.3/1.0.4，根 pom `<parent>` 计数 0）。这条只有 repo1-only 那遍
   复跑能抓到，本机 `~/.m2` 里恰好有那件快照就一路绿。所以每仓还有一遍必查：
   把自己依赖的每个内部件 `curl` 回来读 pom，`<parent>` 指向 `com.zifang` 的一律抬号。
   **同一个坑的第二种死法**：`<project><version>` 写 `${revision}` 而仓里没有常开 flatten ⇒
   发上去的 pom 上那行就是字面的 `${revision}`，使用方一样解析不出（`${project.version}` 反而没事，
   它能被消费方自己的模型补出来，见上面步骤 3 的实测）。现算工具 `central_chain_probe.py` 把这类判成
   `UNRESOLVED_OWN_VERSION`：fleet 那 163 格里目前 1 格 = `z-agent-proxy:0.1.0`，同样只能补 flatten 后抬号。

**判据（两遍都要跑）**：
- 复跑步骤 1 那条命令，与基线 diff ⇒ 允许出现的差异**只有你明确决定要改的那几行**
  （试点那一轮的完整 diff 是 1 行：`z-cache-common 1.3.4 → 1.3.6`）。
  提坐标两边用**同一个** `grep -oE 'g:a:jar:v'`，别一个 4 段一个 3 段——那样比出来的
  "138 项变动"是格式差，不是版本漂。
- 干净机器复跑：`mvn -B -s z-boot/_doc/003_script/repo1-settings.xml -Dmaven.repo.local=<空目录> clean package`。
  用 `-s` 而不是 `-gs`：这样 `~/.m2/settings.xml` 整个作废，aliyun 镜像和 seenew 那个私有
  `nexus` profile 都不会注入，只有 repo1 说话。
  这一步才是迁移的目的本身——本机 `~/.m2` 里有旧 parent 时，"换台机器构建不起来"是测不出来的。
- ⚠ **基线那遍和迁移后那遍必须串行，不能并行**。z-vector 那一轮把 `HEAD~1` 与 `HEAD` 两条
  `mvn clean package` 同时发出去，两边都在 `ZVectorConfigContractTest` 报**一模一样**的
  5 条错（10 run / 1 failure / 4 errors），看着像"这仓本来就红"，其实是两边都要绑
  **写死的** 6334（`ZVectorProperties` 的默认端口）互相踩掉；这台机器还常年跑着平台进程，
  占着 6334/6379/8091/8888/9085/9090/12888/18180/20880。见到
  `BindException: Address already in use` 先 `lsof -nP -iTCP:<port> -sTCP:LISTEN` 认人，
  **别去 kill 在跑的服务**；要判"迁移有没有伤到测"，就在**两边同一条命令里排掉同一个测类**
  （`-Dtest='!XxxTest' -Dsurefire.failIfNoSpecifiedTests=false`），再把这个测类单独串行跑一遍对比。
- 顺手回读每份 `.flattened-pom.xml`：判据是**和本仓中央上那一版对得上**（见步骤 7 的三种形状），
  自包含形状的仓要求 `<parent>` 计数 0、不含 `com.zifang`、不含悬空 `${...}`；
  本来就发带 `<parent>` 的仓（`z-skill` 那一类）叶子件带 `<parent>z-skill:x.y.z</parent>` 是对的，
  但**根 pom 的新 parent 必须落在 repo1 上读得动**，这条由下一遍复跑覆盖，不靠肉眼。

### 聚合 POM (3 个) + 两个独立 pom

- `z-boot`（**根，1.0.19 起没有 `<modules>`**，只带 plugin 版本、`central` profile、flatten 配置；它是**发布用** parent）
- `z-boot-starter`（基础 starter 聚合：base / web / datasource）
- `z-boot-integration-starters`（集成 + L3 聚合 starter 聚合，20 个 active `<module>`）
- `z-boot-dependencies` / `z-boot-fleet` 两个 BOM 文件夹 + `z-boot-parent` 各是独立工程，都不聚合任何人
  （注意 `z-boot-parent` 是**消费用** parent，和上面那个"发布用"根 pom 不是一个东西：根只管发布口径，
  parent 管的是使用方拿到什么）

五个文件夹（+ 根）都是**独立可发**的 Maven 工程：`<parent>` 和自己的 `<version>` 都写字面量（不再有
`${revision}`），所以 `mvn deploy -f <文件夹>/pom.xml` 只发那一个文件夹。

---

## ✨ 核心能力

### L3 中间件聚合（一行集成）
- ✅ **19 个聚合 starter**（上面那张表逐行实测），把已发布的 z-* 中间件包装成 `z-boot-*`；
  `z-boot-integration-starters` 下合计 20 个 `<module>`，多出的 1 个是 `z-boot-jackson-starter`（不聚合任何 L3）
- ✅ **每个 starter 只做"传递依赖"这一件事**：
  - 引入对应 L3 坐标作为 transitive dependency（19/19 有，pom 抽取实测）
  - ~~暴露统一的 `z.{pkg}.enabled` 开关（默认 false）~~ **这条以前是编的**：开关名、默认态一律由 L3 自己定，
    z-boot 这层只有 `z-boot-ctc-starter` 自己挂了开关（`z.boot.ctc.enabled=true`，
    `ZBootCtcAutoConfiguration:27`，实测全仓 java 里 `@ConditionalOnProperty` 仅此 1 处命中——
    注意它用的是第四种命名 `z.boot.ctc`，和 L3 侧的 `z.ctc`/`zmq`/`z-msg` 都不同）；
    逐行实测见上表最后一列
  - **marker class 不是 19/19 都有**：**9 个** starter 有 `com/zifang/z/boot/{pkg}/ZBoot{Pkg}AutoConfiguration.java`
    （config / cache / mq / gw / kb / vector / graph / rpc / oss——纯占位类，没有 `@AutoConfiguration` 注解，
    也没写进任何 `spring.factories`——实测 z-boot 里只有
    `z-boot-jackson-starter` 和 `z-boot-ctc-starter` 两个模块注册了自动装配），
    `z-boot-script-starter` 是**第十个有 marker 的、但换了个命名**（`com/zifang/z/boot/script/ZBootScriptStarter.java`，
    28 行、`public final class` + 私有构造、0 注解、`src/main/resources` 整个目录都没有 ⇒ 不注册任何 bean），
    `z-boot-msg-starter` / `z-boot-schedule-starter` 只有 `package-info.java`，
    `z-boot-llm/mcp/skill/agent/bot/agent-proxy-starter` **6 个零源文件**——它们的 jar 实测 ~1.9 KB，只有一个 MANIFEST
- ✅ **L3 版本统一由 `z-boot-fleet` 的 `<z-*.version>` property 管理**（1.0.19 起；此前在根 pom），
  改版本 = 改 `gen_fleet_bom.py` 的 `FAMILIES` 表后 `--write` 重算，**不手改 pom**。
  1.0.18 及以前是"根 property + `z-boot-integration-starters` 的 36 行 dm 写 `${z-*.version}`"
  （2026-09-26 之前有两处漏网的字面量/错 property：`z-oss-common` 钉死 `1.0.1`、`z-ctc-web` 钉
  `${project.version}`（= z-boot 自己的 `<revision>`，跟 z-ctc 的发布节奏无关，repo1 上那个号根本不存在），
  两处都已接回 `${z-oss.version}` / `${z-ctc.version}`）
  - ⚠ **同一类坑还有"子 pom 里再抄一份 property"**：`z-boot-msg-starter/pom.xml` 和
    `z-boot-schedule-starter/pom.xml` 各自写过 `<z-msg.version>` / `<z-schedule.version>`，
    **子 pom 的 property 会遮蔽父 pom 的**——1.0.15 那次只抬根 property 时，`dependency:tree`
    实测仍解析到 `z-msg-web:jar:1.0.0`（而且 msg 那份副本自己的注释写着"须与根 pom 同步"）。
    两份副本已在 `a6035e4` 删掉。判据：改完 property 必须跑 `dependency:tree` 从 **stdout** 读实际落点，
    "flatten 之后子 pom 要自包含"不是留副本的理由——flatten 折的本就是**生效值**。
    （`z-boot-dependencies/pom.xml:136-142` 里还有 7 处这种 property 副本，动它会改到发布件字节，尚未处理）
    1.0.19 里 msg/schedule 那两条**依赖级**的 `${z-msg.version}` / `${z-schedule.version}` 也删了（版本改由
    fleet 的 dm 供给），因为 property 已经不在父链上，留着 Maven 当场报 "must be a valid version"
    —— 第二遍构建失败就是这么炸出来的。

### 第三方版本权威（BOM）
- ✅ **1.0.19 的分工已经量过**：`z-boot-dependencies` dm **156 条**（字面 109 / property 42 / import 5），
  其中 `io.github.yuku123` 坐标 **0 条**；`z-boot-fleet` dm **163 条**，其中 `io.github.yuku123` **163 条**
  （全部 `${z-*.version}`，字面 0）；`z-boot-parent` dm **24 条**，全是 `io.github.yuku123` 的 z-boot 自家坐标。
  floor 与 fleet 坐标空间不相交 ⇒ 并列 import 不打架。
  下面那批 132/133 的读数是 **1.0.16 发布件**的历史账，别拿来当现值。
- ✅ **z-boot-dependencies** 锁的是**第三方**版本，不是 z-* 的版本锁入口
  （实测：BOM 的 `<dependencyManagement>` 里 `z-boot-*` 坐标 **0 条**，见上面「5 分钟接入」的 ⚠）
- ✅ **132 条受管依赖**（2026-09-26 在 **repo1 的 1.0.16 发布件**上逐条解析 `<dependencyManagement>`
  得到的分解）：**119 条钉的是字面版本**（其中 2 条是 `scope=import`）+ **13 条钉的是 `${...}` property**
  = 132，条数自洽。内容如 spring-boot-dependencies 2.7.12 / jackson-databind 2.18.6 /
  mybatis-plus 3.5.7 / druid 1.2.23 / log4j2 2.25.4 / commons-lang3 3.18.0
  （早先这里写的是"115 + 14 + 2 = 131 / 共 133"，那 2 条 `import` 本来就带字面版本、被重复数成了另一类，
  分解对不上总数；1.0.16 起按上面的口径重数）
- ✅ **1.0.16 修掉了一个对外失效的缺陷**（这是发 1.0.16 的唯一目的）：
  1.0.15 及之前，外部工程 import `z-boot-dependencies` 后有 **4 条**受管项解析不出来——
  `io.github.yuku123:z-graph-{api,core,protocol}`（`${z-graph.version}` 只定义在根 pom 里）和
  `com.oracle.database.jdbc:ojdbc6`。症状不是"没锁住"，是 Maven **当场拒读整份 BOM**：
  `'dependencies.dependency.version' for io.github.yuku123:z-graph-api:jar is missing`，
  定位到 BOM pom 第 977 行；同一支探针把坐标换成钉字面版本的
  `org.springframework.boot:spring-boot-configuration-processor` ⇒ 正常解析出 2.7.12（阳性对照）。
  成因在发布机制：BOM 用 `resolveCiFriendliesOnly`，占位符**原样**留在发布件里（flatten 文档原话
  "keep the dependencyManagement as-is without resolving parent influences"），指望父 pom 给出 property，
  而根 pom 用 `oss` 模式发布成 37 行、**`<properties>` 一个都没有** ⇒ 链条断在中间。
  所以这个缺陷在**仓内永远看不见**（reactor 里父 pom 是真的，property 解析得动）。
  ⚠ **早先这里写的"14 条都失效"是错的**：那 14 条 `${...}` 里有 **10 条**的 property 就在 BOM
  自己那 110 条 `<properties>` 里，外部 import 者解析得到；真正失效的是 4 条。数错的原因是把
  "版本带 `${}`"当成了"对外失效"，没逐条回查 property 定义在哪。
- ✅ **修法 = 让发布出去的父 pom 带上 `<properties>`**（`z-boot/pom.xml` 的 flatten 配置加
  `<pomElements><properties>keep</properties></pomElements>`）。为此试过又否掉的三条路留档：
  `flattenMode=bom` 会把 `<parent>` 剥掉、占位符一条不归零；
  `<pomElements><dependencyManagement>interpolate</…>` 构建成功但 13 条占位符**依旧在**；
  写 `resolved` 连构建都进不去——`ElementHandling` 的合法取值实测只有
  `flatten / expand / resolve / interpolate / extended_interpolate / keep / remove`（`javap` 读 Enum）。
  即"占位符归零但不吞 import"这一档插件里没有现成档 ⇒ 不改 BOM，改**父 pom 该发布成什么样**。
  实测效果：`z-boot-1.0.16.pom` = 69 行 / **30 条 property**（含 `z-graph.version=1.0.5`），
  对 1.0.15 的 37 行 / 0 条。只加 `<properties>`、不顺手展开占位符，是这套里改动最小的一档
  （`flattenMode=bom` 产出的根 pom 与之逐字节相同，但会顺带换一整套元数据处理规则，没必要）。
  一次性对账（空仓、隔离 repo，跑的是**上传的那批字节**）：无版本声明 `z-graph-api`
  ⇒ 对 1.0.15 拒读、对 1.0.16 解析出 **1.0.5**；`ojdbc6` 现在给的是消费者自己 pom 上那句
  honest 的 "version is missing"，而不是一份坏掉的 BOM。
- ⚠ **这条修法有个连带效应，发布件形状变了**（别拿行数当"没被动过"的尺）：根 pom 的
  `<build><plugins>` 里那份 flatten `<configuration>` 会被 BOM 模块**继承**，于是 BOM 那遍
  从"保留注释的原始 XML 支路"切到了模型写入器 ⇒ repo1 的 BOM 从 1011 行变 **889 行**、
  XML 注释 **2153 字节 → 0**。A/B 实测（同一份 HEAD 树，唯一差别是有没有那段 `pomElements`）：
  加 ⇒ 889 行 / 0 注释字节，且产物与 repo1 上 1.0.16 的 BOM **md5 逐字节相同**
  （`c6e4141d6b1e41a65a4a0828ff0acbb6`）；去掉 ⇒ 1009 行 / 2366 注释字节（这是 1.0.16 那棵树的读数，
  仓内现在因下文那条"删 7 条 property 复制件"是 1005 行）。两遍
  `<dependencyManagement>` 都是 132 条、逐条对得上，实质差别只有 `nacos-config` /
  `flowable-…-process` 两条 `<version>` 尾部的空白被规范化掉。
  其余 25 个子模块的发布件形状，逐个 diff 1.0.15/1.0.16 量过（27 个 pom 全部成对比过，不是抽样）：
  **每个 pom 多出的恰好是它自己在源码 pom 里声明的那几条 property**——22 个模块是 3 条
  （`maven.compiler.source` / `maven.compiler.target` / `project.build.sourceEncoding`，每个 pom
  都自己写了这三条）、`z-boot-base` 4 条（多 `log4j2.version`）、`z-boot-jackson-starter` 4 条
  （多 `jackson-databind.version`）、`z-boot-datasource-starter` 6 条（多 `druid/mysql/log4j2.version`）、根 pom 30 条（+1557 B）；其余行逐字节同。
  对外新暴露的 129 条去重 property 键值（27 个发布件的 `<properties>` 段合计 274 **行** = 220 条条目
  + 每份 pom 那两行标签），
  按凭证类词（password/secret/token/apikey/credential/…）和内网主机类词（`192.168.`/`localhost`/
  `http://`/…）扫 = **0 命中**（按 property 条数分：22 个模块 3 条、`z-boot-base` 4 条、
  `z-boot-jackson-starter` 4 条、`z-boot-datasource-starter` 6 条、`z-boot-dependencies` 110 条、根 pom 30 条；
  同一批 1.0.16 发布件的 `<dependencyManagement>` 里 `io.github.yuku123` 受管坐标合计 3 条，全在 BOM 那份里）。
  这把尺的阳性对照是当场喂它两支必然该红的合成行
  （一支 `<db.password>` 带假口令、一支 `<repo.url>` 带 `192.168.` 开头的内网地址；两条原文留在量具里，
  不往公开 README 抄）⇒ 都命中，所以那个 0 不是"正则写空了"。
- ⚠ **`com.oracle.database.jdbc:ojdbc6` 那条受管项已在 1.0.16 删除**（133 → 132 条）。它钉的是
  `${oracle6.version}`，而这个 property **全仓从未定义过**（首笔提交 `2b17fb9` 起就是死的）——
  所以它不是"对外失效"，是对内对外都从来没生效过，谁撞上都是 Maven 拒读整份 BOM。
  留了一条注释说明为什么这里空了。删它的判据是机械的：受管项的 property 在 BOM 自身 + 父链里
  都找不到 ⇒ 死项。
- ✅ **BOM 自己那份 `<properties>` 里 L3 Agent/AI 的 7 条复制件已删**（2026-09-26，仓内 1009 → 1005 行）。
  判据同样是机械的而不是"看着没人用"：这 7 个键（`z-agent-kernel` / `z-llm` / `z-mcp` / `z-skill` /
  `z-agent` / `z-bot` / `z-agent-proxy`）在 BOM 文件内各只出现 **1 次 = 只有定义**，而引用它们的
  `z-boot-integration-starters/pom.xml:269-294` 父链是**根 pom**（根 pom 91-97 行本来就有一条同值的），
  且 `<scope>import</scope>` 只搬 `dependencyManagement`、不把 property 借给导入方 ⇒ 复制件空转。
  两侧都实测过：改前/改后 `help:effective-pom`（BOM 与 `z-boot-llm-starter` 两个模块）**逐字节同**
  ⇒ 仓内解析零影响；发布侧新构建的扁平件 889 → **882 行**、property **110 → 103 条**，
  少掉的正好是那 7 个键、`<dependencyManagement>` 规范化后逐条同 ⇒ 对外也只是少 7 个没人能读的键。
  ⚠ 这条只落在仓里：**repo1 上的 `z-boot-dependencies:1.0.16` 仍是 110 条**，要等下一次发布才变。
- ✅ 这条"外部 import 者能不能解析"从此有永久闸：`z-opc/z-middleware-integration-test` 的
  `ZBootBomExternalResolutionIT`（5 例，见下面「集成测试覆盖」）。
- ✅ 自研 L3 里目前**只有 z-graph 的三个坐标**（引擎侧 `z-graph-{api,core,protocol}`，2026-09-26 补进）
  进了这份 BOM；**连 `z-graph-spring-boot-starter` 本身都不在**，其余 z-* 也仍只在
  `z-boot-integration-starters` 里钉，import 这份 BOM 的消费者拿不到约束
- ✅ 业务方对**第三方**依赖**禁止**自己声明版本号（由这份 BOM 锁）；
  但对 `z-boot-*-starter` 和无 BOM 约束的 L3 坐标，**必须自己写 `<version>`**
  ——实测无版本声明会被 Maven 直接拒读（见「5 分钟接入」的 ⚠），这条以前写反了

### 零 z-opc 内部依赖
- ✅ **reactor 里的 26 条 active `<module>` 都不依赖** `com.zifang:z-opc` (monorepo 内部 parent)——
  分解：根 3 + `z-boot-starter` 3 + `z-boot-integration-starters` 20（`grep -cE "^\s*<module>"` 三个 pom 相加）。
  全仓 `--include=pom.xml` 找**真坐标位** `<groupId>com.zifang`：4 条命中、全在未进反应堆的
  `z-tool-webide-spring-boot-starter/pom.xml`（55/66/70/74 行），参与构建的 pom 里 0 条
  （另有几处 `com.zifang` 出现在**注释文字**里——解释 tool-webide 为什么被排除、以及
  script-starter 提到 z-script 的包名 `com.zifang.z.script`——那不是坐标，别拿"grep 到 com.zifang"当缺陷）
- ⚠ **树上只剩一个未进 reactor 的目录**：`z-tool-webide-spring-boot-starter`
  （`z-boot-script-starter` 已经在 1.0.15 补进反应堆并发布，见下面目录树的 ⚠）。
  这条不是"忘了加"，是**加了就整个 reactor 读不起**——2026-09-26 本机复跑过：放开那行 `<module>`
  ⇒ `mvn -B -o validate` rc=1、5 条 ERROR 原文与判据记在 `z-boot-integration-starters/pom.xml`
  那段注释里。要点两条：它 `<parent>` 写死 `1.0.1` 不吃 `${revision}`；它三条依赖的 groupId 是
  `com.zifang`，而本聚合 pom **已经**管了 `io.github.yuku123:z-tool-webide-{common,api,core,docker}`
  ⇒ 报 "version is missing" 是 groupId 对不上，不是没人管版本。被包的 L3 源码在 **sibling 仓
  `z-opc-foundation/z-webide`**（不在 z-opc 里），repo1 上两个 groupId 都 404 ⇒ 今天无解，
  再入门条件按那段注释逐条走。
- ✅ **可独立发布到 Maven Central**——`<revision>` 1.0.17，repo1 实测 27 个坐标的 `.pom` 全 200、
  staging 里 84 个 `.pom`/`.jar` 与 repo1 逐字节相同、84 份 `.asc` 全部验签通过（判据脚本、注入对照
  与历史口径见上面「已发布到 Maven Central 的所有模块」那段）

---

## ⚙️ 实用 Case（生产场景）

### Case 1: 业务方全栈（一行 import 一个能力）

依赖形状就是上面 [🚀 5 分钟接入 · 方式一](#方式一业务模块推荐-一次性-import-全部能力) 那一份
（BOM import + 每个 `z-boot-*-starter` 自带 `<version>`），这一格以前抄了第二份、
下面「模块结构 → 用法」抄了第三份 ⇒ 2026-09-26 三份收敛成那一份真源，别再往回抄。
按场景在真源那份的 `<dependencies>` 里增删就行，全 19 个 L3 聚合 starter 逐个列在
「z-boot-* 聚合 starter（19 个）」那张表里。业务方全栈常见的一档：`web` + `datasource`
+ `jackson`，再按需挂 `cache` / `mq` / `rpc` / `config` / `oss`。

### Case 2: 单独用某个 starter（外部开发者）

```xml
<!-- 我只要 z-cache 客户端, 不要全套 -->
<dependency>
    <groupId>io.github.yuku123</groupId>
    <artifactId>z-boot-cache-starter</artifactId>
    <version>1.0.17</version>
</dependency>
```

### Case 3: 在 L3 starter 中用 BOM 锁第三方版本（不引入 z-boot 内部坐标）

```xml
<!-- L3 starter 可以依赖 z-boot-dependencies BOM, 但**绝不**依赖 z-boot-base / z-boot-web-starter -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>io.github.yuku123</groupId>
            <artifactId>z-boot-dependencies</artifactId>
            <version>1.0.17</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

### Case 4: 通过 z-boot-* 启动 RAG 知识库

```xml
<dependencies>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-web-starter</artifactId><version>1.0.17</version></dependency>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-kb-starter</artifactId><version>1.0.17</version></dependency>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-vector-starter</artifactId><version>1.0.17</version></dependency>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-cache-starter</artifactId><version>1.0.17</version></dependency>
</dependencies>
```

---

## 🏗️ 项目结构

```
z-boot/
├── pom.xml                          # 发布用 parent (Central namespace) — 1.0.19 起无 <modules>，只管 plugin 版本 / central profile / flatten
├── z-boot-dependencies/             # 第三方版本 BOM（仓内 1179 行 / 156 条受管项；发布件行数以 flatten 后为准，见下面 flatten 那节）
├── z-boot-fleet/                    # 兄弟仓 z-* 版本 BOM（911 行 / 163 条受管项 / 21 个版本格，由 gen_fleet_bom.py 生成，不手写）
├── z-boot-parent/                   # 消费入口 parent（270 行）：继承地板 + import fleet + 24 条 z-boot-* + Java 8 pluginManagement
├── z-boot-starter/                  # 基础 starter 聚合
│   ├── z-boot-base                  # Log4j2 门面
│   ├── z-boot-web-starter           # Web + Log4j2 + Knife4j
│   └── z-boot-datasource-starter    # Druid + MyBatis-Plus + mysql
└── z-boot-integration-starters/     # 集成 starter 聚合 (20 个 active <module>)
    ├── z-boot-cache-starter         # ← L3 聚合
    ├── z-boot-mq-starter            # ← L3 聚合
    ├── z-boot-gw-starter            # ← L3 聚合
    ├── z-boot-kb-starter            # ← L3 聚合
    ├── z-boot-vector-starter        # ← L3 聚合
    ├── z-boot-graph-starter         # ← L3 聚合
    ├── z-boot-rpc-starter           # ← L3 聚合
    ├── z-boot-oss-starter           # ← L3 聚合
    ├── z-boot-schedule-starter      # ← L3 聚合
    ├── z-boot-msg-starter           # ← L3 聚合
    ├── z-boot-script-starter        # ← L3 聚合 (1.0.15 才进反应堆)
    ├── z-boot-config-starter
    ├── z-boot-ctc-starter
    ├── z-boot-jackson-starter
    ├── z-boot-llm-starter
    ├── z-boot-mcp-starter
    ├── z-boot-skill-starter
    ├── z-boot-agent-starter
    ├── z-boot-bot-starter
    └── z-boot-agent-proxy-starter
```

> **1.0.19 是拓扑改动**，不是又一个版本号：以前根 pom 是"顶层聚合"（`<modules>` 挂 3 个文件夹 + 兄弟仓版本
> property 全住在这里），现在根只是 parent，五个文件夹各自独立成工程、各带字面版本。发版按文件夹发
> （`_doc/003_script/deploy_maven_center.sh publish <folder>`），兄弟仓抬一格只重发 `z-boot-fleet`，
> 不再牵动 floor BOM 和 23 个 starter。

> 上面这棵树与各 pom 的 active `<module>` 是**逐名对过账的**：`~/.cache/zboot-1016/tree-vs-modules.py`
> 剥掉 XML 注释后取 `z-boot-starter` 3 + `z-boot-integration-starters` 20 条，与树里的名字求双向差集
> ⇒ **双向 0 差**；同一条尺报出"磁盘上有 pom 但未进 `<module>`"= 1 个（就是下面那条 webide）。
> 造这把尺时它先假红了两次：注释里也写着 `<module>`（不剥就把排除掉的模块算成在反应堆里），
> 以及树的第一行 `z-boot/` 没有 `├──` 前缀（漏了它反报"树漏画"）。阳性对照：内存里抹掉
> `z-boot-script-starter` 一个名字，尺当场报出它。对不上是迟早的事，所以判据留在仓外、不靠眼睛。
> ⚠ 1.0.19 起这条尺**不再对根 pom 跑**（根没有 `<modules>` 了），"根 3 条"那个读数只属于 1.0.18 及之前。

> ⚠ 唯一没有进 `<modules>` 的 starter：**`z-boot-integration-starters/z-tool-webide-spring-boot-starter`**
> （注意它在 `z-boot-integration-starters/` 下面，不在仓根 ⇒ 只扫顶层目录的尺会报"零个未进反应堆"，
> 上面那条尺因此改成递归找 `pom.xml`）。
> 不是"没排上队"，是**补进去会让整个 reactor 读不起 pom**（`mvn -B package` rc=1，Maven 自己数出来
> `has 5 errors`；5 条原文按形状抄在 `z-boot-integration-starters/pom.xml:46-53` 的注释里）。
> 2026-09-26 对着它自己的 pom 逐行量过，坏在**依赖侧不是坐标侧**：
> 它的 `<parent>` 写死 `1.0.1`（不吃 `${revision}`，14 行自己那份 `<version>` 同样写死），自身
> `<groupId>` **已经**是 `io.github.yuku123`（12 行）；`com.zifang` 那 4 条全在依赖里——
> 55 行 `<dependencyManagement>` import 了 `com.zifang:z-boot-dependencies`（repo1 上 404，这份 BOM
> 对外只叫 `io.github.yuku123`），66/70/74 行是 `com.zifang:z-tool-webide-{docker,api,common}`；
> 无 `<version>` 的直接依赖实测 **4 条** = 那 3 条 + `spring-boot-autoconfigure`。
> 要发它得先把 `z-tool-webide-{docker,api,common}` 发到 Central、把那处 BOM import 换成
> `io.github.yuku123`、并把写死的版本换成 `${revision}`。
> （另一条 `z-boot-script-starter` 的排除理由 2026-09-26 实测是假的——空仓
> `dependency:resolve io.github.yuku123:z-script-web:1.0.0` `BUILD SUCCESS`、落地 16 个
> `io.github.yuku123` jar（其中 z-script 自己的三个坐标 core/engine/web 都在），所以 1.0.15 已补进
> `<modules>` 并发布。）

---

## 🔧 高级

### 升级 z-boot / L3 中间件版本

**1.0.19 起分两处**，按你要抬的是哪一类版本选：

- 抬**第三方**（spring / jackson / druid / netty / log4j2 …）→ 改 `z-boot-dependencies/pom.xml`，发 `publish z-boot-dependencies`（+ 需要重发引它的 starter）。
- 抬**兄弟仓 `z-*`**（z-cache / z-mq / z-llm / z-graph …）→ **不要手改 pom**，改 `_doc/003_script/gen_fleet_bom.py` 里的 `FAMILIES` 表然后重算，发 `publish z-boot-fleet` 一个文件夹就完事，floor BOM 和 23 个 starter 都不用动。

```bash
# 真源是脚本里的这张表：repo -> (property 名, 版本)
FAMILIES = { "z-cache": ("z-cache.version", "1.3.5"), "z-llm": ("z-llm.version", "0.1.6"), ... }

python3 _doc/003_script/gen_fleet_bom.py          # 只算不发：逐 family 打印"收几件 / repo1 是 OK 还是 MISSING"
python3 _doc/003_script/gen_fleet_bom.py --write  # 落成 z-boot-fleet/pom.xml
```

脚本的判据不是"我以为这个版本存在"：每个候选坐标都用 `curl -r 0-0` 打 repo1 的 `.jar`/`.pom`
（⚠ **HEAD 不行**，repo1/Fastly 对 HEAD 不给 200，只有 200/206 算活着），200 才写进 pom；
拉不到就报 `MISSING`，本机有 `~/.m2` 副本报 `PENDING`（已 deploy 未索引）。
**所以 fleet 里不存在"凭记忆钉一个还没发出去的版本"这条路**——1.0.18 之前那 36 行 `${z-*.version}`
是手抄的，抄错没人拦得住。

```xml
<!-- z-boot-fleet/pom.xml（脚本产物，勿手改） -->
<properties>
    <z-cache.version>1.3.5</z-cache.version>
    <z-llm.version>0.1.6</z-llm.version>
    <z-graph.version>1.0.5</z-graph.version>   <!-- 1.0.6 作废（api/protocol 是 52=Java 8、core/bolt/starter 是 61=Java 17，
                                                    class major 实测混装）、1.0.7 未发 ⇒ 钉 repo1 上内部一致的 1.0.5 -->
    ...                                        <!-- 共 21 格 -->
</properties>
```

> 别指望"改 property 一处"就对外生效：property 只影响**下一次构建**，业务方拿到的是
> `z-boot-*-starter` 发布件 pom 里**已经展开成字面量**的版本号。抬完必须发版才对外可见。
> 1.0.19 起"发版"的粒度变小了：兄弟版只需 `publish z-boot-fleet`，starter 侧因为把版本格写死成
> `import z-boot-fleet:1.0.0`，所以 fleet 重发一版时要连 starter 一起重发（见下面那条）。
> 2026-09-26 这条正反两面都量过：`${z-msg.version}` 抬到 1.1.0 之后、1.0.15 发布**之前**，
> repo1 上 1.0.14 的 `z-boot-msg-starter.pom` 里读到的还是 `z-msg-web:1.0.0`；
> 1.0.15 上线后同一处 curl 回读 = **1.1.0**；1.0.16 上线后（21:58 那次 curl）再回读 = **1.2.0**。
> 19/19 个 starter 的发布件都按这条对过账，且那 19 个期望值是**从下面那张表机械解析**的
> （21:5x 对 1.0.16 重跑：19/19 一致、0 不一致，见表格下面那段）。

> **曾经欠着的一格（2026-09-27 登记 → 1.0.19 兑现）**：repo1 已有 z-llm **0.1.6**（#40① 的
> "body 读坏回 400 且不再把 controller 方法签名吐给调用方"），而本仓 `<z-llm.version>` 仍是
> **0.1.5** —— 尺是现成的：`python3 ~/.cache/zboot-1016/latest-census.py` 读
> 「分母 19 个坐标 / **LAG 1**：`z-llm-starter` 仓内 0.1.5，repo1 最新 0.1.6」（同一次运行内的
> 阳性对照：把 z-cache 强行退回 1.3.1 后 LAG=2 ⇒ 这一格不是尺瞎）。
> ✅ **这一格 1.0.19 已兑现**：`z-boot-fleet` 的 `<z-llm.version>` = **0.1.6**（脚本对 repo1 实测过才写进去的）。
> 上面那段登记原文保留，因为它记的是"仓内改了、对外没兑现"这件事**只在尺的 F 判红里现形**——
> 1.0.19 的重构就是把这条教训固化成了流程：版本格由脚本从 repo1 回读生成，不再靠人回读声明行。
> `z-opc/z-middleware-integration-test` 原本还自己抄了一份 `<z-llm.version>` **死副本**（本文件内引用次数 0），2026-09-27 已删，
> 删前删后 `dependency:tree` 逐行 diff = 0 行 ⇒ 它从来就没决定过任何读数。
> 在 1.0.19 之前，只有像 z-opc 那样**直接**声明 `z-llm-*` 的消费者能吃到 0.1.6。

消费者的口径没变：`<z-boot.version>` 一处决定所有 z-boot 坐标；第三方锁来自 import
`z-boot-dependencies`，兄弟仓 `z-*` 锁来自 import `z-boot-fleet`（1.0.19 起两者成对，starter 的 pom 里
就把这两条并列 import 写死）。发布件的 pom 里版本全是字面量，`<revision>` 那个占位符从此不出现在
z-boot 自己的 pom 里。

### 自定义 z-boot 内部 starter（私有）

```java
@Configuration
@ConditionalOnClass(MyFeature.class)
@ConditionalOnProperty(prefix = "z.boot.myfeature", name = "enabled", havingValue = "true")
public class MyFeatureAutoConfiguration {

    @Bean
    public MyFeature myFeature(MyFeatureProperties props) {
        return new MyFeature(props);
    }
}
```

参考 `z-boot-ctc-starter`（唯一真有实现的：4 个 class，含 `ZBootCtcProperties` + `ZBootCtcAutoConfiguration`
+ 两个 HTTP hook 默认实现）。其余 `z-boot-*-starter` 的那个 `ZBoot{Pkg}AutoConfiguration` 只是**无注解的空类**
（`public final class` + 私有构造），既不会装配 Bean，也没有配套 Properties——名字里的 `AutoConfiguration`
是历史包袱，别照它抄，也别指望 import 就有效果。

---

## 🧪 集成测试覆盖

`z-opc/z-middleware-integration-test` 里现在有两支管 z-boot 对外契约的 IT，整模块
2026-09-26 21:46 本机跑绿：`Tests run: 57, Failures: 0, Errors: 0, Skipped: 20`（12 个类）。

### `ZBootAggregatorStarterMavenCentralPullIT`（4 例，24.47 s）

- **19 个 z-boot-* 聚合 starter @ 1.0.16**（`VERSION` 已跟版；本轮 IT 文件 md5 `6a1f24aa245d8c66cf68a9b1e4964615`）：逐个拉 `.pom`，HTTP 200 **且**发布件正文里必须出现上表对应的那一个
  L3 坐标（`<artifactId>z-cache-spring-boot-starter</artifactId>` 整串匹配）。
  以前只断言"pom 拉得到"、且只覆盖 10 个 ⇒ 现在 19 行全覆盖，第二列从此不能手填。
- **这张表怎么来的**：不手抄。机械抽取每个 `z-boot-*-starter/pom.xml` 里 `io.github.yuku123` 的**直接**
  依赖（先剥 XML 注释、再剥 `<dependencyManagement>`）⇒ 20 条 active `<module>` 里 19 条有 ≥1 个 z-* 依赖，
  只有 `z-boot-jackson-starter` 是 0 个（所以它不在表里）。
- **表自证**：行数必须等于 19、artifactId 不许重复（重复 = 某个 starter 静默失去覆盖）。
  三支变异实测（1.0.15 那轮的备份 md5 `a74ccbe3fd7c0c0f88ee6c2cb92df2ee`，还原后回读过）：
  1. `AGGREGATOR_COUNT` 改 18 ⇒ `EXPECTED_AGGREGATORS 应该有 18 行 … expected: <18> but was: <19>`
  2. 复制 cache 行**并把 count 一起改成 20**（否则长度守卫先红，重复守卫根本测不到）⇒
     `有重复 artifactId, 对应 starter 没被真正覆盖: [z-boot-cache-starter]`
  3. `VERSION` 改成**当时**从未发布的 1.0.16 ⇒ 19 条 URL 全 404，`Tests run: 4, Failures: 1, Errors: 1`
     （那支 Error 是抽样测试读不到流）。这测试拼的是字面 `https://repo1.maven.org/...` URL、
     不经过 Maven 解析 ⇒ 404 只可能来自 repo1，不是本地仓库的回声
  - ⚠ **第 3 支的注入值会随发布自己失效**：1.0.16 现在真发出去了（21:31 上传），下次抬号必须换一个
    repo1 上还不存在的号——本轮实测 **1.0.17 的 19 条 URL 全 404**，尺仍然抓得住。
    同理，早先这里那句"本机 m2 里没有 1.0.16"也作废了：`mvn deploy` 的 `install` 阶段会顺手把
    1.0.16 装进本机 m2（21:30:40 那批目录），已核对 m2 里的父 pom / BOM 与 repo1 **md5 逐字节同**
    （`eec689f23a7bd8df557ddc293af5797e` / `c6e4141d6b1e41a65a4a0828ff0acbb6`）
- 命名约定校验 ✅（19 个都符合 `z-boot-{pkg}-starter`、无 `--`）
- `z-boot-cache-starter` pom 抽样：确认引用 `z-cache-spring-boot-starter` 且 groupId 是 `io.github.yuku123` ✅

### `ZBootBomExternalResolutionIT`（5 例，4.791 s）—— 1.0.16 新增的永久闸

它验的是**站在仓外** import 这份 BOM 能拿到什么。这件事在 reactor 里结构上看不见（reactor 的父 pom
是真的，property 解析得动），所以只能写成一支"从 repo1 拉字节、按消费者视角建模"的 IT。5 例：

1. 发布件根 pom 仍带 `<properties>`（这条一红，就说明 flatten 那份 `properties>keep` 被摘了）
2. BOM 的**每一条**受管版本，按消费者视角（BOM 自身 property + 发布出去的父链）都必须解析得出，
   残留占位符集必须为空
3. `z-graph` 那条解析出来的版本，要**等于** repo1 上 `z-boot-graph-starter` 发布件里的字面量，
   且该版本自己的 `.pom` 在 repo1 是 200 ⇒ 这一例不抄任何手写数字，两半都现拉
4. 死项 `ojdbc6` 不许回来（判据用 property 名，不是坐标字符串——它在注释里也出现）
5. **自身阳性对照**：同一套判据跑 1.0.15，必须判出"父 pom 0 条 property + 恰好 4 条失效项"
   （`z-graph-{api,core,protocol}` + `ojdbc6`）。第 1–4 例全绿而这一例不红 = 尺瞎了，所以它常驻。

六支变异实测（日志 `~/.cache/zboot-1016/mut-M*.log`；每次注入前 `cp` 具名备份、还原只从备份 `cp`，
还原后 md5 回读 `9dde9c8c683c62c7050bca28b318bec8`）：

| 注入 | 结果 |
|---|---|
| M1 `VERSION` → 1.0.15（把闸指回坏版本） | **4 红**（1–4 例全抓回来，报的就是那 4 条） |
| M2 摘掉"沿父链找 property"那一步 | 1 红：3 条 z-graph 被报失效 |
| M3 把对照例的期望从 4 改成 3 | 1 红：`expected: <3> but was: <4>` |
| M4 分母守卫 `> 100` 放宽成 `> 0` | **0 红** |
| M5 把 `<dependency>` 正则打断（模拟解析器失效） | 2 红：`条目数异常（解析器可能失效了）: 0` |
| M6 阈值改 100 → 200 | 2 红：`: 132` 与 `: 133`（两份 BOM 各一处） |

M4 那一行是**没达标的一支**，留在这是为了记住它为什么不算数：把守卫放宽，对"解析产出 132 条"
这个既成事实没有任何影响 ⇒ 它只在解析器归零时才生效，M4 结构上够不着它。所以补了 M5（证明
"解析产出 0"这个分支可达）和 M6（证明阈值这个数值可判红）。**一条守卫"改坏不红"有两种解释**
（够不着 / 等价变异），必须再拿一支必然够得着的注入把前者排掉，否则不许说这条守卫有效。

⚠ **`dependency:tree` 不是可用性尺**：同一支 tree 对一个 repo1 上 **404** 的坐标照样打印
`…:jar:1.0.15:compile` + `BUILD SUCCESS`，只在日志里留一行 `WARNING The POM for … is missing`。
它答的是"多个候选版本里哪个赢"，"这件到底存不存在"要判 HTTP 状态。上面第 3 例分两半就是这个原因。

⚠ **跑法**：`z-middleware-integration-test` **不在** `z-opc/pom.xml` 的 `<modules>` 里（实测全仓
`grep -rn z-middleware-integration-test --include=pom.xml .` 只有它自己 pom 的 4 处自引用），
所以 `mvn -pl z-middleware-integration-test` 当场 `Could not find the selected project in the reactor`，
必须 `mvn -f z-middleware-integration-test/pom.xml test`。

⚠ **整模块 57 例里有 20 例是关着的**：6 个类级 `@EnabledIfEnvironmentVariable` 开关
（`RUN_ZCACHE_IT` / `RUN_ZMQ_IT` / `RUN_ZOSS_CENTRAL_IT` / `RUN_ZRPC_CENTRAL_IT` /
`RUN_ZWF_CENTRAL_IT` / `RUN_ZWF_RPC_IT`）默认不给值 ⇒ `BUILD SUCCESS` 不等于那些 L3 被验过。

**本轮顺带修掉一格常红**（不是本次抬号引入的）：`ZConfigMavenCentralPullIT` 的 `VERSION` 停在 **1.0.0**，
而 1.0.0 从未发布到 Central —— 实测四坐标 × {1.0.0, 1.0.1, 1.0.2, 1.0.4, 1.0.7, 1.0.8} = 24 次 curl，
1.0.0 那 4 次全 404、其余 20 次全 200。改成该模块 `pom.xml` 自己钉的 1.0.7 后：整模块从
`52, Failures: 1, Errors: 1, Skipped: 20`（20:36:07）变 `52 / 0 / 0 / 20`（20:38:46），逐类 tally
 **只有 ZConfig 那一行变**（其余 10 行逐字节同）。那是 1.0.15 那轮的 11 个类；1.0.16 起多了
`ZBootBomExternalResolutionIT` ⇒ 12 个类 / 57 例。

**同时把该模块的 `<z-boot.version>` 1.0.14 → 1.0.15**：抬号前逐个比了发布件，本模块消费的 7 个 starter
的 pom 在两版之间只差版本字面量、其余逐字节同；`dependency:tree` 两版各 250 行，diff 恰好只有那 7 行
⇒ 对解析出来的依赖树是 no-op（抬号前后两次整模块逐类 tally md5 同为 `c551dffe3c9173c506814b21554add74`）。

**1.0.16 这一轮同一处再抬一次 `1.0.15 → 1.0.16`，抬号前同样逐个比了发布件**：本模块直接依赖的
7 个 `z-boot-*-starter`，两版之间的差异**只有** `<version>` 字面量 + 1.0.16 新多出的那个
`<properties>` 块（6 个是 7 行差异、`z-boot-jackson-starter` 是 8 行，多的那行是它自己声明的
`jackson-databind.version`），其余逐字节同 ⇒ 对它的依赖解析同样是 no-op。
而这个模块 import 的那份 BOM 停在 **1.0.11**（`pom.xml` 的 `<z-boot-dependencies.version>`，
且模块里所有 `io.github.yuku123` 依赖都自带版本号），所以 BOM 那个对外失效的缺陷**从来没打到本模块**——
这也是为什么修完缺陷后这里只需跟版、不需要改判据。

> 这份 IT 验的是"**发布件里聚合关系对不对**"，不验 jar 里有没有 class、也不验 property 抬的版本
> 有没有真的进入发布件（那要 `dependency:tree` + 发版）。上面「已发布到 Maven Central」那段的
> 84 构件字节普查（`~/.cache/zboot-1016/census2.py`，分母取本机 staging 目录、不敲清单）也**不在 IT 里**，
> 每轮发版手工跑一次。

---

## 📚 详细文档

- [三层架构与职责边界](https://github.com/z-opc-foundation/z-opc-foundation-lead/blob/main/001_项目认知/002_z系列架构与职责边界.md)
- [L3 中间件聚合 starter 矩阵](https://github.com/z-opc-foundation/z-opc-foundation-lead/blob/main/001_项目认知/002_z系列架构与职责边界.md#l3-中间件聚合-starter-矩阵)
- [踩坑记录 / Maven Central 发布](https://github.com/z-opc-foundation/z-opc-foundation-lead/blob/main/003_辅助能力/踩坑记录/Maven_Central_发布踩坑记录.md)
- [Maven Central 发布实战指南](https://github.com/z-opc-foundation/z-opc-foundation-lead/blob/main/003_辅助能力/maven-central-publish/references/中央仓库发布实战指南.md)

---

## 🤝 贡献

```bash
mvn clean verify -Pcentral   # 编译 + 测试 + 准备发布
bash deploy_maven_center.sh publish   # 发到 Maven Central
```

新加 starter 时（1.0.19 起的拓扑）：
1. 在 `z-boot-integration-starters/` 下建目录
2. 写 `pom.xml`：`<parent>` 指 `z-boot-integration-starters` 且**版本写字面量**（不再有 `${revision}`），
   自己那份 `<version>` 同样写字面量；`<dependencyManagement>` 里并列 import
   `z-boot-dependencies` + `z-boot-fleet`（都写字面版本），依赖 L3 坐标**不写 version**，由 fleet 下发
3. 新 L3 仓的版本格加进 `_doc/003_script/gen_fleet_bom.py` 的 `FAMILIES` 表，`--write` 重算 fleet
   （脚本会先打 repo1 确认那个版本真的活着）+ 在 `z-boot-integration-starters/pom.xml` 加 `<module>`
4. `mvn -o -B package` 验反应堆，再用 `dependency:tree` 从 **stdout** 读实际落到的 L3 版本
   （**不要** `mvn install`：那会把本机 m2 里的 z-boot 覆盖成未发布版本，
   下游/本机后续构建就分叉于已发布构件——这条踩过。⚠ fleet 例外：它必须 `install` 过一次，
   反应堆外的解析才认它，所以本机那份 `~/.m2` 副本发版后要拿 `.sha1` 跟 repo1 对一遍）
5. `bash _doc/003_script/deploy_maven_center.sh publish integration`（parent 未发时脚本自动前置）
6. 发完逐个 curl repo1 回读：`.pom` 200 **且**正文里那条 L3 坐标的版本号是新的
   （starter 的 pom 是 flatten 过的，property 已展开成字面量，光看 200 验不出版本。
   ⚠ repo1 对 HEAD 不给 200，探活要用 `curl -r 0-0`）

> `.scripts/gen_z_boot_starters.py`（工作区脚本，不在本仓 git 里）**已退役**：模板把 parent/自身版本写死成
> `1.0.1`、缺 licenses/developers/scm、还把 L3 版本内联成字面量，且只覆盖 8 个 starter
> （脚本里出现的 `z-boot-*-starter` 名去重后是 9 个，其中 `z-boot-integration-starter` 不是模块名，
> 真落盘过的只有 cache/graph/gw/kb/mq/oss/rpc/vector 八个——对照现在 20 个集成模块就是 8/20）——
> 重跑会把 8 个 starter 的 pom 打回 2026-08 的骨架。脚本里已加 `RETIRED` 守卫（实测 `rc=2`、不写盘）。

---

## 📄 许可证

[MIT License](LICENSE)

---

## 🔗 相关项目

| 项目 | 关系 |
|---|---|
| [z-cache](https://github.com/z-opc-foundation/z-cache) | 被 z-boot-cache-starter 聚合 |
| [z-mq](https://github.com/z-opc-foundation/z-mq) | 被 z-boot-mq-starter 聚合 |
| [z-gw](https://github.com/z-opc-foundation/z-gw) | 被 z-boot-gw-starter 聚合 |
| [z-kb](https://github.com/z-opc-foundation/z-kb) | 被 z-boot-kb-starter 聚合 |
| [z-vector](https://github.com/z-opc-foundation/z-vector) | 被 z-boot-vector-starter 聚合 |
| [z-graph](https://github.com/z-opc-foundation/z-graph) | 被 z-boot-graph-starter 聚合 |
| [z-rpc](https://github.com/z-opc-foundation/z-rpc) | 被 z-boot-rpc-starter 聚合 |
| [z-oss](https://github.com/z-opc-foundation/z-oss) | 被 z-boot-oss-starter 聚合 |

> 这张表只有 8 行，而实际聚合的 L3 有 19 个（另有 z-config / z-ctc / z-llm / z-mcp / z-skill / z-agent /
> z-bot / z-agent-proxy / z-msg / z-schedule / z-script）。没把剩下 11 个的 GitHub 链接补上，是因为这些 URL 我没逐个
> 核实过存在性——宁缺不编。要看全量对照，看上面那张 19 行的表。

---

## 📮 联系

- GitHub Issues: 提交 bug / feature request
- Email: yuku123@users.noreply.github.com

## 模块结构

这一节以前抄了第二份目录树（停在"集成 starter (9 个)"、还带 `本地 16379` 这类没出处的端口），
和上面「🏗️ 项目结构」那份两次抬号都没同步 ⇒ 删掉，只留一份。
完整 26 条 active `<module>` + 一个未进反应堆的目录，见上面 [🏗️ 项目结构](#️-项目结构)。

## 用法

> ⚠ 这一段是防"版本号腐烂"的制度，不是装饰。2026-09-26 的整批腐烂（README 停在 1.0.2、lead 停在 1.0.9、
> pom 是当时的发布版）成因就是**同一段 XML 被抄了三份、抬版只改了一份**。
> ✅ **三份已收敛成一份真源 = 「🚀 5 分钟接入 · 方式一」**（CEO 2026-09-26 点头"执行这五项修改"之后做的）：
> 真源那份补成超集（多一行 `z-boot-mq-starter`，使被删的两份一个字都没丢），
> 「⚙️ 实用 Case · Case 1」和下面「### 业务方接入」两整块 XML 换成回指真源的链接。
> 实测效果：本文件行数 `4ed124a`=857 →（收敛这一笔）`1e6a5c8`=803 → 工作树现在 822
> （后面这 19 行是 pin 分叉声明加回来的，`git diff --numstat` = `19 0`，纯增行；`1526342`=840 是 1.0.16
> 那批文档收口的读数）——**这三个数各自钉一笔，别拿任何一个当"现状"，现状一律 `wc -l README.md` 现测**；
> 尺的判定分母 25 → **14 行**（收敛后仍围栏内 14 行、值只有一种
> `1.0.16`、STALE 0 ⇒ PASS，同一轮把第 24 行改成 `1.0.9` 的内存副本当场判出 STALE 1 ⇒ 尺有牙）。
> 留一条能跑的账兜底：`~/.cache/zboot-1016/readme-classify.py` —— 它从根 pom 读 `<revision>`
> （剥掉 XML 注释再读，见下方 ⚠），然后要求**代码围栏内每一行 `<version>X</version>` 都等于那个值**，
> 围栏外的提及只列出来不参与判定。
> ⚠ **别拿 `grep -c "<version>1\.0\.16</version>"` 当尺**：这个数本身会随示例增减而漂（今天就是 25 → 14），
> 而且 1.0.15 那轮的 26 里含「5 分钟接入」末尾那句 `<version>1.0.15</version>` 取证叙述——**别按行号去找它，
> 行号会随每次编辑漂**（它这轮就从第 63 行漂到第 68 行）， blanket sed 会把这段**历史测量**改坏
> （1.0.16 这轮就是这么差点丢掉的）。
> ⚠ 这把尺第一次跑判的是"所有示例都没跟上 `X.Y.Z`"——根 pom 第 10 行**注释里**就写着
> `<revision>X.Y.Z</revision>`，不剥注释量到的就是它。
> 对不上就是漏改了某一份——不用眼睛找，一条命令判红。

### 业务方接入 (推荐: 一次性引入 z-boot)

这段以前抄了第三份"完整接入 XML"（和上面「5 分钟接入 · 方式一」逐行同构），2026-09-26 删掉，
只留真源那一份：BOM import + 每个 starter 自带 `<version>`，形状见
[🚀 5 分钟接入](#-5-分钟接入)。要挑哪些 starter 看「z-boot\* 聚合 starter（19 个）」那张表。

### 全世界开发者 (外部, 一行 import 一个中间件)

```xml
<dependency>
    <groupId>io.github.yuku123</groupId>
    <artifactId>z-boot-cache-starter</artifactId>
    <version>1.0.17</version>
</dependency>
```

application.yml:

```yaml
z:
  cache:
    enabled: true
    host: localhost
    port: 6379
```

启动类加 `@SpringBootApplication` 即可——但**"即可"只对默认开的那几个成立**：
`zmq` / `zgw` / `zkb` / `z.rpc` / `z-msg` 是 `matchIfMissing=true`（import 就装配），
而 `z.cache` / `z.graph` / `z.config` / `z.llm` / `z.mcp` / `z.skill` / `z.agent` / `z.boot.ctc` 必须显式写
`enabled: true`。逐行对照见上面「z-boot-* 聚合 starter（19 个）」表的最后一列。

## L3 中间件聚合 starter 矩阵

矩阵只有一份，在上面 **「已发布到 Maven Central 的所有模块 → z-boot-* 聚合 starter（19 个）」** 那一节。
这里以前抄过一份副本（11 行、版本列停在 cache 1.0.2 / graph 1.0.1，还带 `默认端口` 列），
两次抬号都没同步它，所以删掉——第二份表只会制造第二个"看起来对"的数字。

## 历史

- **2026-08**: 从 z-opc monorepo 拆出, 独立为 z-opc-foundation 产品仓
- **2026-07 之前**: z-boot 是 z-opc 子模块 (`z-opc/z-boot/`)

## 与其他仓的关系

```
z-boot (本仓)              ← 版本权威 (BOM)
   ↑
   ├── import BOM 锁版本
   │
z-opc (主后端)              ← 消费者
   └── （已无 `z-opc/z-boot/` 目录；旧注释说"暂时保留 z-config/z-ctc/z-lc/z-mist/z-msg 业务 starter"已作废——
       实测它们各自是 `z-opc-foundation/` 下的同级仓，z-opc 里剩下的 z-* 目录是业务域：
       z-agent / z-asset / z-ext / z-meta / z-opcs-bridge / z-product / z-qa / z-rpa / z-task / z-team / z-tool / z-trade）
```

**z-boot 不依赖任何 z-opc 业务模块**。版本由 z-boot 锁定。

> ⚠ "消费者 import BOM 就拿到全部约束"这句**只对钉字面版本的那批第三方成立**：repo1 的
> `z-boot-dependencies-1.0.15.pom` 里 `io.github.yuku123` 坐标**一共只有 3 条**
> （逐条解析 `<dependencyManagement>` 得到：`z-graph-api` / `z-graph-core` / `z-graph-protocol`，
> 连 `z-graph-spring-boot-starter` 都不在——早先这里写过"四个坐标"，那是把 pom **注释里**
> 解释"为什么不放 starter"的那一行当成了坐标）。**1.0.15 及之前**这三条的版本还是 `${z-graph.version}`
> 占位符、对外部 import 者**一条都落不下来**；**1.0.16 起落得下来**（发布出去的父 pom 带上了
> `<properties>`，实测：只 import 该 BOM 的干净 pom 里无版本声明 `z-graph-api` ⇒ 解析出 1.0.5，
> 且有 `ZBootBomExternalResolutionIT` 常驻钉住），机制与取证见上面「第三方版本权威（BOM）」。
> 其余 z-* 版本钉在 `z-boot-integration-starters` 的 `<dependencyManagement>` 里，
> 只有走 `z-boot-*-starter` 聚合的消费者才继承得到。直接在 pom 里写 `io.github.yuku123:z-cache-*`
> 而不引聚合 starter 的模块，BOM 不会给它任何版本约束。

## 发布

一键脚本在仓内：`_doc/003_script/deploy_maven_center.sh`（凭证读 `.env`，密钥环 `./.gnupg`，两者都被 `.gitignore` 排除）。

```bash
./_doc/003_script/deploy_maven_center.sh readme                # 摘要：前置 + 文件夹语义 + 判据
./_doc/003_script/deploy_maven_center.sh publish --dry fleet    # 只 mvn verify：编译+sources+javadoc+gpg 签名，不打包不上传
./_doc/003_script/deploy_maven_center.sh publish --bundle fleet # bundle 演练：连打包都跑，只把上传目标指到不可达域名
./_doc/003_script/deploy_maven_center.sh bundle <folder>/target/central-publishing/central-bundle.zip  # 逐坐标点件
python3 _doc/003_script/central_pom_scan.py                # 上传前静态点伤，一次扫 ../ 下所有带 central profile 的仓
./_doc/003_script/deploy_maven_center.sh publish fleet          # 只发一个文件夹（脚本会在当版 root 未上线时自动前置）
./_doc/003_script/deploy_maven_center.sh publish                # 按序全发 root→deps→fleet→parent→starter→integration
```

1.0.19 起**发布粒度 = 文件夹**：脚本按 `FLEET_ORDER` 逐文件夹 `mvn -f <folder>/pom.xml deploy -Pcentral`，
每个文件夹先回读 repo1，**同版本已上线就跳过**（Central 不允许覆盖，硬重发只会 400）；如果你只发子文件夹
而当版 parent 还没上线，脚本自动把 parent 前置。日志 `/tmp/z-boot-deploy-<folder>.log`。

`--dry` 到 verify 为止，**看不出 bundle 里到底装了什么**：pom-only 模块少件、`*-admin` 这类"永不发布"的模块
混进包里，都只在打包那步现形 —— 所以有 `--bundle`：staging/签名/打包全按发布态真跑，只把 `centralBaseUrl`
指到解析不了的域名，于是一件都发不出去，但包内容可以逐坐标点清楚。`--bundle` 现在自带点件
（`bundle_audit`：每个坐标要 `pom + jar + -sources.jar + -javadoc.jar` 四件齐、各自带 `.asc`，pom-packaging
只要 pom），缺任意一件直接 `rc=1`；拿到别人的包也能点，用 `bundle <zip>` 子命令。动过 flatten 配置、
`excludeArtifacts` 或新加文件夹时先走一遍它（2026-09-28 就是这么验掉 z-ctc 的 `z-ctc-admin` 排除生效的：
102 个文件里 admin 命中 0；integration 演练 21 个坐标 0 缺件）。

⚠ **`maven.deploy.skip` 拦不住 Central** —— `central-publishing-maven-plugin` 不认这个属性，实测照样把
admin 的 pom/jar/exec fat jar 全打进 bundle。要挡只能用插件自己的 `excludeArtifacts`（按 artifactId 精确匹配）。

`central_pom_scan.py` 是上面两类事故的**上传前**版本：静态扫 `../` 下每个带 `central profile` 的仓，报四类
—— B `deploy.skip=true` 却没进 `excludeArtifacts`、C 发布的 pom 缺自己的 `<name>`、D `dependencyManagement`
条目无 `version`、E 插件无 `version` 且父链无兜底。它按 Maven 口径解析 `<modules>`（注释掉的 module 不算，
`z-config-admin` / `z-oss/_frontend` / `z-gw-examples` 这些"目录在、reactor 不在"的不会误报），根 pom 无
`<modules>` 的 z-boot 文件夹拓扑单独认。实测口径：25 仓 / 0 缺陷；正负双向都验过（造一个缺 javadoc.jar
和一个 `.asc` 的包，两处缺口都报出且 `rc=1`）。

抬一格兄弟仓 L3 版本的完整动作只有三条命令：`gen_fleet_bom.py --write` → `publish --dry fleet` → `publish fleet`。
以前这件事要重发整个 z-boot（27 个坐标），因为版本格住在根 pom 的 `<properties>`、经
`z-boot-integration-starters` 的 36 行 `<dependencyManagement>` 下发。
`--write` 现在带守卫：只要有格在 repo1 上还取不到（PENDING），就拒绝落盘并 exit 2 —— 把不存在的版本钉进
BOM 是"烧格子"，Central 不许覆盖，只能靠抬版本号重发来收拾（`--allow-pending` 才放行）。

**上传成功 ≠ 收下**：`Uploaded bundle successfully … will publish automatically` 之后 Central 还要异步校验整批
组件，任何一个 pom 不合格整批 FAILED，而 mvn 侧早就 BUILD SUCCESS 了（z-ctc 1.0.2 就是这么挂了 2.5 小时：
repo1 一直 404，实际 17:36 那批已判 FAILED，错误只有一行 `Project name is missing` 挂在 `z-ctc-admin` 上）。
查法：

```bash
curl -u "$CENTRAL_USERNAME:$CENTRAL_TOKEN" \
  'https://central.sonatype.com/api/v1/publisher/deployments?page=1&size=5'
# 逐件看 deploymentState / deploymentComponents[].errors
```

这份清单有一小时量级的滞后（刚发的那几条不在里面），`/publisher/status?key=` 实测一律返 500，别指望它。
最终判据还是 repo1 回读。

（以前这里写的 `lead/003_辅助能力/maven-central-publish` skill 和 `z-util/发布指引.md` 都不是仓内可依赖的入口：
后者 `find` 零命中，前者是另一台机器的文档。发布手册从此以本脚本 + 本节为准。）


## 文档目录

本项目文档统一收口在 `_doc/` 下:

- [`_doc/001_arch/`](_doc/001_arch/) — 架构文档 (项目总览 / 模块结构 / 接口清单 / DB schema / 前端 / 能力 / roadmap):
  - [`AGENTS.md`](_doc/001_arch/AGENTS.md)

- [`_doc/003_script/`](_doc/003_script/) — 运维脚本:
  - [`batch_fix_zboot_meta.py`](_doc/003_script/batch_fix_zboot_meta.py)
  - [`central_pom_scan.py`](_doc/003_script/central_pom_scan.py) — 上传前静态点伤（`../` 全仓 B/C/D/E 四类，非 0 就有缺陷）
  - [`deploy_maven_center.sh`](_doc/003_script/deploy_maven_center.sh) — 按文件夹发布（`publish fleet` 等）+ `bundle <zip>` 逐坐标点件
  - [`gen_fleet_bom.py`](_doc/003_script/gen_fleet_bom.py) — `z-boot-fleet` 的生成器 + 对账尺（兄弟仓 pom × repo1 实测 → 163 条受管项；`--parent` / `--write-parent` 维护 `z-boot-parent` 里那段 z-boot 自家 starter 清单）
  - [`repo1_census.py`](_doc/003_script/repo1_census.py) — 逐坐标点 repo1 的 4 件套（只认 repo1，不回退 `~/.m2`）；"半发/漏件"用它抓，`--repo ../z-xxx` 可点任意仓
  - [`install-settings.sh`](_doc/003_script/install-settings.sh)

各文档详细说明见各子目录。
