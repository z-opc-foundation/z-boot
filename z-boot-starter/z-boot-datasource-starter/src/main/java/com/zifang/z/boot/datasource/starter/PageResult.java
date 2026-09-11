package com.zifang.z.boot.datasource.starter;

import java.util.List;

/**
 * 分页结果（占位）
 */
public class PageResult<T> {
    private List<T> records;
    private long total;
    private int current;
    private int size;
    public List<T> getRecords() { return records; }
    public void setRecords(List<T> records) { this.records = records; }
    public long getTotal() { return total; }
    public void setTotal(long total) { this.total = total; }
    public int getCurrent() { return current; }
    public void setCurrent(int current) { this.current = current; }
    public int getSize() { return size; }
    public void setSize(int size) { this.size = size; }
}
