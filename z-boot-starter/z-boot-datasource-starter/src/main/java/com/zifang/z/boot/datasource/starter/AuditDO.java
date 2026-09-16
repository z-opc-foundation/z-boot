package com.zifang.z.boot.datasource.starter;

import com.baomidou.mybatisplus.annotation.*;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * z-boot-datasource AuditDO 兼容层基类。
 *
 * <p>当 z-boot-datasource-starter 正式 JAR 中提供该类时，直接删除本类，
 * 所有 TeamDetailAuditDO / Entity 子类零修改切换。
 *
 * <p>字段约定与 MyBatis-Plus 全局配置对齐（application.yaml 中的 global-config）：
 * <pre>
 *   id:            雪花算法 ASSIGN_ID (Long)
 *   createTime:    INSERT 填充
 *   updateTime:    INSERT_UPDATE 填充
 *   createBy:      INSERT 填充
 *   updateBy:      INSERT_UPDATE 填充
 *   deleted:       @TableLogic (逻辑删除，值 0/1)
 * </pre>
 *
 * <p>⚠️ 注意：本类不使用 lombok，显式提供全部 getter/setter。
 */
public abstract class AuditDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableField(fill = FieldFill.INSERT)
    private String createBy;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private String updateBy;

    @TableLogic
    @TableField(value = "deleted", select = false)
    private Integer deleted;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public LocalDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(LocalDateTime v) {
        this.createTime = v;
    }

    public LocalDateTime getUpdateTime() {
        return updateTime;
    }

    public void setUpdateTime(LocalDateTime v) {
        this.updateTime = v;
    }

    public String getCreateBy() {
        return createBy;
    }

    public void setCreateBy(String v) {
        this.createBy = v;
    }

    public String getUpdateBy() {
        return updateBy;
    }

    public void setUpdateBy(String v) {
        this.updateBy = v;
    }

    public Integer getDeleted() {
        return deleted;
    }

    public void setDeleted(Integer v) {
        this.deleted = v;
    }
}
