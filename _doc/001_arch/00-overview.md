# 项目总览

## 1. 项目简介

z-boot 是 z-opc-foundation 的 **Spring Boot Starter 聚合仓 + 唯一版本权威**。它自己不是一个可运行的应用，而是给组织内所有 Java 仓提供一条统一消费入口 `io.github.yuku123:z-boot-parent`：消费方写一行 `<parent>`，后面所有依赖都不再写 `<version>`。

本仓同时承担两件事：

1. **版本权威** —— 第三方依赖的版本地板（spring-boot / netty / jackson / mybatis-plus / druid / log4j2 …）与兄弟仓 `z-*`（z-cache / z-mq / z-gw / z-oss …）的版本格，都收口在 `z-boot-parent` 的 `<dependencyManagement>` 里。
2. **Starter 聚合** —— 把已发布的 L3 中间件包装成 `z-boot-*` starter 向下游发；另有 3 个基础 starter（base / web / datasource）承载全组织共用的 Web、持久化、日志口径。

**技术栈：** Java 8 · Spring Boot 2.7.18 · Maven（聚合发布件，发 Maven Central）· 前端侧一套 React 19 + antd 6 + Vite 6 的独立管理台壳（`_frontend/z-boot-suit`，不发布 npm）

**本仓不启进程、不监听端口** —— 仓内没有 Dockerfile、docker-compose 或 k8s yaml，所有产物都是 jar / pom。

## 2. 模块架构

```
z-boot/
├── pom.xml                       # 根：z-boot:1.0.19，packaging=pom，1.0.19 起不再有 <modules>，只管 plugin 版本 / central profile / flatten
├── z-boot-parent/                # 唯一消费入口：z-boot-parent:1.1.1，第三方地板 + 接入面 pin + 自家 22 格 starter
├── z-boot-starter/               # 基础 starter 聚合器：z-boot-starter:1.1.1
│   ├── z-boot-base/              # 应用名 / 根包名两个 SPI 接口（ApplicationModuleDescription）
│   ├── z-boot-web-starter/       # Web + Log4j2 + Knife4j + Actuator/Prometheus + Long→String 序列化
│   └── z-boot-datasource-starter/ # Druid + MyBatis-Plus + MySQL，附审计字段自动填充
├── z-boot-integration-starters/  # 集成 starter 聚合器：z-boot-integration-starters:1.1.1，19 个 <module>
│   ├── z-boot-cache-starter/     # ← L3 聚合（占位 marker）
│   ├── z-boot-mq-starter/        # ← L3 聚合（占位 marker）
│   ├── z-boot-gw-starter/        # ← L3 聚合（占位 marker）
│   ├── z-boot-kb-starter/        # ← L3 聚合（占位 marker）
│   ├── z-boot-vector-starter/    # ← L3 聚合（占位 marker）
│   ├── z-boot-graph-starter/     # ← L3 聚合（占位 marker）
│   ├── z-boot-rpc-starter/       # ← L3 聚合（占位 marker）
│   ├── z-boot-oss-starter/       # ← L3 聚合（占位 marker）
│   ├── z-boot-schedule-starter/  # 仅 package-info
│   ├── z-boot-msg-starter/       # 仅 package-info
│   ├── z-boot-ctc-starter/       # 唯一自带自动装配的 L3 starter（ZBootCtcAutoConfiguration + 鉴权 Hook）
│   ├── z-boot-script-starter/    # marker 改名的一例（ZBootScriptStarter，不注册 bean）
│   ├── z-boot-llm-starter/       # 仅 package-info
│   ├── z-boot-mcp-starter/       # 仅 package-info
│   ├── z-boot-skill-starter/     # 仅 package-info
│   ├── z-boot-agent-starter/     # 仅 package-info
│   ├── z-boot-bot-starter/       # 仅 package-info
│   └── z-boot-agent-proxy-starter/ # 仅 package-info
├── _frontend/z-boot-suit/        # 独立运行壳：React 19 + antd 6 + Vite 6，private，不发 npm
├── _doc/
│   ├── 001_arch/                 # 架构与协作约定（本文 + AGENTS.md）
│   └── 003_script/               # 27 个发布 / 量具 / 判据脚本
├── .github/workflows/publish-central.yml  # Central 发布 workflow（只调仓内脚本，版本来自 pom）
└── .flattened-pom.xml            # flatten 插件产物
```

