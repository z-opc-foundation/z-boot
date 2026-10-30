package com.zifang.boot.web.starter;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.prometheusmetrics.PrometheusMeterRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.autoconfigure.actuate.observability.AutoConfigureObservability;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 指标暴露口径的收口验证。
 *
 * <p>这组用例守两条容易悄悄退化、而退化后没人会发现的口径：
 * ①micrometer 的版本只能由 z-boot-parent 独供，本模块 pom 里不许出现字面量；
 * ②actuator 装上了不等于端点全开 —— 默认暴露面必须仍然只有 health。
 *
 * <p>@AutoConfigureObservability 不能省：spring-boot-test-autoconfigure 自带的
 * MetricsExportContributorAutoConfiguration 会把 management.metrics.export.defaults.enabled
 * 压成 false（避免测试互相污染指标），少了这个注解，PrometheusMeterRegistry 根本不装配，
 * /actuator/prometheus 也永远 404 —— 那是测试脚手架关的门，不是产品行为。
 */
@AutoConfigureObservability
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        classes = MetricExposureTest.TestApp.class,
        properties = {
                "management.endpoints.web.exposure.include=health,info,prometheus",
                "management.endpoint.prometheus.enabled=true"
        })
class MetricExposureTest {

    @Autowired
    private MeterRegistry registry;

    @Autowired
    private TestRestTemplate rest;

    @LocalServerPort
    private int port;

    @SpringBootApplication
    static class TestApp {
    }

    @Test
    void 容器里装的是Prometheus注册表() {
        assertThat(registry).isInstanceOf(PrometheusMeterRegistry.class);
    }

    @Test
    void prometheus端点可达且吐文本格式() {
        registry.counter("zboot.web.smoke", "k", "v").increment();
        ResponseEntity<String> resp = rest.getForEntity(
                "http://localhost:" + port + "/actuator/prometheus", String.class);

        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(resp.getBody())
                .contains("# HELP")
                .contains("zboot_web_smoke_total");
    }

    @Test
    void micrometer版本没在本模块被钉死() throws IOException {
        String pom = new String(Files.readAllBytes(
                new File("pom.xml").toPath()), StandardCharsets.UTF_8);
        Matcher m = Pattern.compile(
                "<dependency>\\s*<groupId>io\\.micrometer</groupId>.*?</dependency>",
                Pattern.DOTALL).matcher(pom);
        int found = 0;
        while (m.find()) {
            found++;
            assertThat(m.group())
                    .as("micrometer 依赖里不许带 <version>，版本只由 z-boot-parent 下发")
                    .doesNotContain("<version>");
        }
        assertThat(found).isPositive();
    }

    @Test
    void 实际解析出的micrometer版本就是地板版本() {
        String location = MeterRegistry.class.getProtectionDomain()
                .getCodeSource().getLocation().toString();
        Matcher m = Pattern.compile("micrometer-core-([0-9][^/]*?)(?:\\.jar)?$")
                .matcher(location);
        assertThat(m.find())
                .as("micrometer-core 应当来自本地仓的 jar，实际: " + location)
                .isTrue();
        // spring-boot-dependencies 3.3.13 钉的是 1.13.15；地板一抬，这条要跟着改
        assertThat(m.group(1)).isEqualTo("1.13.15");
    }
}
