package com.zifang.z.boot.datasource.starter;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import java.util.function.Function;

/**
 * 分页工具（Phase 7 扩展）。
 *
 * <p>0815 业务调用 {@code PageUtil.convert(page, mapper)} 将 Mybatis-Plus Page 转业务分页对象；
 * 本类在保留 0615 旧 {@link #of(int, int)} 的同时新增 {@link #convert(Page, Function)}。</p>
 */
public class PageUtil {

    public static <T> Page<T> of(int current, int size) {
        return new Page<>(current, size);
    }

    /**
     * Phase 7 扩展：将 Mybatis-Plus Page 数据转换为业务对象 Page。
     *
     * @param source  Mybatis-Plus Page 对象
     * @param mapper  单元素转换函数（Entity -> DTO）
     * @param <T>     源对象类型
     * @param <R>     目标对象类型
     * @return 转换后的业务 Page（保留分页信息）
     */
    @SuppressWarnings({"unchecked", "rawtypes"})
    public static <T, R> Page<R> convert(Page<T> source, Function<T, R> mapper) {
        if (source == null) {
            return new Page<>();
        }
        Page<R> result = new Page<>(source.getCurrent(), source.getSize(), source.getTotal());
        result.setRecords(source.getRecords().stream().map(mapper).collect(java.util.stream.Collectors.toList()));
        return result;
    }

    /**
     * Phase 7 扩展：将 Mybatis-Plus Page 转为 0815 业务用的 IPageable（IPageable 不在 z-boot 可见）。
     * <p>本方法在 z-boot-datasource-starter 中不直接依赖 z-util-core，而是通过运行时反射
     * 适配（避免在 z-boot 上引入 z-util-core 重型依赖）。调用方使用 {@code PageUtil.convert}
     * + 手动构造 {@code SimpleIPageable} 的方式自行适配；若 z-boot 后续引入 z-util-core 依赖，
     * 本方法可改为静态分派。</p>
     */
    @SuppressWarnings({"unchecked", "rawtypes"})
    public static <T> Object toIPageable(Page<T> source) {
        // Phase 7 存根：返回 null 调用方应当自行适配 SimpleIPageable。
        return null;
    }
}