## 3. 核心功能

### 3.1 统一消费入口 `z-boot-parent`

`z-boot-parent/pom.xml` 是本仓唯一对外的消费坐标（当前版本 `1.1.1`，`<parent>` = 根 `z-boot:1.0.19`）。它的 `<dependencyManagement>` 共 **256 条**，按坐标空间分三段互不重叠：

- 第三方地板 **150 条**（spring-boot 2.7.18 / netty 4.1.138.Final / mybatis-plus / druid / knife4j / dubbo 2.7.21 / elasticsearch …）
- 第三方 BOM import **5 条**（如 `spring-boot-dependencies`、`jackson-bom`、`netty-bom`、`junit-bom`、`spring-framework-bom`）
- `io.github.yuku123` 坐标 **101 条** —— 接入面 pin（兄弟仓 `z-*` 的真实跨仓声明）+ 自家 22 格 `z-boot-*` starter

`<properties>` 段 136 个键，承担 Java 8 编译口径与全部第三方版本号。

### 3.2 火车制版本拓扑

根 pom 自 1.0.19 起**没有 `<modules>`**：每个文件夹是独立可发的 Maven 工程，自带字面版本（当前三件同号 `1.1.1`）。发布粒度 = 文件夹，发版顺序 root → parent → starter → integration，由 `_doc/003_script/deploy_maven_center.sh` 按 `FLEET_ORDER` 逐文件夹 `mvn -f <folder>/pom.xml deploy -Pcentral`，并对「同版本已上线就跳过」「当版 parent 未上线自动前置」做了硬处理。

版本格的唯一真源是 `_doc/003_script/gen_train_bom.py` 的 `FAMILIES` 表（**25 族**：z-config / z-ctc / z-cache / z-mq / z-gw / z-kb / z-vector / z-graph / z-rpc / z-oss / z-schedule / z-msg / z-script / z-util / z-agent-kernel / z-llm / z-mcp / z-skill / z-agent / z-bot / z-agent-proxy / z-mist / z-qa / z-camuda / z-indexer），另有 `EXTRA_PIN` 补 3 个 `z-util-http-*` 坐标。生成器从 `git HEAD` 读模板输入，重放幂等。

### 3.3 三个基础 starter

- **`z-boot-base`** —— 只有一个接口 `com.zifang.z.boot.base.ApplicationModuleDescription`，定义 `getApplicationName()` 与 `getBasePackage()` 两个方法（应用标准名 / 当前模块根包路径）。
- **`z-boot-web-starter`** —— 依赖 `spring-boot-starter-web` + `spring-boot-starter-log4j2` + `knife4j-openapi3-spring-boot-starter` + `spring-boot-starter-actuator` + `micrometer-registry-prometheus`；唯一有实质行为的类是 `com.zifang.boot.web.starter.GlobalJacksonConfig`，把 `Long` / `long[]` 序列化为字符串（JS Number 安全精度只有 2^53，19 位雪花 ID 会丢末位精度），并通过 `META-INF/spring.factories` 注册为自动装配。
- **`z-boot-datasource-starter`** —— 依赖 `druid-spring-boot-starter` + `mybatis-plus-boot-starter` + `mysql-connector-j`；源码 5 个类：`ModuleDataSourceTemplate`（按模块路由数据源）、`IPageable` / `PageUtil`（分页协议）、`AuditDO` / `AuditMetaObjectHandler`（审计字段自动填充）。

### 3.4 19 个集成 starter 的真实形态

