package com.example.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
//本类用于测试接口，不用关心其中具体内容
@RestController
public class TestController {
    @Autowired
    private RedisTemplate redisTemplate;
    @GetMapping("/test")
    public String testRedis() {
        redisTemplate.opsForValue().set("key", "value");
        Object key = redisTemplate.opsForValue().get("key");
        return key.toString();
    }
    @GetMapping("/test2")
    public String test2(){
        return "test2";
    }
}
