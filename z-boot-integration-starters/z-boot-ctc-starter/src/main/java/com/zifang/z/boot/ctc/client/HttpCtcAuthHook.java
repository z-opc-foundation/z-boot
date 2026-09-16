package com.zifang.z.boot.ctc.client;

import com.zifang.ctc.sso.hook.CtcAuthHook;
import com.zifang.ctc.sso.model.UserInfo;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.web.client.RestTemplate;

/**
 * 通过 HTTP 调用 z-ctc 服务实现的 CtcAuthHook (基于 io.github.yuku123:z-ctc-sso 的接口).
 *
 * <p>业务方在 z-opc-main-starter 实现 {@link CtcAuthHook} 时, 可直接 bean 化本类,
 * 或自定义 RPC 实现. 本类作为"HTTP 默认实现"提供, 适用于业务侧与 z-ctc 跨进程部署.</p>
 */
public class HttpCtcAuthHook implements CtcAuthHook {

    private static final Logger log = LogManager.getLogger(HttpCtcAuthHook.class);

    private final String serverAddr;
    private final RestTemplate restTemplate;

    public HttpCtcAuthHook(String serverAddr, int connectTimeoutMs, int readTimeoutMs) {
        this.serverAddr = serverAddr;
        org.springframework.http.client.SimpleClientHttpRequestFactory factory =
                new org.springframework.http.client.SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(connectTimeoutMs);
        factory.setReadTimeout(readTimeoutMs);
        this.restTemplate = new RestTemplate(factory);
    }

    @Override
    public UserInfo verifyToken(String token) {
        log.info("[HttpCtcAuthHook] verifyToken called, server={}", serverAddr);
        org.springframework.http.HttpHeaders headers = new org.springframework.http.HttpHeaders();
        headers.setBearerAuth(token);
        org.springframework.http.HttpEntity<String> entity = new org.springframework.http.HttpEntity<>(headers);
        return restTemplate.exchange(
                serverAddr + "/api/ctc/sso/verify",
                org.springframework.http.HttpMethod.GET,
                entity,
                UserInfo.class
        ).getBody();
    }

    @Override
    public String hookType() {
        return "http";
    }
}
