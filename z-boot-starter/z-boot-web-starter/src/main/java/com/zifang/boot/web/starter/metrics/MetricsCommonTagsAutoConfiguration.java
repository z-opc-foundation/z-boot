package com.zifang.boot.web.starter.metrics;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Tags;
import org.springframework.boot.actuate.autoconfigure.metrics.MeterRegistryCustomizer;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;

import java.net.InetAddress;

/**
 * 指标公共标签（app / instance / env）的统一装配。
 *
 * <p>为什么放在 starter 这一层而不是让每个应用各写一遍 {@code management.metrics.tags.*}：
 * 漏装的那一个服务，指标根本不会带标签，于是"这个服务没埋点"和"这个服务挂了"在告警侧
 * 长得一模一样 —— 而漏装是**不会有人发现的**那种漏（服务照常跑，只是没有指标）。
 * 装在这一层，所有引 z-boot-web-starter 的应用自动获得同一套标签。
 *
 * <p>实现用的是 Micrometer 的 {@link MeterRegistryCustomizer}：Boot 的
 * {@code MeterRegistryPostProcessor} 会把它应用到容器里**每一个** MeterRegistry bean 上
 * （Prometheus / Simple / Composite 都算），所以不需要知道应用最终选了哪种注册表。
 *
 * <p>bean 名固定为 {@code zBootMetricsCommonTagsCustomizer}：Spring Boot 2.x 的
 * {@code @ConditionalOnMissingBean} 对 BeanPostProcessor 类自动配置不生效（它太早注册），
 * 所以这里用名字做条件 —— 应用想自己接管公共标签时，定义一个同名 bean 即可覆盖本条。
 */
@Configuration(proxyBeanMethods = false)
@ConditionalOnClass(MeterRegistry.class)
@EnableConfigurationProperties(MetricsCommonTagsProperties.class)
public class MetricsCommonTagsAutoConfiguration {

    public static final String BEAN_NAME = "zBootMetricsCommonTagsCustomizer";

    /** app 标签在应用没给 spring.application.name 时的兜底值。 */
    static final String UNKNOWN_APP = "unknown";

    /** 没有激活 profile 时的 env 标签取值（与 Spring 生态的 "default" 约定一致）。 */
    static final String DEFAULT_ENV = "default";

    @Bean(BEAN_NAME)
    @ConditionalOnMissingBean(name = BEAN_NAME)
    public MeterRegistryCustomizer zBootMetricsCommonTagsCustomizer(MetricsCommonTagsProperties properties,
                                                                     Environment environment) {
        return new MetricsCommonTagsCustomizer(properties, environment);
    }

    /**
     * 真正的打标动作单独成类：便于单测直接调，不必起 Spring 上下文。
     */
    static class MetricsCommonTagsCustomizer implements MeterRegistryCustomizer {

        private final MetricsCommonTagsProperties properties;
        private final Environment environment;

        MetricsCommonTagsCustomizer(MetricsCommonTagsProperties properties, Environment environment) {
            this.properties = properties;
            this.environment = environment;
        }

        @Override
        public void customize(MeterRegistry registry) {
            registry.config().commonTags(resolveTags());
        }

        Tags resolveTags() {
            String app = firstNonBlank(properties.getApp(),
                    environment.getProperty("spring.application.name"), UNKNOWN_APP);
            String instance = firstNonBlank(properties.getInstance(), deriveInstance(app));
            String env = firstNonBlank(properties.getEnv(), deriveEnv());
            return Tags.of("app", app, "instance", instance, "env", env);
        }

        /**
         * instance 的推导：app + "-" + 端口；端口没定（server.port=0 或没配）时退回主机名 ——
         * 容器里主机名就是 Pod 名，比一个随机的临时端口更能定位实例。
         */
        private String deriveInstance(String app) {
            String port = environment.getProperty("server.port");
            if (port != null && !port.trim().isEmpty() && !"0".equals(port.trim())) {
                return app + "-" + port.trim();
            }
            return app + "-" + hostname();
        }

        private String hostname() {
            try {
                String name = InetAddress.getLocalHost().getHostName();
                return (name == null || name.trim().isEmpty()) ? UNKNOWN_APP : name;
            } catch (Exception e) {
                // 取主机名失败不该让应用起不来：退回 unknown，标签还在，值没那么有用而已
                return UNKNOWN_APP;
            }
        }

        private String deriveEnv() {
            String[] profiles = environment.getActiveProfiles();
            if (profiles != null) {
                for (String profile : profiles) {
                    if (profile != null && !profile.trim().isEmpty()) {
                        return profile.trim();
                    }
                }
            }
            return DEFAULT_ENV;
        }

        private static String firstNonBlank(String... values) {
            for (String value : values) {
                if (value != null && !value.trim().isEmpty()) {
                    return value.trim();
                }
            }
            return "";
        }
    }
}
