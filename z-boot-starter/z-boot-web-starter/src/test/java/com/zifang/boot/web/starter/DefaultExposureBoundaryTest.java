package com.zifang.boot.web.starter;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.autoconfigure.actuate.observability.AutoConfigureObservability;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 暴露面边界：应用**没有**自己声明暴露面时，starter 给的是四项基线
 * （health / info / metrics / prometheus），beans / env 一个都不开。
 *
 * <p>和 MetricExposureTest 分成两个上下文，是因为同一个 Spring 上下文里改不了
 * 这类启动期属性 —— 硬凑成一条用 try-with-resources 假装"切回去"的写法，
 * 断言的其实是构造出来的假象。
 *
 * <p>@AutoConfigureObservability 不能省：少了它，PrometheusMeterRegistry 根本不装配，
 * prometheus 端点也就不会注册 —— 那是测试脚手架关的门，不是产品行为
 * （见 MetricExposureTest 的注释）。
 */
@AutoConfigureObservability
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        classes = DefaultExposureBoundaryTest.TestApp.class)
class DefaultExposureBoundaryTest {

    @Autowired
    private TestRestTemplate rest;

    @LocalServerPort
    private int port;

    @SpringBootApplication
    static class TestApp {
    }

    @Test
    void 默认暴露health_info_metrics_prometheus() {
        ResponseEntity<String> index = rest.getForEntity(
                "http://localhost:" + port + "/actuator", String.class);
        assertThat(index.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(index.getBody())
                .contains("health")
                .contains("info")
                .contains("metrics")
                .contains("prometheus")
                .doesNotContain("beans")
                .doesNotContain("env");

        assertThat(rest.getForEntity("http://localhost:" + port + "/actuator/health", String.class)
                .getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(rest.getForEntity("http://localhost:" + port + "/actuator/info", String.class)
                .getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(rest.getForEntity("http://localhost:" + port + "/actuator/metrics", String.class)
                .getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(rest.getForEntity("http://localhost:" + port + "/actuator/prometheus", String.class)
                .getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(rest.getForEntity("http://localhost:" + port + "/actuator/beans", String.class)
                .getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
        assertThat(rest.getForEntity("http://localhost:" + port + "/actuator/env", String.class)
                .getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
    }
}
