package com.zifang.z.boot.config;

/**
 * z-boot Config aggregator starter marker.
 *
 * <p>本 starter 只做"传递依赖 + 默认配置提示"两件事, 不提供额外 Bean.
 * 真正的配置中心客户端连接由 L3 starter
 * (<code>io.github.yuku123:z-config-spring-boot-starter</code>) 在
 * <code>z.config.enabled=true</code> 时自动装配.</p>
 *
 * <p>使用方只需在 application.yml 加:</p>
 * <pre>
 * z.config:
 *   enabled: true
 *   server-addr: localhost:8848
 *   namespace: default
 * </pre>
 *
 * <p>本类的存在仅为:</p>
 * <ul>
 *   <li>在 JAR 里留下 z-boot 一致的命名空间
 *       (<code>com.zifang.z.boot.config</code>), 便于 IDE 跳转</li>
 *   <li>未来追加 z-boot 默认值时无需新增 artifact</li>
 * </ul>
 */
public final class ZBootConfigAutoConfiguration {

    private ZBootConfigAutoConfiguration() {
        // utility class, not for instantiation
    }
}
