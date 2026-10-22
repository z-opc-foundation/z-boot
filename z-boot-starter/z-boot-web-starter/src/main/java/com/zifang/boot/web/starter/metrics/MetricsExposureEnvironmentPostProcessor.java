package com.zifang.boot.web.starter.metrics;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.env.EnvironmentPostProcessor;
import org.springframework.core.Ordered;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.core.env.MapPropertySource;

import java.util.HashMap;
import java.util.Map;

/**
 * 暴露面基线：把"哪些 actuator 端点走 web 暴露"收成一处口径。
 *
 * <p>本组织统一的暴露口径是四项起步 —— <b>health / info / metrics / prometheus</b>
 * （对齐 z-webide 现状）。应用侧要窄化暴露面，走本类的开关键
 * {@code z.boot.metrics.exposure.include}，**不要**各自去改
 * {@code management.endpoints.web.exposure.include} —— 后者一旦各写各的，
 * 就回到"每个应用一个口径"的原状，收口就白做了。
 *
 * <p>优先级（从高到低）：
 * <ol>
 *   <li>{@code z.boot.metrics.exposure.include} —— 本 starter 的开关键，应用显式写就以它为准
 *       （写成 {@code health} 即窄化到只开健康检查）；</li>
 *   <li>{@code management.endpoints.web.exposure.include} —— 应用自己已经声明过暴露面时，
 *       **以应用为准，starter 不动它**。starter 替应用开端点 = 替应用做安全决定，
 *       而暴露面恰恰是最该由应用自己决定的那件事（z-opc 就显式只开 health+info，
 *       因为它的 ManagementWebSecurityAutoConfiguration 被 exclude 了，actuator 端点
 *       没有 Spring Security 兜底）；</li>
 *   <li>都没有 —— 用本类的四项基线 {@link #DEFAULT_INCLUDE}。</li>
 * </ol>
 *
 * <p>落盘方式用 {@code addLast}（最低优先级）而不是 {@code addFirst}：应用自己写的
 * 那一行必须赢。开关键那条走 {@code addFirst}，因为它和应用写在不同键上、不存在竞争，
 * 但它要能盖住"应用没声明"这个默认状态。
 *
 * <p>顺序取 {@link Ordered#LOWEST_PRECEDENCE}：必须排在 ConfigData 之后跑，
 * 否则读不到应用配置文件里写的那一行（读不到就会误判成"应用没声明"⇒ 强行盖基线）。
 */
public class MetricsExposureEnvironmentPostProcessor implements EnvironmentPostProcessor, Ordered {

    /** 应用侧显式声明暴露面时用的键（本 starter 不覆盖它）。 */
    public static final String INCLUDE_KEY = "management.endpoints.web.exposure.include";

    /** 本 starter 的统一开关键：写它 = 窄化/放宽暴露面，优先级最高。 */
    public static final String SWITCH_KEY = "z.boot.metrics.exposure.include";

    /** 全组织暴露口径基线：四项起步。 */
    public static final String DEFAULT_INCLUDE = "health,info,metrics,prometheus";

    private static final String PROPERTY_SOURCE_NAME = "zBootMetricsExposure";

    @Override
    public void postProcessEnvironment(ConfigurableEnvironment environment, SpringApplication application) {
        String switchValue = environment.getProperty(SWITCH_KEY);
        if (switchValue != null && !switchValue.trim().isEmpty()) {
            // 应用用统一开关键显式表态了 ⇒ 以它为准
            put(environment, switchValue.trim(), true);
            return;
        }
        if (environment.getProperty(INCLUDE_KEY) != null) {
            // 应用自己已经声明了暴露面 ⇒ 不动（starter 不替应用做安全决定）
            return;
        }
        put(environment, DEFAULT_INCLUDE, false);
    }

    private void put(ConfigurableEnvironment environment, String value, boolean highest) {
        Map<String, Object> props = new HashMap<String, Object>();
        props.put(INCLUDE_KEY, value);
        MapPropertySource source = new MapPropertySource(PROPERTY_SOURCE_NAME, props);
        if (highest) {
            environment.getPropertySources().addFirst(source);
        } else {
            environment.getPropertySources().addLast(source);
        }
    }

    @Override
    public int getOrder() {
        return Ordered.LOWEST_PRECEDENCE;
    }
}
