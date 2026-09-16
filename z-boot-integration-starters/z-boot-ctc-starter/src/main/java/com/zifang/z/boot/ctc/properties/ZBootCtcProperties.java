package com.zifang.z.boot.ctc.properties;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * z-boot ctc starter 配置属性。
 *
 * <p>使用方在 application.yml 加:</p>
 * <pre>
 * z.boot.ctc:
 *   enabled: true
 *   mode: http
 *   server-addr: http://localhost:8888
 *   connect-timeout-ms: 3000
 *   read-timeout-ms: 5000
 * </pre>
 */
@ConfigurationProperties(prefix = "z.boot.ctc")
public class ZBootCtcProperties {

    private boolean enabled = false;
    private String mode = "http";
    private String serverAddr = "http://localhost:8888";
    private int connectTimeoutMs = 3000;
    private int readTimeoutMs = 5000;

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public String getMode() {
        return mode;
    }

    public void setMode(String mode) {
        this.mode = mode;
    }

    public String getServerAddr() {
        return serverAddr;
    }

    public void setServerAddr(String serverAddr) {
        this.serverAddr = serverAddr;
    }

    public int getConnectTimeoutMs() {
        return connectTimeoutMs;
    }

    public void setConnectTimeoutMs(int connectTimeoutMs) {
        this.connectTimeoutMs = connectTimeoutMs;
    }

    public int getReadTimeoutMs() {
        return readTimeoutMs;
    }

    public void setReadTimeoutMs(int readTimeoutMs) {
        this.readTimeoutMs = readTimeoutMs;
    }
}
