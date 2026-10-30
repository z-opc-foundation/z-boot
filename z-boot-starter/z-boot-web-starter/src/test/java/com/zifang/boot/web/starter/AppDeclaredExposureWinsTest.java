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
 * 应用自己声明了暴露面时，**starter 不覆盖它**。
 *
 * <p>这条是暴露面收口里最要紧的边界：暴露面是应用的安全决定（z-opc 就显式只开
 * health+info，因为它的 ManagementWebSecurityAutoConfiguration 被 exclude 了，
 * actuator 端点没有 Spring Security 兜底），starter 替应用开端点 = 替应用做决定。
 *
 * <p>starter 只在应用**没有**表态时给四项基线；应用表态了，以应用为准。
 * 应用要窄化，走统一开关键 {@code z.boot.metrics.exposure.include}（见
 * MetricsExposureEnvironmentPostProcessor 的注释）。
 */
@AutoConfigureObservability
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        classes = AppDeclaredExposureWinsTest.TestApp.class,
        properties = {
                "management.endpoints.web.exposure.include=health"
        })
class AppDeclaredExposureWinsTest {

    @Autowired
    private TestRestTemplate rest;

    @LocalServerPort
    private int port;

    @SpringBootApplication
    static class TestApp {
    }

    @Test
    void 应用声明的暴露面不被starter改写() {
        assertThat(rest.getForEntity("http://localhost:" + port + "/actuator/health", String.class)
                .getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(rest.getForEntity("http://localhost:" + port + "/actuator/prometheus", String.class)
                .getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
        assertThat(rest.getForEntity("http://localhost:" + port + "/actuator/metrics", String.class)
                .getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
    }
}
