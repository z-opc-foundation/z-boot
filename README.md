# z-boot

> z-opc-foundation 的 Spring Boot Starter 聚合仓 + 第三方依赖版本权威 (BOM)。
> z-opc 主后端 / 未来各业务仓 都从这里拉版本约束。

## 模块结构

```
z-boot/
├── pom.xml                          # 自给自足 parent (无依赖 com.zifang:z-opc)
├── z-boot-dependencies/             # 第三方版本 BOM (spring-boot 2.7.12 + jackson 2.18.6 + z-util 1.0.10 + 951 行版本锁)
├── z-boot-starter/                  # 基础 starter (3 个)
│   ├── z-boot-base                  # Log4j2 门面
│   ├── z-boot-web-starter           # Web 通用 (ControllerAdvice / Jackson / CORS)
│   └── z-boot-datasource-starter    # 多数据源 + HikariCP + MyBatis-Plus
└── z-boot-integration-starters/     # 集成 starter (2 个)
    ├── z-boot-jackson-starter       # Jackson 全局配置 (Long 转 String 防精度丢失)
    └── z-tool-webide-spring-boot-starter # Web IDE 自动配置
```

## 用法

### 业务方接入

```xml
<!-- 1. 引入 z-boot-dependencies BOM (锁 spring-boot / jackson / mybatis-plus / log4j2 等所有第三方版本) -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>com.zifang</groupId>
            <artifactId>z-boot-dependencies</artifactId>
            <version>1.0.0-SNAPSHOT</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<!-- 2. 引入需要的 starter (不用写 version, BOM 已锁) -->
<dependencies>
    <dependency>
        <groupId>com.zifang</groupId>
        <artifactId>z-boot-web-starter</artifactId>
    </dependency>
    <dependency>
        <groupId>com.zifang</groupId>
        <artifactId>z-boot-datasource-starter</artifactId>
    </dependency>
</dependencies>
```

### 全世界开发者 (外部)

```xml
<dependency>
    <groupId>com.zifang</groupId>
    <artifactId>z-boot-web-starter</artifactId>
    <version>1.0.0</version>
</dependency>
```

启动类加 `@SpringBootApplication` 即可, AutoConfiguration 会自动装配。

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
