# z-boot

> **Spring Boot Starter 聚合仓 + 第三方依赖版本权威 (BOM)**
> 把所有 z-* L3 中间件 + 通用 starter 收成"开箱即用"系列, 业务模块一行 import 一个能力

[![Maven Central](https://img.shields.io/badge/Maven%20Central-1.0.15-blue?logo=apache-maven)](https://central.sonatype.com/search?q=g:io.github.yuku123+a:z-boot*)
[![License](https://img.shields.io/license/MIT-green)](LICENSE)
[![Java](https://img.shields.io/badge/Java-8%2B-orange)](https://openjdk.org)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-2.7.x-6DB33F)](https://spring.io)

---

## 🚀 5 分钟接入

### 方式一：业务模块（推荐, 一次性 import 全部能力）

```xml
<!-- 1. 引入 z-boot-dependencies BOM —— 它只锁第三方版本 -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>io.github.yuku123</groupId>
            <artifactId>z-boot-dependencies</artifactId>
            <version>1.0.16</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<!-- 2. 引入 starter —— version 必须自己写，BOM 不管理 z-boot-* 坐标 -->
<dependencies>
    <!-- 基础能力 -->
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-web-starter</artifactId>
        <version>1.0.16</version>
    </dependency>
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-datasource-starter</artifactId>
        <version>1.0.16</version>
    </dependency>

    <!-- L3 中间件 (一行 import 一个) -->
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-cache-starter</artifactId>
        <version>1.0.16</version>
    </dependency>
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-rpc-starter</artifactId>
        <version>1.0.16</version>
    </dependency>
</dependencies>
```

> ⚠ **"starter 不写 version、由 BOM 锁"这条是错的，实测证伪**（2026-09-26 在 **1.0.15** 发布件上复测）：
> 拿一个只 import `z-boot-dependencies:1.0.15` 的干净 pom 声明无版本的 `z-boot-web-starter`，
> Maven 直接拒绝读项目 ——
> `'dependencies.dependency.version' for io.github.yuku123:z-boot-web-starter:jar is missing`；
> 同一份 pom 补上 `<version>1.0.15</version>` 才 `BUILD SUCCESS`（树里读到 `z-boot-web-starter:jar:1.0.15:compile`）。
> 原因见下面「第三方版本权威（BOM）」：这份 BOM 里 `z-boot-*` 坐标 **0 条**。
> 现网消费者（如 `z-opc/pom.xml:455-458`）也正是自己钉 `<version>` 的。

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
    <version>1.0.16</version>
</dependency>
```

---

## 📦 已发布到 Maven Central 的所有模块

> groupId: `io.github.yuku123` · 最新 release: **1.0.15**（2026-09-26 19:52 上传，20:04:53 repo1 可见）· 共 **27 个坐标**
> （2026-09-26 逐个 curl repo1：`27/27 .pom = 200`；**23 个 jar 模块**的 `.jar.md5` 与本机
> `target/central-staging/**/*-1.0.15.jar` 实测 md5 `23/23 相同、0 不一致`——阳性对照拿 1.0.14 的
> md5 去比 1.0.15 的本地 jar，尺当场判"不同"，所以那 23 个"相同"不是空跑。
> 计数 = 全仓 26 条 active `<module>`（根 3 + `z-boot-starter` 3 + `z-boot-integration-starters` 20）
> + 顶层 `z-boot` 自身，其中 `z-boot` / `z-boot-starter` / `z-boot-integration-starters`
> / `z-boot-dependencies` 4 个是 pom-only，所以 jar 数 = 27 − 4 = 23）

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

> **版本列不是手抄的**：真源是 `z-boot/pom.xml` 里的 `<z-*.version>` property（经
> `z-boot-integration-starters/pom.xml` 的 `<dependencyManagement>` 下发给每个 `z-boot-*-starter`）。
> 升级改 property，这张表只是 2026-09-26 从 property 抄下来的一次快照。
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
| `z-boot-config-starter` | z-config-spring-boot-starter | `${z-config.version}` = 1.0.7 | `z.config.enabled=true`，无 matchIfMissing ⇒ 默认关 |
| `z-boot-cache-starter` | z-cache-spring-boot-starter | `${z-cache.version}` = 1.3.1 | `z.cache.enabled=true`，默认关 |
| `z-boot-mq-starter` | z-mq-spring-boot-starter | `${z-mq.version}` = 1.2.0 | **`zmq.enabled`**（前缀无点），`matchIfMissing=true` ⇒ 默认开 |
| `z-boot-gw-starter` | z-gw-spring-boot-starter | `${z-gw.version}` = 1.0.1 | **`zgw.enabled`**，默认开 |
| `z-boot-kb-starter` | z-kb-spring-boot-starter | `${z-kb.version}` = 1.0.2 | **`zkb.enabled`**，默认开 |
| `z-boot-vector-starter` | z-vector-spring-boot-starter | `${z-vector.version}` = 1.0.1 | **`zvector.server.auto-start`**，没有 `z.vector.enabled` 这个键 |
| `z-boot-graph-starter` | z-graph-spring-boot-starter | `${z-graph.version}` = 1.0.5 | `z.graph.enabled=true`，默认关 |
| `z-boot-rpc-starter` | z-rpc-spring-boot-starter | `${z-rpc.version}` = 1.0.2 | `z.rpc.enabled`，`matchIfMissing=true` ⇒ 默认开 |
| `z-boot-oss-starter` | z-oss-common | `${z-oss.version}` = 1.0.2 | 按 **`oss.provider`** 分支（`local` 为 matchIfMissing），没有 enabled 开关 |
| `z-boot-schedule-starter` | z-schedule-spring-boot-starter | `${z-schedule.version}` = 1.0.4 | 按 **`z.base.db.schedule.disabled=false`** 反向开关，没有 `z.schedule.enabled` |
| `z-boot-msg-starter` | z-msg-web | `${z-msg.version}` = 1.2.0（**仓内 property**；repo1 的 1.0.15 发布件实测仍是 1.1.0，见下方注） | **`z-msg.enabled`**（连字符不是点），默认开 |
| `z-boot-ctc-starter` | z-ctc-sso | `${z-ctc.version}` = 1.0.1 | **`z.boot.ctc.enabled=true`**（开关在 z-boot 这层，不在 L3；`ZBootCtcAutoConfiguration:27`），默认关 |
| `z-boot-llm-starter` | z-llm-starter | `${z-llm.version}` = 0.1.4 | `z.llm.enabled=true`，默认关 |
| `z-boot-mcp-starter` | z-mcp-starter | `${z-mcp.version}` = 0.1.2 | `z.mcp.enabled=true`，`matchIfMissing=false` ⇒ 默认关 |
| `z-boot-skill-starter` | z-skill-starter | `${z-skill.version}` = 0.1.2 | `z.skill.enabled=true`，默认关 |
| `z-boot-agent-starter` | z-agent-starter | `${z-agent.version}` = 0.1.2 | `z.agent.enabled=true`，默认关 |
| `z-boot-bot-starter` | z-bot-core | `${z-bot.version}` = 0.1.0 | 无开关（L3 全仓 `@ConditionalOnProperty` 0 命中） |
| `z-boot-agent-proxy-starter` | z-agent-proxy | `${z-agent-proxy.version}` = 0.1.0 | 无开关（同上） |
| `z-boot-script-starter` | z-script-web | `${z-script.version}` = 1.0.0 | 无开关（z-boot 侧 0 个 `@ConditionalOnProperty`；实体装配在 z-script-web 自己的 `spring.factories` → `ZScriptWebAutoConfiguration`）。1.0.15 才进反应堆，宿主前置：MySQL 建过 z-script 的 `_doc/002_deploy/init.sql`、数据源键写 `z.base.db.script.*`（写 `spring.datasource.*` 会静默回落 localhost/root） |

> **这一列的版本号已经在对外发布件里了，不只是仓内 property**：2026-09-26 逐个 curl repo1 上
> `z-boot-*-starter-1.0.15.pom`（flatten 已把 property 展开成字面量），19/19 抽出的
> `io.github.yuku123` 直接依赖与本表"聚合的 L3 坐标 + 版本"两列逐格一致
> （量具：`~/.cache/zboot-1015/published-aggregate-table.sh`）。上一版这条对不上的是 `z-msg`
> （property 抬了但 1.0.14 发布件里还是 1.0.0）和 `z-llm`——两处都在 1.0.15 兑现了。
>
> ⚠ **这条"表格 == 发布件"的等式现在对 z-msg 一格重新失效，且是故意的**：2026-09-26 21:11 把根 pom 的
> `<z-msg.version>` 抬到 1.2.0 后，实测是 **18/19 一致 + 1 格已知分叉** —— repo1 的
> `z-boot-msg-starter-1.0.15.pom` 仍写 `z-msg-web:1.1.0`（21:12 curl，`1.0.16` 404，
> `maven-metadata.xml` 的 `<version>` 列表停在 1.0.15）。仓内这一侧量过：`mvn -o -pl
> z-boot-integration-starters/z-boot-msg-starter -am package` 生成的 `.flattened-pom.xml` 里是字面量
> `1.2.0`，`dependency:tree` 解析出 `z-msg-web:jar:1.2.0 → z-msg-core:jar:1.2.0 → z-msg-api:jar:1.2.0`。
> 所以分叉只能靠**发 1.0.16** 收掉，改表格文字收不掉它。
>
> ⚠ **反向的账：19 个 pin 里原本有 6 个落后于 Central 的 `<latest>`**（2026-09-26 逐个读
> `<artifact>/maven-metadata.xml`，13 个 SAME / 6 个 LAG / 0 个读不到）：
> z-config 1.0.7→**1.0.8**、z-cache 1.3.1→**1.3.5**、z-mq 1.2.0→**1.2.1**、
> z-gw 1.0.1→**1.0.3**、z-vector 1.0.1→**1.0.3**、z-msg 1.1.0→**1.2.0**。
> 其中 `z-msg` 那一格已在 09-26 21:11 抬到 1.2.0（仓内），所以这份清单只剩 5 格待判。
> "落后"不等于"该抬"——每个 L3 的新版是否可用要按各仓的回归判，别照 `<latest>` 盲抬；
> 但这张表从此有了一个能自动跑的对账尺，抬号前拿它量一遍就行。

### BOM (1 个)

| 模块 | 说明 |
|---|---|
| `z-boot-dependencies` | 第三方依赖版本权威（spring-boot-dependencies 2.7.12 + jackson-databind 2.18.6 + druid 1.2.23 + log4j-core 2.25.4，共 133 条受管依赖 / 1011 行；repo1 上的 1.0.15 发布件也是 1011 行——BOM 用 `resolveCiFriendliesOnly` 模式，`<dependencyManagement>` 原样保留）|

### 聚合 POM (3 个)

- `z-boot`（顶层聚合）
- `z-boot-starter`（基础 starter 聚合）
- `z-boot-integration-starters`（集成 + L3 聚合 starter 聚合）

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
- ✅ **L3 版本统一由 `z-boot/pom.xml` 的 `<z-*.version>` property 管理**——改版本只改 property 一处，
  `z-boot-integration-starters/pom.xml` 的 `<dependencyManagement>` 全部写成 `${z-*.version}`
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

### 第三方版本权威（BOM）
- ✅ **z-boot-dependencies** 锁的是**第三方**版本，不是 z-* 的版本锁入口
  （实测：BOM 的 `<dependencyManagement>` 里 `z-boot-*` 坐标 **0 条**，见上面「5 分钟接入」的 ⚠）
- ✅ **1011 行 / 133 条受管依赖**（2026-09-26 在 **repo1 的 1.0.15 发布件**上逐条解析
  `<dependencyManagement>` 得到的分解）：**115 条钉的是字面版本** + **14 条钉的是 `${...}` property**
  + 2 条 `scope=import`。内容如 spring-boot-dependencies 2.7.12 / jackson-databind 2.18.6 /
  mybatis-plus 3.5.7 / druid 1.2.23 / log4j2 2.25.4 / commons-lang3 3.18.0
- ⚠ **那 14 条 `${...}` 对外部 import 者是失效的**（不是"看起来失效"，是空仓跑出来的）：
  拿一个只 import `z-boot-dependencies:1.0.14` 的干净 pom、无版本声明 `io.github.yuku123:z-graph-api`
  ⇒ Maven 当场拒读，`'dependencies.dependency.version' for io.github.yuku123:z-graph-api:jar is missing`；
  同一支 pom 把坐标换成钉字面版本的 `org.springframework.boot:spring-boot-configuration-processor`
  ⇒ 正常解析出 2.7.12、`BUILD SUCCESS`（阳性对照，证明不是网/量具的错）。
  14 条是：`log4j-to-slf4j`、`mybatis-plus-{boot-starter,extension,core,generator}`、
  `dynamic-datasource-spring-boot-starter`、`jsqlparser`、`ojdbc6`、`mybatis-spring-boot-starter`、
  `mybatis-spring`、`mybatis`、`z-graph-{api,core,protocol}`。
  成因是发布机制不是笔误：BOM 用 `resolveCiFriendliesOnly`（flatten 文档原话——该模式
  "keep the dependencyManagement **as-is** without resolving parent influences"，占位符原样留着，
  指望父 pom 给出 property），而根 pom 用 `oss` 模式发布成 37 行、**不含 `<properties>`** ⇒ 链条断在中间。
  已试过的路都不成立（实测）：`flattenMode=bom` 会把 `<parent>` 剥掉、占位符一条不归零；
  `<pomElements><dependencyManagement>interpolate</...>` 构建成功但 14 条占位符**依旧在**；
  写 `resolved` 连构建都进不去——`ElementHandling` 的合法取值实测只有
  `flatten / expand / resolve / interpolate / extended_interpolate / keep / remove`（`javap` 读 Enum），
  连 `resolveCiFriendliesOnly` 之外想要"占位符归零但不吞 import"这一档，插件里没有现成档可用。
  ⇒ 要修得动发布机制本身，且 Central 构件不可变（1.0.11–1.0.15 都是这个行为），**未擅自改，等裁定**。
  影响面先说清楚：这 14 条里的 13 条是第三方，走 `z-boot-*-starter` 聚合的消费者不受影响
  （starter 的 pom 是 `oss` 模式、版本已折成字面量）；真正拿不到约束的只有"直接 import BOM
  又自己声明这些坐标、且不写 version"的写法。
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
  （`z-boot-script-starter` 已经在 1.0.15 补进反应堆并发布，见下面目录树的 ⚠）
- ✅ **可独立发布到 Maven Central**——`<revision>` 1.0.15，repo1 实测 27 个坐标的 `.pom` 全 200、
  23 个 jar 的 `.jar.md5` 与本机 staging 逐字节相同

---

## ⚙️ 实用 Case（生产场景）

### Case 1: 业务方全栈（一行 import 一个能力）

```xml
<!-- 引入 z-boot BOM -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>io.github.yuku123</groupId>
            <artifactId>z-boot-dependencies</artifactId>
            <version>1.0.16</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependencies>
    <!-- Web + DB -->
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-web-starter</artifactId><version>1.0.16</version></dependency>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-datasource-starter</artifactId><version>1.0.16</version></dependency>

    <!-- 中间件 (一行一个) -->
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-cache-starter</artifactId><version>1.0.16</version></dependency>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-mq-starter</artifactId><version>1.0.16</version></dependency>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-rpc-starter</artifactId><version>1.0.16</version></dependency>
</dependencies>
```

### Case 2: 单独用某个 starter（外部开发者）

```xml
<!-- 我只要 z-cache 客户端, 不要全套 -->
<dependency>
    <groupId>io.github.yuku123</groupId>
    <artifactId>z-boot-cache-starter</artifactId>
    <version>1.0.16</version>
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
            <version>1.0.16</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

### Case 4: 通过 z-boot-* 启动 RAG 知识库

```xml
<dependencies>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-web-starter</artifactId><version>1.0.16</version></dependency>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-kb-starter</artifactId><version>1.0.16</version></dependency>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-vector-starter</artifactId><version>1.0.16</version></dependency>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-cache-starter</artifactId><version>1.0.16</version></dependency>
</dependencies>
```

---

## 🏗️ 项目结构

```
z-boot/
├── pom.xml                          # 自给自足 parent (Central namespace)
├── z-boot-dependencies/             # 第三方版本 BOM (1011 行 / 133 条受管依赖)
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

> 上面这棵树和 `z-boot-integration-starters/pom.xml` 的 active `<module>` 是**逐名对过账的**
> （脚本：剥掉 XML 注释后取 `<module>`，与树里的名字求差集 ⇒ 双向 0 差）。对不上是迟早的事，
> 所以判据留在仓外、不靠眼睛。

> ⚠ 目录里还剩 **一个**没有进 `<modules>` 的 starter：`z-tool-webide-spring-boot-starter`。
> 不是"没排上队"，是**补进去会让整个 reactor 读不起 pom**（`mvn -B package` rc=1，Maven 自己数出来
> `has 5 errors`；5 条原文按形状抄在 `z-boot-integration-starters/pom.xml:46-52` 的注释里）：
> 它的 `<parent>` 写死 `1.0.1`（不吃 `${revision}`）、
> `<groupId>` 还在 `com.zifang` 命名空间且 4 条依赖无版本。
> 要发它得先做两件事：把 `z-tool-webide-{docker,api,common}` 发到 Central、并把坐标迁到 `io.github.yuku123`。
> （另一条 `z-boot-script-starter` 的排除理由 2026-09-26 实测是假的——空仓
> `dependency:resolve io.github.yuku123:z-script-web:1.0.0` `BUILD SUCCESS`、落地 16 个
> `io.github.yuku123` jar（其中 z-script 自己的三个坐标 core/engine/web 都在），所以 1.0.15 已补进
> `<modules>` 并发布。）

---

## 🔧 高级

### 升级 z-boot / L3 中间件版本

改 `z-boot/pom.xml` 的 `<z-*.version>` property 一处（`z-boot-integration-starters` 的
`<dependencyManagement>` 全部写成 `${z-*.version}`，所以只有 property 是真源）：

```xml
<!-- z-boot/pom.xml -->
<properties>
    <z-cache.version>1.3.1</z-cache.version>   <!-- ← 改这一行 = 只换 z-boot-cache-starter 一个 starter 的 L3 版本 -->
    <z-graph.version>1.0.5</z-graph.version>   <!--    graph 特殊：BOM 里那 3 个引擎坐标也吃这个 property
                                                    （但只对**仓内**生效——发布件里它是 `${...}` 占位符，
                                                    见上面「第三方版本权威（BOM）」的 ⚠） -->
    ...
</properties>
```

> 别指望"改 property 一处"就对外生效：property 只影响**下一次构建**，业务方拿到的是
> `z-boot-*-starter` 发布件 pom 里**已经展开成字面量**的版本号。抬完 property 必须发一版
> z-boot（`<revision>` +1），否则 repo1 上的旧 starter 依旧引旧 L3。
> 2026-09-26 这条正反两面都量过：`${z-msg.version}` 抬到 1.1.0 之后、1.0.15 发布**之前**，
> repo1 上 1.0.14 的 `z-boot-msg-starter.pom` 里读到的还是 `z-msg-web:1.0.0`；
> 1.0.15 上线后同一处 curl 回读 = **1.1.0**（19/19 个 starter 的发布件都按这条对过账，见上面那张表下面那段）。

发一版 z-boot 之后，业务方只改 `<z-boot.version>` 一处就能整批换 L3 版本；
L1 业务模块的第三方版本锁则来自 import `z-boot-dependencies`（同 `<revision>`）。

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

`z-opc/z-middleware-integration-test` → `ZBootAggregatorStarterMavenCentralPullIT`
（2026-09-26 20:43 本机跑绿：`Tests run: 4, Failures: 0, Errors: 0, Skipped: 0`，22.40 s）：

- **19 个 z-boot-* 聚合 starter @ 1.0.15**：逐个拉 `.pom`，HTTP 200 **且**发布件正文里必须出现上表对应的那一个
  L3 坐标（`<artifactId>z-cache-spring-boot-starter</artifactId>` 整串匹配）。
  以前只断言"pom 拉得到"、且只覆盖 10 个 ⇒ 现在 19 行全覆盖，第二列从此不能手填。
- **这张表怎么来的**：不手抄。机械抽取每个 `z-boot-*-starter/pom.xml` 里 `io.github.yuku123` 的**直接**
  依赖（先剥 XML 注释、再剥 `<dependencyManagement>`）⇒ 20 条 active `<module>` 里 19 条有 ≥1 个 z-* 依赖，
  只有 `z-boot-jackson-starter` 是 0 个（所以它不在表里）。
- **表自证**：行数必须等于 19、artifactId 不许重复（重复 = 某个 starter 静默失去覆盖）。
  三支变异实测（每次注入前先 `cp` 具名备份、还原只从备份 `cp`，两边 md5 都是 `a74ccbe3fd7c0c0f88ee6c2cb92df2ee`）：
  1. `AGGREGATOR_COUNT` 改 18 ⇒ `EXPECTED_AGGREGATORS 应该有 18 行 … expected: <18> but was: <19>`
  2. 复制 cache 行**并把 count 一起改成 20**（否则长度守卫先红，重复守卫根本测不到）⇒
     `有重复 artifactId, 对应 starter 没被真正覆盖: [z-boot-cache-starter]`
  3. `VERSION` 改成从未发布的 1.0.16 ⇒ 19 条 URL 全 404，`Tests run: 4, Failures: 1, Errors: 1`
     （那支 Error 是抽样测试读不到流）。本机 m2 里也只有 1.0.1–1.0.15、没有 1.0.16，且这测试拼的是
     字面 `https://repo1.maven.org/...` URL ⇒ 404 只可能来自 repo1，不是本地仓库的回声
- 命名约定校验 ✅（19 个都符合 `z-boot-{pkg}-starter`、无 `--`）
- `z-boot-cache-starter` pom 抽样：确认引用 `z-cache-spring-boot-starter` 且 groupId 是 `io.github.yuku123` ✅

⚠ **跑法**：`z-middleware-integration-test` **不在** `z-opc/pom.xml` 的 `<modules>` 里（实测全仓
`grep -rn z-middleware-integration-test --include=pom.xml .` 只有它自己 pom 的 4 处自引用），
所以 `mvn -pl z-middleware-integration-test` 当场 `Could not find the selected project in the reactor`，
必须 `mvn -f z-middleware-integration-test/pom.xml test`。

⚠ **整模块 52 例里有 20 例是关着的**：6 个类级 `@EnabledIfEnvironmentVariable` 开关
（`RUN_ZCACHE_IT` / `RUN_ZMQ_IT` / `RUN_ZOSS_CENTRAL_IT` / `RUN_ZRPC_CENTRAL_IT` /
`RUN_ZWF_CENTRAL_IT` / `RUN_ZWF_RPC_IT`）默认不给值 ⇒ `BUILD SUCCESS` 不等于那些 L3 被验过。

**本轮顺带修掉一格常红**（不是本次抬号引入的）：`ZConfigMavenCentralPullIT` 的 `VERSION` 停在 **1.0.0**，
而 1.0.0 从未发布到 Central —— 实测四坐标 × {1.0.0, 1.0.1, 1.0.2, 1.0.4, 1.0.7, 1.0.8} = 24 次 curl，
1.0.0 那 4 次全 404、其余 20 次全 200。改成该模块 `pom.xml` 自己钉的 1.0.7 后：整模块从
`52, Failures: 1, Errors: 1, Skipped: 20`（20:36:07）变 `52 / 0 / 0 / 20`（20:38:46），逐类 tally
**只有 ZConfig 那一行变**（其余 10 行逐字节同）。

**同时把该模块的 `<z-boot.version>` 1.0.14 → 1.0.15**：抬号前逐个比了发布件，本模块消费的 7 个 starter
的 pom 在两版之间只差版本字面量、其余逐字节同；`dependency:tree` 两版各 250 行，diff 恰好只有那 7 行
⇒ 对解析出来的依赖树是 no-op（抬号前后两次整模块逐类 tally md5 同为 `c551dffe3c9173c506814b21554add74`）。

> 这份 IT 验的是"**发布件里聚合关系对不对**"，不验 jar 里有没有 class、也不验 property 抬的版本
> 有没有真的进入发布件（那要 `dependency:tree` + 发版）。上面「项目结构」的 27 坐标 / 23 jar 普查
> 是 2026-09-26 手工 curl 的，不在 IT 里。

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

新加 starter 时：
1. 在 `z-boot-integration-starters/` 下建目录
2. 写 `pom.xml`（`<parent>` 指 `z-boot-integration-starters`，依赖 L3 坐标**不写 version**，
   由父 pom 的 `<dependencyManagement>` 从 `${z-*.version}` 下发）
3. 根 pom 加 `<z-xxx.version>` property + 在 `z-boot-integration-starters/pom.xml` 的
   `<dependencyManagement>` 加一条 `${z-xxx.version}` + 加 `<module>`
4. `mvn -o -B package` 验反应堆，再用 `dependency:tree` 从 **stdout** 读实际落到的 L3 版本
   （**不要** `mvn install`：那会把本机 m2 里的 z-boot 覆盖成未发布版本，
   下游/本机后续构建就分叉于已发布构件——这条踩过）
5. 升 `<revision>` + `bash deploy_maven_center.sh publish`
6. 发完逐个 curl repo1 回读：`.pom` 200 **且**正文里那条 L3 坐标的版本号是新的
   （starter 的 pom 是 flatten 过的，property 已展开成字面量，光看 200 验不出版本）

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

> ⚠ 本节与上面「🚀 5 分钟接入」「⚙️ 实用 Case」是**同一段 XML 的第三份副本**。
> 2026-09-26 的整批版本号腐烂（README 停在 1.0.2、lead 停在 1.0.9、pom 是当时的发布版）就是这么来的：
> 抬版时只改了一份。三份现在都是 1.0.15，但**权威那份是「5 分钟接入」**。
> 副本没法一次改到位，所以留一条能跑的账：**抬版后 `grep -c "<version>1\.0\.15</version>" README.md`
> 必须正好是 26**（2026-09-26 全仓实测的份数；换版本号时这个数字也要跟着重数一次）。
> 对不上就是漏改了某一份——不用眼睛找，一条命令判红。（把后两段直接删掉只留一份这件事仍等点头，不擅自动手。）

### 业务方接入 (推荐: 一次性引入 z-boot)

```xml
<!-- 1. 引入 z-boot-dependencies BOM (锁所有第三方版本) -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>io.github.yuku123</groupId>
            <artifactId>z-boot-dependencies</artifactId>
            <version>1.0.16</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<!-- 2. 引入需要的 starter (version 必须自己写 —— BOM 不管理 z-boot-* 坐标) -->
<dependencies>
    <!-- 基础能力 -->
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-web-starter</artifactId>
        <version>1.0.16</version>
    </dependency>
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-datasource-starter</artifactId>
        <version>1.0.16</version>
    </dependency>

    <!-- L3 中间件 (一行 import 集成, 不用自己再找 L3 starter) -->
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-cache-starter</artifactId>
        <version>1.0.16</version>
    </dependency>
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-mq-starter</artifactId>
        <version>1.0.16</version>
    </dependency>
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-rpc-starter</artifactId>
        <version>1.0.16</version>
    </dependency>
    <!-- ... 其他 5 个 z-boot-*-starter 按需 -->
</dependencies>
```

### 全世界开发者 (外部, 一行 import 一个中间件)

```xml
<dependency>
    <groupId>io.github.yuku123</groupId>
    <artifactId>z-boot-cache-starter</artifactId>
    <version>1.0.16</version>
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
> 解释"为什么不放 starter"的那一行当成了坐标），而且这三条的版本还是 `${z-graph.version}` 占位符，
> 对外部 import 者一条都落不下来（见上面「第三方版本权威（BOM）」的 ⚠）。
> 其余 z-* 版本钉在 `z-boot-integration-starters` 的 `<dependencyManagement>` 里，
> 只有走 `z-boot-*-starter` 聚合的消费者才继承得到。直接在 pom 里写 `io.github.yuku123:z-cache-*`
> 而不引聚合 starter 的模块，BOM 不会给它任何版本约束。

## 发布

通过 `lead/003_辅助能力/maven-central-publish` skill 一键发布到 Maven Central。
（以前这里写的 `z-util/发布指引.md` 是个死路径：`find z-util -name '*发布*'` 零命中，
`z-util/README.md` 是那个库自己的说明，不是发布手册。）


## 文档目录

本项目文档统一收口在 `_doc/` 下:

- [`_doc/001_arch/`](_doc/001_arch/) — 架构文档 (项目总览 / 模块结构 / 接口清单 / DB schema / 前端 / 能力 / roadmap):
  - [`AGENTS.md`](_doc/001_arch/AGENTS.md)

- [`_doc/003_script/`](_doc/003_script/) — 运维脚本:
  - [`batch_fix_zboot_meta.py`](_doc/003_script/batch_fix_zboot_meta.py)
  - [`deploy_maven_center.sh`](_doc/003_script/deploy_maven_center.sh)
  - [`install-settings.sh`](_doc/003_script/install-settings.sh)

各文档详细说明见各子目录。
