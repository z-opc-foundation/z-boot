package com.zifang.z.webide.starter;

import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;

/**
 * z-webide-spring-boot-starter 自动装配入口 (Phase 1 占位, 历史遗留文件, 不改名).
 * <p>
 * 类名沿用 {@code ZWebIdeAutoConfiguration} 保持二进制兼容, 但 starter artifactId 已
 * 重命名为 z-tool-webide-spring-boot-starter. @ConditionalOnClass 仍然引用 webide-api
 * 的 SPI 接口, 当主程序引入 z-tool-webide-api 时该条件成立.
 *
 * @author zifang
 */
@AutoConfiguration
@ConditionalOnClass(name = "com.zifang.z.tool.webide.api.IWebIdeUserManageService")
public class ZWebIdeAutoConfiguration {

    // Phase 4 起在此处 @Bean 注 Docker 默认实现
}
