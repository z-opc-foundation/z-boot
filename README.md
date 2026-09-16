# z-boot

> **Spring Boot Starter 聚合仓 + 第三方依赖版本权威 (BOM)**
> 把所有 z-* L3 中间件 + 通用 starter 收成"开箱即用"系列, 业务模块一行 import 一个能力

[![Maven Central](https://img.shields.io/badge/Maven%20Central-1.0.2-blue?logo=apache-maven)](https://central.sonatype.com/search?q=g:io.github.yuku123+a:z-boot*)
[![License](https://img.shields.io/license/MIT-green)](LICENSE)
[![Java](https://img.shields.io/badge/Java-8%2B-orange)](https://openjdk.org)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-2.7.x-6DB33F)](https://spring.io)

---

## 🚀 5 分钟接入

### 方式一：业务模块（推荐, 一次性 import 全部能力）

```xml
<!-- 1. 引入 z-boot-dependencies BOM (锁所有版本) -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>io.github.yuku123</groupId>
            <artifactId>z-boot-dependencies</artifactId>
            <version>1.0.2</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<!-- 2. 按需引入 starter (version 由 BOM 锁) -->
<dependencies>
    <!-- 基础能力 -->
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-web-starter</artifactId>
    </dependency>
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-datasource-starter</artifactId>
    </dependency>

    <!-- L3 中间件 (一行 import 一个) -->
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-cache-starter</artifactId>
    </dependency>
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-rpc-starter</artifactId>
    </dependency>
</dependencies>
```

`application.yml`:

```yaml
z:
  cache:
    enabled: true
    host: localhost
    port: 16379
  rpc:
    enabled: true
    protocol: zrpc
    port: 9888
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
    <version>1.0.2</version>
</dependency>
```

---

## 📦 已发布到 Maven Central 的所有模块

> groupId: `io.github.yuku123` · version: **1.0.2** · 共 **15 个 artifact**

### 基础 starter (3 个)

| 模块 | 说明 |
|---|---|
| `z-boot-base` | Log4j2 门面 + ApplicationModuleDescription 接口 |
| `z-boot-web-starter` | Spring Web + Log4j2 + Knife4j OpenAPI 3 自动装配 |
| `z-boot-datasource-starter` | Druid + MyBatis-Plus + mysql + 多数据源 |

### 集成型 starter (2 个)

| 模块 | 说明 |
|---|---|
| `z-boot-jackson-starter` | Jackson 全局配置 (Long → String 防精度丢失) |
| `z-boot-ctc-starter` | CTC 4A 安全 HTTP hook 默认实现 (CtcAuthHook + CtcAuthorizeHook) |
| `z-boot-msg-starter` | MSG 多通道消息下发 (短信 / 邮件 / In-app / Push / Webhook / IM) |

### L3 中间件聚合 starter (10 个)

| 模块 | 依赖的 L3 starter | L3 版本 | 默认端口 | 启用开关 |
|---|---|---|---|---|
| `z-boot-cache-starter` | z-cache-spring-boot-starter | 1.0.2 | 16379 | `z.cache.enabled=true` |
| `z-boot-mq-starter` | z-mq-spring-boot-starter | 1.0.2 | 9876 | `z.mq.enabled=true` |
| `z-boot-gw-starter` | z-gw-spring-boot-starter | 1.0.1 | - | `z.gw.enabled=true` |
| `z-boot-kb-starter` | z-kb-spring-boot-starter | 1.0.1 | - | `z.kb.enabled=true` |
| `z-boot-vector-starter` | z-vector-spring-boot-starter | 1.0.1 | - | `z.vector.enabled=true` |
| `z-boot-graph-starter` | z-graph-spring-boot-starter | 1.0.1 | 8182 | `z.graph.enabled=true` |
| `z-boot-rpc-starter` | z-rpc-spring-boot-starter | 1.0.2 | 9888 | `z.rpc.enabled=true` |
| `z-boot-oss-starter` | z-oss-common | 1.0.1 | 9000 | `z.oss.enabled=true` |
| `z-boot-schedule-starter` | z-schedule-spring-boot-starter | 1.0.0 | 18086 | `z.schedule.enabled=true` |
| `z-boot-msg-starter` | z-msg-web | 1.0.0 | - | `z.msg.enabled=true` |

### BOM (1 个)

| 模块 | 说明 |
|---|---|
| `z-boot-dependencies` | 第三方依赖版本权威（spring-boot 2.7.12 + jackson 2.18.6 + z-util 1.0.10 + 951 行版本锁）|

### 聚合 POM (3 个)

- `z-boot`（顶层聚合）
- `z-boot-starter`（基础 starter 聚合）
- `z-boot-integration-starters`（集成 + L3 聚合 starter 聚合）

---

## ✨ 核心能力

### L3 中间件聚合（一行集成）
- ✅ **8 个聚合 starter**，把已发布的 z-cache / z-mq / z-gw / z-kb / z-vector / z-graph / z-rpc / z-oss 全部包装成 `z-boot-*`
- ✅ **每个 starter 自动**:
  - 引入对应 L3 的 `-spring-boot-starter` 作为 transitive dependency
  - 暴露统一的 `z.{pkg}.enabled` 开关（默认 false，业务方显式打开）
  - 提供 IDE 跳转的 marker class（`com.zifang.z.boot.{pkg}.ZBoot{Pkg}AutoConfiguration`）
- ✅ **L3 版本统一由 z-boot-integration-starters BOM 管理**——改版本只改一处

### 第三方版本权威（BOM）
- ✅ **z-boot-dependencies** 是 L1 业务模块**唯一**版本锁入口
- ✅ **951 行版本表**：spring-boot 2.7.12 / jackson 2.18.6 / z-util 1.0.10 / druid / mybatis-plus / log4j2 / netty / lettuce / commons-*
- ✅ 业务方**禁止**自己声明版本号（应该由 BOM 锁）

### 零 z-opc 内部依赖
- ✅ **z-boot 自身不依赖** `com.zifang:z-opc` (monorepo 内部 parent)
- ✅ **所有子模块** 也都不依赖 monorepo
- ✅ **可独立发布到 Maven Central**——已发布 1.0.2

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
            <version>1.0.2</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependencies>
    <!-- Web + DB -->
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-web-starter</artifactId></dependency>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-datasource-starter</artifactId></dependency>

    <!-- 中间件 (一行一个) -->
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-cache-starter</artifactId></dependency>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-mq-starter</artifactId></dependency>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-rpc-starter</artifactId></dependency>
</dependencies>
```

### Case 2: 单独用某个 starter（外部开发者）

```xml
<!-- 我只要 z-cache 客户端, 不要全套 -->
<dependency>
    <groupId>io.github.yuku123</groupId>
    <artifactId>z-boot-cache-starter</artifactId>
    <version>1.0.2</version>
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
            <version>1.0.2</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

### Case 4: 通过 z-boot-* 启动 RAG 知识库

```xml
<dependencies>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-web-starter</artifactId></dependency>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-kb-starter</artifactId></dependency>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-vector-starter</artifactId></dependency>
    <dependency><groupId>io.github.yuku123</groupId><artifactId>z-boot-cache-starter</artifactId></dependency>
</dependencies>
```

---

## 🏗️ 项目结构

```
z-boot/
├── pom.xml                          # 自给自足 parent (Central namespace)
├── z-boot-dependencies/             # 第三方版本 BOM (951 行)
├── z-boot-starter/                  # 基础 starter 聚合
│   ├── z-boot-base                  # Log4j2 门面
│   ├── z-boot-web-starter           # Web + Log4j2 + Knife4j
│   └── z-boot-datasource-starter    # Druid + MyBatis-Plus + mysql
└── z-boot-integration-starters/     # 集成 starter 聚合 (9 个)
    ├── z-boot-cache-starter         # ← NEW L3 聚合
    ├── z-boot-mq-starter            # ← NEW L3 聚合
    ├── z-boot-gw-starter            # ← NEW L3 聚合
    ├── z-boot-kb-starter            # ← NEW L3 聚合
    ├── z-boot-vector-starter        # ← NEW L3 聚合
    ├── z-boot-graph-starter         # ← NEW L3 聚合
    ├── z-boot-rpc-starter           # ← NEW L3 聚合
    ├── z-boot-oss-starter           # ← NEW L3 聚合
    └── z-boot-jackson-starter       # Jackson 全局配置
```

---

## 🔧 高级

### 升级 z-boot / L3 中间件版本

改 `z-boot-integration-starters/pom.xml` 的 `<dependencyManagement>` 一处：

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>io.github.yuku123</groupId>
            <artifactId>z-cache-spring-boot-starter</artifactId>
            <version>1.0.3</version>   <!-- ← 只改这里, 8 个 z-boot-* starter 全部跟着升级 -->
        </dependency>
        ...
    </dependencies>
</dependencyManagement>
```

业务方只需升 `z-boot-dependencies` 一个 BOM。

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

参考 `z-boot-cache-starter` 的 marker class 结构（pom + Properties + IDE 跳转锚点）。

---

## 🧪 集成测试覆盖

```
Maven Central 拉取测试:
- 8 个 z-boot-* 聚合 starter (1.0.2) 全部 jar=200 pom=200 ✅
- BOM 内容校验 ✅
- 命名约定校验 ✅

详情见 z-opc/z-middleware-integration-test/ZBootAggregatorStarterMavenCentralPullIT
```

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
2. 写 `pom.xml`（依赖 L3 starter）+ 1 个 marker Java 类
3. 父 pom 加 `<module>` + dependencyManagement 加 L3 版本
4. 升 version + 跑 `mvn clean install -DskipTests`
5. `bash deploy_maven_center.sh publish`

参考 `.scripts/gen_z_boot_starters.py`。

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

---

## 📮 联系

- GitHub Issues: 提交 bug / feature request
- Email: yuku123@users.noreply.github.com

## 模块结构

```
z-boot/
├── pom.xml                          # 自给自足 parent (无依赖 com.zifang:z-opc)
├── z-boot-dependencies/             # 第三方版本 BOM (spring-boot 2.7.12 + jackson 2.18.6 + z-util 1.0.10 + 951 行版本锁)
├── z-boot-starter/                  # 基础 starter (3 个)
│   ├── z-boot-base                  # Log4j2 门面
│   ├── z-boot-web-starter           # Web 通用 (ControllerAdvice / Jackson / CORS)
│   └── z-boot-datasource-starter    # 多数据源 + HikariCP + MyBatis-Plus
└── z-boot-integration-starters/     # 集成 starter (9 个)
    ├── z-boot-cache-starter         # ← NEW  z-cache 客户端 (本地 16379)
    ├── z-boot-mq-starter            # ← NEW  z-mq producer/consumer
    ├── z-boot-gw-starter            # ← NEW  z-gw 网关服务注册
    ├── z-boot-kb-starter            # ← NEW  z-kb 知识库 (LLM + 向量 + 图)
    ├── z-boot-vector-starter        # ← NEW  z-vector 向量数据库
    ├── z-boot-graph-starter         # ← NEW  z-graph 图数据库
    ├── z-boot-rpc-starter           # ← NEW  z-rpc 分布式 RPC
    ├── z-boot-oss-starter           # ← NEW  z-oss 对象存储抽象层
    └── z-boot-jackson-starter       # Jackson 全局配置 (Long 转 String 防精度丢失)
```

## 用法

### 业务方接入 (推荐: 一次性引入 z-boot)

```xml
<!-- 1. 引入 z-boot-dependencies BOM (锁所有第三方版本) -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>io.github.yuku123</groupId>
            <artifactId>z-boot-dependencies</artifactId>
            <version>1.0.2</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<!-- 2. 引入需要的 starter (不用写 version, BOM 已锁) -->
<dependencies>
    <!-- 基础能力 -->
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-web-starter</artifactId>
    </dependency>
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-datasource-starter</artifactId>
    </dependency>

    <!-- L3 中间件 (一行 import 集成, 不用自己再找 L3 starter) -->
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-cache-starter</artifactId>
    </dependency>
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-mq-starter</artifactId>
    </dependency>
    <dependency>
        <groupId>io.github.yuku123</groupId>
        <artifactId>z-boot-rpc-starter</artifactId>
    </dependency>
    <!-- ... 其他 5 个 z-boot-*-starter 按需 -->
</dependencies>
```

### 全世界开发者 (外部, 一行 import 一个中间件)

```xml
<dependency>
    <groupId>io.github.yuku123</groupId>
    <artifactId>z-boot-cache-starter</artifactId>
    <version>1.0.2</version>
</dependency>
```

application.yml:

```yaml
z:
  cache:
    enabled: true
    host: localhost
    port: 16379
```

启动类加 `@SpringBootApplication` 即可, L3 starter 的 AutoConfiguration 会自动装配。

## L3 中间件聚合 starter 矩阵

| z-boot starter | 依赖 L3 starter | 默认端口 | 启用开关 |
|---|---|---|---|
| z-boot-cache-starter | z-cache-spring-boot-starter 1.0.2 | 16379 | `z.cache.enabled=true` |
| z-boot-mq-starter | z-mq-spring-boot-starter 1.0.2 | 9876 | `z.mq.enabled=true` |
| z-boot-gw-starter | z-gw-spring-boot-starter 1.0.1 | - | `z.gw.enabled=true` |
| z-boot-kb-starter | z-kb-spring-boot-starter 1.0.1 | - | `z.kb.enabled=true` |
| z-boot-vector-starter | z-vector-spring-boot-starter 1.0.1 | - | `z.vector.enabled=true` |
| z-boot-graph-starter | z-graph-spring-boot-starter 1.0.1 | 8182 | `z.graph.enabled=true` |
| z-boot-rpc-starter | z-rpc-spring-boot-starter 1.0.2 | 9888 | `z.rpc.enabled=true` |
| z-boot-oss-starter | z-oss-common 1.0.1 | 9000 | `z.oss.enabled=true` |

**每个 z-boot-* starter 都自动:
- 引入对应 L3 的 spring-boot-starter (transitive dependency)
- 暴露统一的 `z.{pkg}.enabled` 开关 (默认 false, 业务方显式打开)
- 提供 IDE 跳转的 marker class (`com.zifang.z.boot.{pkg}.ZBoot{Pkg}AutoConfiguration`)
- 由 z-boot-integration-starters BOM 统一锁 L3 版本号 (改版本只改一处)**

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
   └── z-opc/z-boot/         ← 暂时保留 z-config/z-ctc/z-ext/z-lc/z-mist/z-log/z-msg 业务 starter (等业务仓独立后再迁出)
```

**z-boot 不依赖任何 z-opc 业务模块**。版本由 z-boot 锁定, z-opc 等消费者通过 import BOM 间接获得约束。

## 发布

通过 `lead/003_辅助能力/maven-central-publish` skill 一键发布到 Maven Central。
具体见 z-util/发布指引.md (28KB 实战手册)。


## 文档目录

本项目文档统一收口在 `_doc/` 下:

- [`_doc/001_arch/`](_doc/001_arch/) — 架构文档 (项目总览 / 模块结构 / 接口清单 / DB schema / 前端 / 能力 / roadmap):
  - [`AGENTS.md`](_doc/001_arch/AGENTS.md)

- [`_doc/003_script/`](_doc/003_script/) — 运维脚本:
  - [`batch_fix_zboot_meta.py`](_doc/003_script/batch_fix_zboot_meta.py)
  - [`deploy_maven_center.sh`](_doc/003_script/deploy_maven_center.sh)
  - [`install-settings.sh`](_doc/003_script/install-settings.sh)

各文档详细说明见各子目录。
