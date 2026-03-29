package com.example.pojo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class Result {
    private Integer code;//1成功 0失败
    private String message;//错误信息
    private Object data;//返回的数据

    public static Result success() {
        Result result = new Result();
        result.setCode(1);
        result.setMessage("success");
        result.setData(null);
        return result;
    }
    public static Result success(Object data) {
        Result result = new Result();
        result.setCode(1);
        result.setMessage("success");
        result.setData(data);
        return result;
    }
    public static Result error(String message) {
        Result result = new Result();
        result.setCode(0);
        result.setMessage(message);
        result.setData(null);
        return result;
    }

}