package com.zifang.z.boot.script;

/**
 * z-boot z-script 内嵌 starter 的标记类。
 * <p>
 * 本 starter 是直通聚合：唯一职责是把 {@code io.github.yuku123:z-script-web}（传递 core/engine）
 * 带进宿主，实体装配全部由 z-script-web 自己的 spring.factories 完成
 * （{@code ZScriptWebAutoConfiguration}：扫描 com.zifang.z.script + 注册 ScriptEngine 等引擎 bean）。
 * 这里刻意不注册任何 bean、不设开关 —— z-script-web 的装配不归本 starter 管，
 * 提供 {@code z.boot.script.enabled} 之类的假开关只会误导宿主。
 * <p>
 * 宿主要求（缺一不可）：
 * <ul>
 *   <li>MySQL 已执行 z-script 的 {@code _doc/002_deploy/init.sql}；</li>
 *   <li>数据源键 {@code z.base.db.script.host/port/database/username/password}
 *       （{@code ModuleDataSourceTemplate} 只读这组键，写 spring.datasource.* 会静默回落 localhost/root）；</li>
 *   <li>宿主是 Web 应用（Controller / Mock 分发挂在 spring-webmvc 上）。</li>
 * </ul>
 * 鉴权：内嵌后依旧走 z-script 自带的 app+AK（{@code X-Api-Key}）默认拒绝链路，
 * 唯一免鉴权端点是 {@code POST /api/script/api-key}（签发第一把 Key 的引导）。
 * 想整体关闭时不要引本依赖，或由宿主通过 {@code spring.autoconfigure.exclude}
 * 排除 {@code com.zifang.z.script.web.config.ZScriptWebAutoConfiguration}。
 */
public final class ZBootScriptStarter {

    private ZBootScriptStarter() {
    }
}
