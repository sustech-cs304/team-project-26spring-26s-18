package com.example.utils;

import io.jsonwebtoken.JwtBuilder;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;

import java.util.Date;
import java.util.HashMap;
import java.util.Map;

public class JWTUtil {
    //密钥
    private static final String SECRET = "mysecretkey";
    //根据用户ID生成token
    public static String generateToken(Integer userId) {
        Map<String,Object>dataMap=new HashMap<>();
        dataMap.put("userId",userId);
        return Jwts.builder().signWith(SignatureAlgorithm.HS256, SECRET)
                .addClaims(dataMap)
                .setExpiration(new Date(System.currentTimeMillis() + 1000 * 60 * 60 * 24)) // 24小时后过期
                .compact();
    }
    //解析token获取用户ID，无效返回null
    public static Integer parseToken(String token) {
        try {
            Map<String, Object> claims = Jwts.parser()
                    .setSigningKey(SECRET)
                    .parseClaimsJws(token)
                    .getBody();
            Object userId = claims.get("userId");
            return userId == null ? null : ((Number) userId).intValue();
        } catch (Exception e) {
            // token无效或被篡改
            return null;
        }
    }
}
