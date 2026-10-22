package com.zifang.boot.web.starter.metrics;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * 指标公共标签（common tags）的口径配置。
 *
 * <p>三个标签的组织含义固定，不允许各应用各叫各的：
 * <ul>
 *   <li><b>app</b> —— 应用名，默认取 {@code spring.application.name}；</li>
 *   <li><b>instance</b> —— 实例标识，默认由 app + 端口（或主机名）拼出；</li>
 *   <li><b>env</b> —— 环境名，默认取当前激活的 Spring profile。</li>
 * </ul>
 *
 * <p>三个键都能用本类显式覆盖（{@code z.boot.metrics.tags.app} 等）。留空即"走默认推导"，
 * 不写死任何具体应用的值 ——  starter 是全组织共用的，写死某个应用名会让别的应用继承到
 * 别人的名字，那比没有标签更坏（指标会安静地归到错误的应用名下）。
 *
 * <p>为什么用 {@code @ConfigurationProperties} 而不是直接读 Environment：
 * 这样应用可以用 profile 段或环境变量覆盖某一个标签，而不用改代码。
 */
@ConfigurationProperties(prefix = "z.boot.metrics.tags")
public class MetricsCommonTagsProperties {

    /** 覆盖 app 标签；null/空 ⇒ 取 spring.application.name。 */
    private String app;

    /** 覆盖 instance 标签；null/空 ⇒ 由 app + 端口（或主机名）推导。 */
    private String instance;

    /** 覆盖 env 标签；null/空 ⇒ 取激活 profile 的第一个，没有激活 profile 时取 "default"。 */
    private String env;

    public String getApp() {
        return app;
    }

    public void setApp(String app) {
        this.app = app;
    }

    public String getInstance() {
        return instance;
    }

    public void setInstance(String instance) {
        this.instance = instance;
    }

    public String getEnv() {
        return env;
    }

    public void setEnv(String env) {
        this.env = env;
    }
}
