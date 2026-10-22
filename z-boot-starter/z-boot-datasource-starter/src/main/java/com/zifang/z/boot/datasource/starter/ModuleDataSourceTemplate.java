package com.zifang.z.boot.datasource.starter;

import com.alibaba.druid.pool.DruidDataSource;
import com.baomidou.mybatisplus.extension.spring.MybatisSqlSessionFactoryBean;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;

import javax.sql.DataSource;

public class ModuleDataSourceTemplate {

    protected DataSource buildDataSource(org.springframework.core.env.Environment env, String module) {
        Binder binder = Binder.get(env);
        String modulePrefix = "z.base.db." + module;
        String defaultPrefix = "z.base.db.default";

        String host = getOrDefault(binder, modulePrefix + ".host", defaultPrefix + ".host", "localhost");
        Integer port = getOrDefault(binder, modulePrefix + ".port", defaultPrefix + ".port", 3306);
        String username = getOrDefault(binder, modulePrefix + ".username", defaultPrefix + ".username", "root");
        String password = getOrDefault(binder, modulePrefix + ".password", defaultPrefix + ".password", "");
        String database = getOrDefault(binder, modulePrefix + ".database", defaultPrefix + ".database", "");

        // ===== JDBC 超时上限（2026-10-22 · TASK-20261021-026）=====
        // 现象（卡内铁证）：阿里云 RDS 抖动时，Druid 建连接线程卡在 Socket.connect 上，
        //   健康端点日志出现 "DataSourceHealthIndicator took 952809ms to respond"（15.9 分钟）
        //   ⇒ 探针被判死 ⇒ 容器被 liveness 重启。
        // 根因：Connector/J 的 connectTimeout / socketTimeout **默认都是 0 = 无限等待**，
        //   连接一旦半开/卡住，等待时间由 TCP 层决定（可达分钟级）。
        // 修法：URL 显式带上毫秒级上限 —— 连不上 3s 内失败，连上但读不动 10s 内失败。
        //   ⇒ 一次改动覆盖所有走本模板拼 URL 的模块（z-ops-admin / z-oss-api / z-config-web /
        //      z-meta-* / z-script-web / z-surl-starter / z-llm-gateway-config /
        //      z-schedule-spring-boot-starter / z-team-starter 的 dataSourceSubscribe+dataSourceProject …）。
        // 可配置（缺省回退 z.base.db.default.*，再缺省 3000 / 10000）：
        //   z.base.db.{module}.connect-timeout / z.base.db.{module}.socket-timeout
        Integer connectTimeout = getOrDefault(binder, modulePrefix + ".connect-timeout", defaultPrefix + ".connect-timeout", 3000);
        Integer socketTimeout = getOrDefault(binder, modulePrefix + ".socket-timeout", defaultPrefix + ".socket-timeout", 10000);

        DruidDataSource ds = new DruidDataSource();
        ds.setUrl(String.format("jdbc:mysql://%s:%d/%s?serverTimezone=UTC&useUnicode=true&characterEncoding=utf-8&connectTimeout=%d&socketTimeout=%d",
                host, port, database, connectTimeout, socketTimeout));
        ds.setUsername(username);
        ds.setPassword(password);
        ds.setDriverClassName("com.mysql.cj.jdbc.Driver");
        ds.setInitialSize(getOrDefault(binder, modulePrefix + ".initial-size", defaultPrefix + ".initial-size", 5));
        ds.setMinIdle(getOrDefault(binder, modulePrefix + ".min-idle", defaultPrefix + ".min-idle", 5));
        ds.setMaxActive(getOrDefault(binder, modulePrefix + ".max-active", defaultPrefix + ".max-active", 20));
        ds.setMaxWait(getOrDefault(binder, modulePrefix + ".max-wait", defaultPrefix + ".max-wait", 60000L));

        // ===== 连接保活 — 解决远程 MySQL (Aliyun RDS) wait_timeout 杀掉空闲连接导致的 200ms+ 抖动 =====
        // 不配置时: 池里 5 个 min-idle 连接会被服务端 wait_timeout 关闭, 借出时第一次查询要重建连接 (≈200ms 抖动).
        // 加上 testWhileIdle + keepAlive 后, 池子每 30s 自动发 SELECT 1 验证 + 主动 keep-alive, 借出永远是热连接.
        ds.setTestWhileIdle(true);
        ds.setTimeBetweenEvictionRunsMillis(30000L);    // 30s 跑一次空闲连接扫描
        ds.setMinEvictableIdleTimeMillis(60000L);       // 空闲 > 60s 才视为可驱逐
        ds.setKeepAlive(true);                          // Druid 1.2+: 主动给 minIdle 连接发心跳
        ds.setValidationQuery("SELECT 1");              // 保活/校验用 SQL
        ds.setValidationQueryTimeout(3000);             // 校验超时 3s
        ds.setTestOnBorrow(false);                      // 借出时不再做 SELECT 1 (依赖 testWhileIdle)
        ds.setTestOnReturn(false);
        ds.setPoolPreparedStatements(true);
        ds.setMaxPoolPreparedStatementPerConnectionSize(20);
        // 可配置: 默认关闭 removeAbandoned，避免 Druid 启动时输 出
        // "removeAbandoned is true, not use in production" 警告。需要在生产排查连接泄漏时
        // 通过 z.base.db.{module}.remove-abandoned=true 显式开启（保留连接超时 5 分钟）。
        boolean removeAbandoned = getOrDefault(binder,
                modulePrefix + ".remove-abandoned", defaultPrefix + ".remove-abandoned", false);
        ds.setRemoveAbandoned(removeAbandoned);
        ds.setRemoveAbandonedTimeout(getOrDefault(binder,
                modulePrefix + ".remove-abandoned-timeout",
                defaultPrefix + ".remove-abandoned-timeout", 300));

        return ds;
    }

    protected MybatisSqlSessionFactoryBean buildSqlSessionFactory(DataSource ds) throws Exception {
        MybatisSqlSessionFactoryBean factoryBean = new MybatisSqlSessionFactoryBean();
        factoryBean.setDataSource(ds);
        factoryBean.setMapperLocations(new PathMatchingResourcePatternResolver().getResources("classpath*:/mapper/**/*.xml"));
        factoryBean.setTypeAliasesPackage("com.zifang.ctc.core.domain.entity");
        return factoryBean;
    }

    protected <T> T getOrDefault(Binder binder, String moduleKey, String defaultKey, T defaultValue) {
        return binder.bind(moduleKey, (Class<T>) defaultValue.getClass())
                .orElseGet(() -> binder.bind(defaultKey, (Class<T>) defaultValue.getClass()).orElse(defaultValue));
    }
}