19 个 `z-boot-*-starter` 里只有 **2 个**注册了自动装配（`META-INF/spring.factories` 全仓只有 2 份）：`z-boot-ctc-starter`（`ZBootCtcAutoConfiguration` + `HttpCtcAuthHook` + `HttpCtcAuthorizeHook` + `ZBootCtcProperties`）与 `z-boot-web-starter`。其余 17 个中，**11 个**带 marker 类（`ZBoot*AutoConfiguration` 占位或 `ZBootScriptStarter`），**8 个**（agent / agent-proxy / bot / llm / mcp / msg / schedule / skill）只有一份 `package-info.java`，jar 内除 `package-info.class` 外无自动装配类。

### 3.5 发布判据与发布流水线

`_doc/003_script/` 下 27 个文件是本仓的「可执行判据」，其中：

- `deploy_maven_center.sh` —— 按文件夹发版，支持 `publish` / `publish --dry`（只到 verify）/ `publish --bundle`（按发布态打包但把上传目标指向不可达域名，逐坐标点 4 件套）/ `bundle <zip>`（拿别人的包也能点）。
- `verify_central.sh` + `verify-classes.txt` + `verify-content.txt` —— 对真实 Maven Central 校验 `.pom` / `.jar` / `-sources.jar` / `-javadoc.jar` / `.asc` 签名 / POM metadata，并把线上 pom 与本地源码 pom 做结构性比对（受管 `<artifactId>` 集合 + `<properties>` 各键值）。
- `fleet_inline_check.py` —— 逐件回读 repo1 上 starter 发布件里内联的兄弟版本，与 fleet 源码当前格对账（本地 `.flattened-pom.xml` 是同一份源码重算的，拿它对账是恒等式，锁不住欠账）。
- `central_pom_scan.py` —— 上传前静态点 B/C/D/E 四类 pom 缺陷。
- `gen_train_bom.py` / `bump_version.py` / `parent_preflight.py` / `publish_bump_check.py` / `ship_train_consumers.py` / `rollout_train_consumers.py` —— 抬号与消费方跟版。
- `doc_audit.py` —— 组织级文档收口审计尺（R1 / R2 / R3 / R4 / R5 / R5b / R6 / R7 / R8 / R9 十条），被其它仓复用。

### 3.6 前端运行壳 `_frontend/z-boot-suit`

`package.json` 标 `private: true`、`"description": "…不发布 npm"`。依赖 `@yuku123/z-frontend-common@^1.0.0` + antd 6 + `@ant-design/pro-components` + react 19 + react-router-dom 7，构建用 Vite 6 + `@vitejs/plugin-react`；源码在 `src/`（`App.jsx` / `HomePage.jsx` / `LoginPage.jsx` / `Status.jsx` / `StatusPage.jsx` / `pages-manifest.jsx` / `main.jsx`），产出静态页面。

## 4. 对外集成 / 上下游

**上游：** 兄弟仓 `z-*` 的已发布坐标（z-cache / z-mq / z-gw / z-kb / z-vector / z-graph / z-rpc / z-oss / z-schedule / z-msg / z-ctc / z-script / z-llm / z-mcp / z-skill / z-agent / z-bot / z-agent-proxy / z-agent-kernel / z-util / z-mist / z-qa / z-camuda / z-indexer / z-config），由 19 个集成 starter 做传递依赖包装。

**下游（消费方）：** 组织内所有 Java 仓以一行 `<parent>io.github.yuku123:z-boot-parent:1.1.1</parent>` 接入，依赖一律不写 `<version>`。外部开发者也可只 import 单个 starter。

**对外 HTTP 边界：无。** 本仓不启进程、不监听端口、不出网。唯一的外部交互是发布动作 —— `deploy_maven_center.sh` 与 `verify_central.sh` 直连 `repo1.maven.org` / `central.sonatype.com`，凭证走仓根 `.env` 与 `./.gnupg`（两者被 `.gitignore` 排除）。

**CI：** `.github/workflows/publish-central.yml` 的 workflow_dispatch 需显式输入 `confirm=publish` 才真上传，否则只跑两道闸 + bundle 演练。

## 5. 技术特点

