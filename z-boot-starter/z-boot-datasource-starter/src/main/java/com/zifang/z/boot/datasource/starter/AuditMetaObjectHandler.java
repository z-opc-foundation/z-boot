package com.zifang.z.boot.datasource.starter;

import com.baomidou.mybatisplus.core.handlers.MetaObjectHandler;
import org.apache.ibatis.reflection.MetaObject;

import java.time.LocalDateTime;

/**
 * z-boot-datasource AuditMetaObjectHandler 兼容层。
 *
 * <p>当 z-boot-datasource-starter 正式 JAR 提供该基类时，删除本类即可切换。
 *
 * <p>默认实现: 参照 z-boot 通用审计字段填充策略
 * <ul>
 *   <li>createTime: insert 时填充 LocalDateTime.now()</li>
 *   <li>updateTime: insert + update 时填充</li>
 *   <li>createBy / updateBy / createByName / updateByName 等业务字段由
 *       Starter 项目的 MybatisPlusConfig 覆盖 fill 方法注入</li>
 *   <li>deleted: 逻辑删除字段不由 MetaObjectHandler 填充（由 MyBatis-Plus 拦截器默认值处理）</li>
 * </ul>
 */
public abstract class AuditMetaObjectHandler implements MetaObjectHandler {

    private static final String CREATE_TIME = "createTime";
    private static final String UPDATE_TIME = "updateTime";

    @Override
    public void insertFill(MetaObject metaObject) {
        LocalDateTime now = LocalDateTime.now();
        strictInsertFill(metaObject, CREATE_TIME, LocalDateTime.class, now);
        strictInsertFill(metaObject, UPDATE_TIME, LocalDateTime.class, now);
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        strictUpdateFill(metaObject, UPDATE_TIME, LocalDateTime.class, LocalDateTime.now());
    }
}
