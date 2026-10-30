package com.zifang.boot.web.starter.response;

import java.io.Serializable;

/**
 * 统一 REST 响应信封（z-boot-web-starter 直供，2026-10-30 Java17/SB3 火车补齐）。
 * <p>
 * 2026-10-30 按 z-biz 测试锚定的契约修正：JSON 顶层布尔字段名是
 * {@code success}（{@code {"success":true,"code":"0","message":"success","data":...}}），
 * 由 {@code code=="0"} 派生，不再暴露 {@code ok}。
 *
 * @param <T> 业务载荷类型
 */
public class Result<T> implements Serializable {

    private static final long serialVersionUID = 1L;

    public static final String CODE_OK = "0";

    private String code;
    private String message;
    private T data;

    public Result() {
    }

    public Result(String code, String message, T data) {
        this.code = code;
        this.message = message;
        this.data = data;
    }

    public static <T> Result<T> success(T data) {
        return new Result<>(CODE_OK, "success", data);
    }

    public static <T> Result<T> success(String message, T data) {
        return new Result<>(CODE_OK, message, data);
    }

    /** {@link #error(String, String)} 的别名 —— 老消费者（z-biz 等）用的是 fail(...) 口径 */
    public static <T> Result<T> fail(String message) {
        return error("500", message);
    }

    public static <T> Result<T> fail(String code, String message) {
        return error(code, message);
    }

    public static <T> Result<T> error(String code, String message) {
        return new Result<>(code, message, null);
    }

    public static <T> Result<T> error(String code, String message, T data) {
        return new Result<>(code, message, data);
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public T getData() {
        return data;
    }

    public void setData(T data) {
        this.data = data;
    }

    /** JSON 字段名 success：code=="0" 即 true（消费方契约锚定） */
    public boolean isSuccess() {
        return CODE_OK.equals(code);
    }

    @Override
    public String toString() {
        return "Result{success=" + isSuccess() + ", code='" + code + "', message='" + message + "', data=" + data + '}';
    }
}