1. **根 pom 刻意没有 `<modules>`**：1.0.19 起按文件夹独立成工程、各带字面版本，于是「抬 z-ctc 一格」不再牵动第三方地板 BOM —— 这是本仓拓扑与多数多模块仓最不一样的地方。
2. **版本格只有一处真源**：`gen_train_bom.py` 的 `FAMILIES`（25 族）生成 parent 的 DM 段，模板输入一律读 `git HEAD`（`pristine()`），重放幂等、生成器不吃自己上一次的产物。
3. **接入面 pin 是机械现算的**：跨仓被真实声明的坐标由脚本遍历 `../` 下各仓 pom 现算得出，DTO 里查不到族就报警，不靠人肉维护。
4. **starter 层普遍是「空壳」**：19 个集成 starter 里 8 个只有 `package-info.java`、11 个的 marker 类无注解也不写进 `spring.factories` —— 只有 ctc 与 web-starter 真注册自动装配。README 明确把这层「只做传递依赖」写成设计意图。
5. **flatten 模式决定了版本键写法**：自家 starter 的版本键必须是字面 property `<z-boot.version>`，不能写 `${project.version}` —— `flatten` 配的是 `resolveCiFriendliesOnly`，只解 `${revision}` 一组，写 `${project.version}` 会把消费方的版本号原样发出去。
6. **发布判据是仓内脚本而不是 CI 里的手写步骤**：workflow 只负责调 `deploy_maven_center.sh`，版本从 pom 取、发布顺序 / 跳过同版本 / 缺 parent 自动前置 / bundle 逐坐标点件全在脚本里，避免两套口径。
7. **Long→String 序列化下沉到基座**：`GlobalJacksonConfig` 的注释记录了成因（JS 2^53 精度 vs 19 位雪花 ID），并明说「本配置下沉到 z-boot-jackson-starter 后由所有 web 模块统一继承」，避免各模块各写一份。

## 6. 目录结构

源码包树共 3 段（`com.zifang.*`），仓内跟踪的 Java 源文件共 31 个（29 个 main + 2 个 test）：

```
z-boot/
├── z-boot-starter/
│   ├── z-boot-base/src/main/java/com/zifang/z/boot/base/
│   │   └── ApplicationModuleDescription.java   # 应用名 / 根包名 SPI
│   ├── z-boot-web-starter/src/main/java/com/zifang/boot/web/starter/
│   │   ├── GlobalJacksonConfig.java             # Long→String 序列化 + spring.factories 注册
│   │   └── ../../../../resources/META-INF/spring.factories
│   ├── z-boot-web-starter/src/test/java/com/zifang/boot/web/starter/
│   │   ├── DefaultExposureBoundaryTest.java
│   │   └── MetricExposureTest.java
│   └── z-boot-datasource-starter/src/main/java/com/zifang/z/boot/datasource/starter/
│       ├── ModuleDataSourceTemplate.java        # 按模块路由数据源
│       ├── IPageable.java / PageUtil.java       # 分页协议与工具
│       └── AuditDO.java / AuditMetaObjectHandler.java  # 审计字段自动填充
└── z-boot-integration-starters/
    ├── 11 个带 marker 的 starter：com.zifang.z.boot.{cache,config,graph,gw,kb,mq,oss,rpc,vector}/ZBoot*AutoConfiguration.java
    │   ├── z-boot-ctc-starter/.../com/zifang/z/boot/ctc/
    │   │   ├── autoconfigure/ZBootCtcAutoConfiguration.java
    │   │   ├── client/HttpCtcAuthHook.java + HttpCtcAuthorizeHook.java
    │   │   └── properties/ZBootCtcProperties.java
    │   └── z-boot-script-starter/.../com/zifang/z/boot/script/ZBootScriptStarter.java
    └── 8 个仅 package-info 的 starter：com.zifang.boot.{agent,agentproxy,bot,llm,mcp,msg,schedule,skill}.starter
```

注意包名有两种前缀并存：`com.zifang.z.boot.*`（带 `z` 段，base / datasource / 全部 L3 marker）与 `com.zifang.boot.*`（不带 `z` 段，web-starter 与 8 个 package-info starter）—— 这是本仓历史沿革留下的形状，不是笔误。

`_doc/` 侧：`001_arch/`（本文 + `AGENTS.md` 协作入口）与 `003_script/`（27 个脚本）两个桶。
