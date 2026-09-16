# AGENTS.md — z-boot 仓 AI 协作入口

## 是什么

z-opc-foundation 的 Spring Boot Starter 聚合仓 + 第三方依赖版本权威 (BOM)。

## 快速开始

```bash
mvn clean install -DskipTests        # 全量构建 (本地 install 到 ~/.m2)
mvn clean install -pl :z-boot-web-starter -am   # 单模块 + 依赖
```

## 新增 starter

1. 决定归类: 基础 (`z-boot-starter/`) / 集成 (`z-boot-integration-starters/`)
2. 在对应聚合模块下新建子目录
3. 子 pom 的 parent 指向**聚合模块** (如 `z-boot-starter`), 子 pom 自己 import `z-boot-dependencies` BOM
4. 写 `AutoConfiguration.java` + `META-INF/spring.factories`
5. 在 z-opc 主后端集成验证

## 不要做的事

- **不要在 z-boot 里加 z-msg/z-ctc/z-log 等业务模块**——那些业务 starter 跟着业务仓走
- **不要在 z-boot 顶层 pom 加 dependencyManagement 的 spring-boot 等版本声明**——这些由 z-boot-dependencies 子模块锁定
- **不要直接依赖 com.zifang:z-opc parent**——z-boot 必须是自给自足的

## 发布

参考 `lead/003_辅助能力/maven-central-publish/SKILL.md` 跑 `./deploy_maven_center.sh publish`。
