# z-boot-web-starter —— 指标暴露口径（全组织统一）

> 火车号：**1.1.2**（2026-10-22 · TASK-20261012-001 收口）
> 适用：所有引 `io.github.yuku123:z-boot-web-starter` 的 z-* 应用

## 1. 这一层装了什么

| 件 | 版本供给 | 说明 |
|---|---|---|
| `spring-boot-starter-actuator` | 由 `z-boot-parent` → `spring-boot-dependencies:2.7.18` 唯一下发 | 提供 `/actuator/**` 端点本体 |
| `micrometer-registry-prometheus` | 同上（micrometer **1.9.17**） | 提供 `/actuator/prometheus` 抓取面 |

⚠ **本模块的 pom 里不写 micrometer 的 `<version>`** —— 写了就是第二处分叉。
版本由 z-boot BOM 唯一下发，`MetricExposureTest` 里有两条测试把这条钉住
（pom 里出现 micrometer 的 `<version>` 直接红；容器里解析出来的必须是 1.9.17）。

## 2. 公共标签（common tags）

所有指标自动带三个标签，**不需要应用自己写任何 `management.metrics.tags.*`**：

| 标签 | 取值 | 覆盖方式 |
|---|---|---|
| `app` | `spring.application.name`（缺省 `unknown`） | `z.boot.metrics.tags.app` |
| `instance` | `app` + `-` + 端口；端口没定（`server.port=0` 或未配）时用主机名 | `z.boot.metrics.tags.instance` |
| `env` | 当前激活的 Spring profile（没有激活 profile 时 `default`） | `z.boot.metrics.tags.env` |

实测样本（z-lc-admin，dev profile，端口 18099）：

```
jvm_gc_memory_allocated_bytes_total{app="z-lc-bootstrap",env="dev",instance="z-lc-bootstrap-18099",} 4.205087256E9
```

**为什么标签要装在这一层**：漏装标签的那个服务照常跑、照常健康，只是没人能按
应用/实例/环境把它挑出来 —— 而"这个服务没埋点"和"这个服务挂了"在告警侧长得一模一样，
且漏装**不会有人发现**。

## 3. 暴露面（哪些 actuator 端点走 web）

基线（starter 给的默认）：**`health,info,metrics,prometheus`** —— 四项起步，对齐 z-webide 现状。

优先级从高到低：

1. `z.boot.metrics.exposure.include` —— **本 starter 的统一开关键**。应用要窄化/放宽暴露面走这一处
   （例：`z.boot.metrics.exposure.include=health`）。
2. `management.endpoints.web.exposure.include` —— 应用自己已经声明过暴露面时，**以应用为准，starter 不动它**。
3. 都没有 —— 用上面的四项基线。

> ⚠ **为什么 starter 不覆盖应用已声明的暴露面**：暴露面是应用的安全决定。
> z-opc 就显式只开 `health,info` —— 它的 `ManagementWebSecurityAutoConfiguration` 被 exclude 了，
> actuator 端点没有 Spring Security 兜底，此时多开一个 `beans`/`env` 就等于把内部配置从局域网读出去。
> starter 替应用开端点 = 替应用做决定，所以这条边界由 `AppDeclaredExposureWinsTest` 钉住。
>
> ⇒ **收口后要改暴露面，只改 `z.boot.metrics.exposure.include` 这一处**，别再去各应用里
> 写各自的 `management.endpoints.web.exposure.include` —— 那正是"每个应用一个口径"的原状。

## 4. 应用侧自查

```bash
curl -s localhost:<port>/actuator | jq .          # 暴露了哪几项
curl -s localhost:<port>/actuator/prometheus | head  # 抓取面 + 公共标签
```

## 5. 已知口径差异（收口后仍存在的）

| 应用 | 现状 | 说明 |
|---|---|---|
| `z-opc` | 显式 `management.endpoints.web.exposure.include=health,info` | **应用自己的安全决定**，starter 不覆盖 ⇒ `/actuator/prometheus` 在 z-opc 上仍 404。要开就改 z-opc 那份 properties 的那一行（本卡授权面外，未改） |
| `z-webide` | 显式 `health,info,metrics,prometheus` + `management.metrics.tags.application=z-webide` | 暴露面已对齐；标签名是 `application`（不是本口径的 `app`），且该仓尚未升到 1.1.2 火车 ⇒ 公共标签暂由它自己的配置提供 |

## 6. 相关测试

| 测试 | 钉住什么 |
|---|---|
| `MetricExposureTest` | 容器里装的是 PrometheusMeterRegistry；`/actuator/prometheus` 可达且吐文本；pom 里没有 micrometer 字面版本；解析出的 micrometer 是地板版本 1.9.17 |
| `MetricsCommonTagsTest` | 每条指标都带 `app`/`instance`/`env`；抓取文本里也有这三个标签 |
| `DefaultExposureBoundaryTest` | 应用没表态时的暴露基线 = health/info/metrics/prometheus；beans/env 仍 404 |
| `AppDeclaredExposureWinsTest` | 应用表态了 `management.endpoints.web.exposure.include` 时，starter 不改写它 |
