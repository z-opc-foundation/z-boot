package com.zifang.z.boot.ctc.autoconfigure;

import com.zifang.ctc.sso.hook.CtcAuthHook;
import com.zifang.ctc.sso.hook.CtcAuthorizeHook;
import com.zifang.z.boot.ctc.client.HttpCtcAuthHook;
import com.zifang.z.boot.ctc.client.HttpCtcAuthorizeHook;
import com.zifang.z.boot.ctc.properties.ZBootCtcProperties;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * z-boot ctc aggregator starter — 提供 z-ctc 4A 安全的 HTTP 默认实现 hook.
 *
 * <p>当 {@code z.boot.ctc.enabled=true} 时, 注册 HTTP 实现的 {@link CtcAuthHook} 和
 * {@link CtcAuthorizeHook}. 业务方可通过自定义 bean 覆盖 (例如 RPC 实现).</p>
 *
 * <p>L3 z-ctc 服务端的 hook 由 {@code io.github.yuku123:z-ctc-sso} 提供,
 * 本 starter 提供的是客户端默认 hook 实现.</p>
 */
@Configuration
@EnableConfigurationProperties(ZBootCtcProperties.class)
@ConditionalOnProperty(prefix = "z.boot.ctc", name = "enabled", havingValue = "true")
public class ZBootCtcAutoConfiguration {

    private static final Logger log = LogManager.getLogger(ZBootCtcAutoConfiguration.class);

    @Bean
    @ConditionalOnMissingBean
    public CtcAuthHook ctcAuthHook(ZBootCtcProperties properties) {
        log.info("[z-boot-ctc] Creating HTTP CtcAuthHook, server={}", properties.getServerAddr());
        return new HttpCtcAuthHook(
                properties.getServerAddr(),
                properties.getConnectTimeoutMs(),
                properties.getReadTimeoutMs()
        );
    }

    @Bean
    @ConditionalOnMissingBean
    public CtcAuthorizeHook ctcAuthorizeHook(ZBootCtcProperties properties) {
        log.info("[z-boot-ctc] Creating HTTP CtcAuthorizeHook, server={}", properties.getServerAddr());
        return new HttpCtcAuthorizeHook(properties.getServerAddr());
    }
}
