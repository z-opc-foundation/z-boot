# z-boot-suit

z-boot（Spring Boot Starter 聚合仓 / 版本权威）的**独立运行壳**（lead 005 §9.1 suit）：一个给「用 z-boot starter 搭起来的
服务」用的通用服务台 —— 登录、首页快捷入口、服务状态（actuator 探针）三块能力，**没有业务域页面**。

- **npm 包名**：`@yuku123/z-boot-suit`（`private: true`，**不发布 npm**）
- **宿主接入**：无（独立壳）。仓内对外出口是 `src/index.js`（页面清单 + 文档页）
- **后端**：⚠ **本仓没有后端服务** —— z-boot 是**starter 聚合仓**（`z-boot-parent` + `z-boot-starter/*` +
  `z-boot-integration-starters/*`，全是 jar）。本壳是给用这些 starter 搭出来的业务服务套用的模板壳；
  dev proxy 的 `/api` 指向 `http://localhost:8888`（平台侧通用地址），当前页面**没有调用任何业务 API**
- **技术栈**：React 19 + antd 6 + react-router-dom 7 + vite（**应用层**，基座内联进 bundle）

> ⚠ 本仓**没有** `z-boot-component` 包：页面代码住在本壳 `src/` 下，
> 因此本文档描述的是**本壳自身的能力**。

---

## 一、能力概览

路由前缀 `/z-boot`，菜单与路由都在 `src/pages-manifest.jsx` 里声明，`src/App.jsx` 读数组自己组装。

| 页面 | 路由 | 源文件 | 能力 |
|------|------|--------|------|
| 首页 | `/z-boot/home` | `src/HomePage.jsx` | 欢迎语 + 按 `menuItems` 渲染的快捷入口卡片 |
| 服务状态 | `/z-boot/status` | `src/StatusPage.jsx` + `src/Status.jsx` | 读 actuator 探针显示健康状态 / 构建信息，10 秒轮询 |
| 登录 | `/z-boot/login` | `src/LoginPage.jsx` | mock 登录（**直接在 `App.jsx` 里注册路由，不在路由表里**） |
| 组件文档 | `/z-boot/docs` | `src/pages/ComponentDoc.jsx` | 本文件渲染页（左侧 240px TOC + 右侧正文） |

> ⚠ 本壳的路由清单导出的名字是 **`routeTable`**（不是 `routes`）——`src/App.jsx` 按这个名字消费，
> 改名字会直接让壳起不来。新增路由时沿用 `routeTable`。

## 二、导出面

```js
// 仓内出口（src/index.js）
import {menuItems, routeTable, appMeta, ComponentDocPage} from './src/index.js'

// 单个页面（直接引源文件）
import HomePage from './src/HomePage.jsx'
import StatusPage from './src/StatusPage.jsx'
```

`src/index.js` 是本壳**唯一的 barrel**：把 `src/pages-manifest.jsx` 的清单整份转发，再具名再导出 `ComponentDocPage`
（与其它仓「文档页统一叫 `ComponentDocPage`」的口径一致，宿主/主壳可以按同一个名字取）。

## 三、API 端点

下表路径是本壳页面**实际调用**的路径。⚠ **本壳当前没有任何业务 API 调用** —— 只有 actuator 探针。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/actuator/health` | 健康探针（`Status` 内直接 `fetch`） |
| GET | `/actuator/info` | 构建元信息（`Status` 内直接 `fetch`） |
| GET | `/actuator/mappings` | HTTP 路由清单（`Status` 页仅提供跳转链接） |
| GET | `/actuator/env` | 环境变量与配置属性（`Status` 页仅提供跳转链接） |

`/actuator/health` 与 `/actuator/info` 在 `z-boot-web-starter` 的默认暴露面里；
`/actuator/mappings` 与 `/actuator/env` **不在**默认暴露面 —— 见「六、已知限制」。

## 四、页面说明

### 4.1 首页

登录后着陆页。顶部欢迎语读 `localStorage.userInfo`，下方按 `menuItems`（剔除自身）渲染快捷入口卡片，点击即 `navigate(m.key)`。

### 4.2 服务状态

读 `/actuator/health` + `/actuator/info`，展示健康状态、构建版本、构建时间，并列出 actuator 常用端点跳转。
**后端未起时优雅降级**（loading skeleton + warn，不抛红）；每 10 秒轮询一次。

### 4.3 登录

**mock 登录**：硬编码 `admin / 123456`，成功后写 `localStorage.token`（值形如 `mock-admin`）与
`localStorage.userInfo`，再整页跳 `/z-boot/home`。 CTC/SSO 接入后应换共享 `LoginPage` 的 `loginApi`。

### 4.4 组件文档

本文件。内容以 `?raw` 在编译期内联，零额外请求；左侧 240px TOC 随滚动联动。

## 五、配置

| 配置项 | 默认值 | 说明 |
|---|---|---|
| dev proxy `/api` | `http://localhost:8888` | 平台侧通用地址；**本壳当前页面尚未使用** |
| dev server port | `3031` | `vite.config.js` 的 `server.port` |
| `LOCAL_SIBLINGS=1` | 关 | 开启后走 `alias: {}`（本仓目前无兄弟包别名） |
| token 存储键 | `token` | `localStorage` |
| userInfo 存储键 | `userInfo` | `localStorage`，JSON 串；解析失败降级为 `{name: raw}` |
| `appTitle` | `boot 服务台` | `App.jsx` 里 `AppLayout` 的标题 |

服务端的 actuator 暴露面由 `z-boot-web-starter` 统一收口（**应用侧不要各自写
`management.endpoints.web.exposure.include`**，用 starter 的开关键
`z.boot.metrics.exposure.include` 窄化暴露面）。

## 六、已知限制

- **本壳没有业务能力**：菜单里目前只有首页与服务状态，没有 starter 列表 / 版本拓扑之类的页面。
- **actuator 暴露面受限**：`z-boot-web-starter` 的默认暴露基线是 `health,info,metrics,prometheus`，
  所以服务状态页上 **`/actuator/mappings` 与 `/actuator/env` 两个跳转链接默认会 404**
  （页面本身不受影响，它只 fetch health 与 info）。要开这两个端点需显式声明暴露面。
- **登录是硬编码 mock**（`admin / 123456`），没有真实鉴权；`App.jsx` 的 `ProtectedShell` 只判断 `localStorage.token` 是否存在。
- `Status` 页用相对路径 `fetch('/actuator/health')`，**要求前后端同域托管**；分域部署会 404（此时降级为 UNKNOWN）。
- `Status` 页 10 秒轮询一次 actuator，页面常开时会持续打后端。
- dev proxy 的 `/api` 目标 `:8888` 是平台侧通用地址，**与 z-boot 仓本身无关**（本仓不起服务）。

## 七、变更记录

| 版本 | 变更 |
|---|---|
| 0.1.0（未发布） | 新增组件文档页 `ComponentDocPage`（lead 008 §7）：`src/DOC.md` + 基座 `ComponentDoc` 薄包装 + 菜单末项 |
| 0.1.0 | 首版：首页 / 服务状态 / mock 登录 + manifest |
