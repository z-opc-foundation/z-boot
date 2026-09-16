package com.zifang.z.boot.rpc;

/**
 * z-boot RPC aggregator starter marker.
 *
 * <p>本 starter 只做"传递依赖 + 默认配置提示"两件事, 不提供额外 Bean.
 * 真正的客户端连接由 L3 starter
 * (<code>io.github.yuku123:z-rpc-spring-boot-starter</code>) 在
 * <code>z.rpc.enabled=true</code> 时自动装配.</p>
 *
 * <p>使用方只需在 application.yml 加:</p>
 * <pre>
 * z.rpc:
 *   enabled: true
 *   host: localhost
 *   port: 9888
 * </pre>
 *
 * <p>详细字段见 L3 starter 的 ZRpcProperties 类.</p>
 *
 * <p>本类的存在仅为:</p>
 * <ul>
 *   <li>在 JAR 里留下 z-boot 一致的命名空间
 *       (<code>com.zifang.z.boot.rpc</code>), 便于 IDE 跳转</li>
 *   <li>未来追加 z-boot 默认值 (如 enabled 默认 true 等)
 *       时无需新增 artifact</li>
 * </ul>
 *
 * @see io.github.yuku123.z-rpc.ZRpcProperties
 */
public final class ZBootRpcAutoConfiguration {

    private ZBootRpcAutoConfiguration() {
        // utility class, not for instantiation
    }
}
