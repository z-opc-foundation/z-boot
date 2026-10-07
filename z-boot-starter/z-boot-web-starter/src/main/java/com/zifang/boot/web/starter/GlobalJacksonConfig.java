package com.zifang.boot.web.starter;

import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.databind.JsonSerializer;
import com.fasterxml.jackson.databind.SerializerProvider;
import com.fasterxml.jackson.databind.module.SimpleModule;
import org.springframework.boot.autoconfigure.jackson.Jackson2ObjectMapperBuilderCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.IOException;

/**
 * 全局 Jackson 配置：将 Long / Long[] 类型序列化为字符串。
 * <p>
 * 原因：JS Number 最大安全精度为 2^53 ≈ 9.007 × 10^15，雪花 ID 是 19 位整数，
 * 超过此精度后末位会被截断/舍入，导致前端用 Number 类型接收后会丢失精度、
 * 无法回传到后端匹配记录（如 scenario_instance_id 末尾 71 误差 → "项目不存在"）。
 * <p>
 * 本配置下沉到 z-boot-jackson-starter 后由所有 web 模块统一继承（不再各模块各自实现）。
 * 仅序列化数字 / 数字数组时改为字符串，反序列化保持原有 Number 兼容。
 *
 */
@Configuration
public class GlobalJacksonConfig {

    @Bean
    public Jackson2ObjectMapperBuilderCustomizer longAsStringCustomizer() {
        return builder -> {
            SimpleModule module = new SimpleModule("ZBootLongAsString");
            module.addSerializer(Long.class, new LongToStringSerializer(false));
            module.addSerializer(Long.TYPE, new LongToStringSerializer(true));
            module.addSerializer(long[].class, new LongArrayToStringSerializer());
            builder.modulesToInstall(module);
        };
    }

    static final class LongToStringSerializer extends JsonSerializer<Long> {
        private final boolean primitive;

        LongToStringSerializer(boolean primitive) {
            this.primitive = primitive;
        }

        @Override
        public void serialize(Long value, JsonGenerator gen, SerializerProvider serializers)
                throws IOException {
            if (value == null) {
                gen.writeNull();
                return;
            }
            gen.writeString(value.toString());
        }

        @SuppressWarnings("unchecked")
        @Override
        public Class<Long> handledType() {
            return primitive ? Long.TYPE : Long.class;
        }
    }

    static final class LongArrayToStringSerializer extends JsonSerializer<long[]> {
        @Override
        public void serialize(long[] value, JsonGenerator gen, SerializerProvider serializers)
                throws IOException {
            if (value == null) {
                gen.writeNull();
                return;
            }
            gen.writeStartArray();
            for (long l : value) {
                gen.writeString(Long.toString(l));
            }
            gen.writeEndArray();
        }
    }
}