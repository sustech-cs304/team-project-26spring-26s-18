package com.example.interceptor;

import com.example.utils.JWTUtil;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Slf4j
@Component
public class TokenInterceptor implements HandlerInterceptor {
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        // 允许浏览器的预检请求通过
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            response.setStatus(HttpServletResponse.SC_OK);
            return false;
        }

        String requestUrl=request.getRequestURL().toString();
        if(requestUrl.contains("/login")||requestUrl.contains("/register")||requestUrl.contains("/sendCode")||requestUrl.contains("/test")){
            log.info("login/register/sendCode/test 请求, 不需要拦截");
            return true;
        }
        String token=request.getHeader("token");
        System.out.println(token);
        if(token==null||token.isEmpty()){
            response.setStatus(401);
            return false;
        }
        Integer userId = JWTUtil.parseToken(token);
        if(userId==null){
            response.setStatus(401);
            return false;
        }else {
            log.info("User ID from token: " + userId);
            request.setAttribute("userId",userId);
            return true;
        }
    }
}
