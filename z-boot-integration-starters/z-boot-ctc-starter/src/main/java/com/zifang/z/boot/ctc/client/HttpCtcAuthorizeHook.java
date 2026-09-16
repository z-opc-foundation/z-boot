package com.zifang.z.boot.ctc.client;

import com.zifang.ctc.sso.hook.CtcAuthorizeHook;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

/**
 * 通过 HTTP 调用 z-ctc 服务实现的 CtcAuthorizeHook (基于 io.github.yuku123:z-ctc-sso 的接口).
 */
public class HttpCtcAuthorizeHook implements CtcAuthorizeHook {

    private static final Logger log = LogManager.getLogger(HttpCtcAuthorizeHook.class);

    private final String serverAddr;
    private final RestTemplate restTemplate;

    public HttpCtcAuthorizeHook(String serverAddr) {
        this.serverAddr = serverAddr;
        this.restTemplate = new RestTemplate();
    }

    @Override
    public boolean hasPermission(String userId, String permissionCode) {
        log.debug("[HttpCtcAuthorizeHook] hasPermission userId={} code={}", userId, permissionCode);
        Map<?, ?> body = restTemplate.getForObject(
                serverAddr + "/api/ctc/sso/hasPermission?userId=" + userId + "&permissionCode=" + permissionCode,
                Map.class
        );
        return body != null && Boolean.TRUE.equals(body.get("hasPermission"));
    }

    @Override
    public boolean hasRole(String userId, String roleCode) {
        log.debug("[HttpCtcAuthorizeHook] hasRole userId={} role={}", userId, roleCode);
        Map<?, ?> body = restTemplate.getForObject(
                serverAddr + "/api/ctc/sso/hasRole?userId=" + userId + "&roleCode=" + roleCode,
                Map.class
        );
        return body != null && Boolean.TRUE.equals(body.get("hasRole"));
    }

    @Override
    public String hookType() {
        return "http";
    }
}
