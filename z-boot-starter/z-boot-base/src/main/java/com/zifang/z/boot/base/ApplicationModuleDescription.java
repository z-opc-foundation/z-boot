package com.zifang.z.boot.base;

public interface ApplicationModuleDescription {

    /**
     * @return 应用标准名称
     */
    String getApplicationName();

    /**
     * @return 当前模块的根路径
     *
     */
    String getBasePackage();

}
