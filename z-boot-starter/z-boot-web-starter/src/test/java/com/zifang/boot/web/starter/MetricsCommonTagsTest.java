package com.zifang.boot.web.starter;

import io.micrometer.core.instrument.MeterRegistry;
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
 * 公共标签口径的验证：app / instance / env 三个标签自动出现在**每一条**指标上。
 *
 * <p>为什么这三个标签必须有：没有它们，指标只有名字没有归属 ——
 * "这个服务没埋点"和"这个服务挂了"在告警侧长得一模一样，而漏装标签的那个服务
 * 照常跑、照常健康，只是没人能按应用/实例/环境把它挑出来。
 *
 * <p>标签值取自应用自己的坐标（spring.application.name / server.port / 激活 profile），
 * 不是 starter 写死的：写死一个应用名会让别的应用继承到别人的名字，
 * 那比没有标签更坏（指标会安静地归到错误的应用名下）。
 */
@AutoConfigureObservability
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        classes = MetricsCommonTagsTest.TestApp.class,
        properties = {
                "spring.application.name=z-boot-metrics-selftest",
                "spring.profiles.active=selftest"
        })
class MetricsCommonTagsTest {

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
    void 每条指标都带app_instance_env三个公共标签() {
        registry.counter("zboot.common.tags.smoke").increment();

        assertThat(registry.get("zboot.common.tags.smoke").meter().getId().getTag("app"))
                .isEqualTo("z-boot-metrics-selftest");
        assertThat(registry.get("zboot.common.tags.smoke").meter().getId().getTag("env"))
                .isEqualTo("selftest");
        assertThat(registry.get("zboot.common.tags.smoke").meter().getId().getTag("instance"))
                .as("instance 至少要有一个能定位实例的值")
                .isNotBlank()
                .startsWith("z-boot-metrics-selftest");
    }

    @Test
    void 抓取出来的prometheus文本里带这三个标签() {
        registry.counter("zboot.common.tags.scrape").increment();

        ResponseEntity<String> resp = rest.getForEntity(
                "http://localhost:" + port + "/actuator/prometheus", String.class);

        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(resp.getBody())
                .contains("app=\"z-boot-metrics-selftest\"")
                .contains("env=\"selftest\"")
                .contains("instance=\"");
    }
}
