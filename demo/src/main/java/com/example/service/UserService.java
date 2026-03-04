package com.example.service;

import com.example.mapper.UserMapper;
import com.example.pojo.LoginReturn;
import com.example.pojo.User;
import com.example.utils.JWTUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class UserService {
    @Autowired
    UserMapper userMapper;
    public LoginReturn login(String email, String password) {
        User user = userMapper.login(email,password);
        if(user != null){
            LoginReturn loginReturn = new LoginReturn();
            loginReturn.setId(user.getId());
            loginReturn.setEmail(user.getEmail());
            loginReturn.setPhone(user.getPhone());
            loginReturn.setUserName(user.getUserName());
            loginReturn.setAvatarURL(user.getAvatarURL());
            loginReturn.setToken(JWTUtil.generateToken(user.getId()));
            return loginReturn;
        }else {
            return null;
        }
    }

    public LoginReturn register(User user) {

        if(userMapper.searchByEmail(user.getEmail())!=null){
            userMapper.updatePasswordByEmail(user);
        }else {
            userMapper.insert(user);
        }
        User userReturn= userMapper.searchByEmail(user.getEmail());
        LoginReturn loginReturn = new LoginReturn();
        loginReturn.setId(userReturn.getId());
        loginReturn.setEmail(userReturn.getEmail());
        loginReturn.setPhone(userReturn.getPhone());
        loginReturn.setUserName(userReturn.getUserName());
        loginReturn.setAvatarURL(userReturn.getAvatarURL());
        loginReturn.setToken(JWTUtil.generateToken(userReturn.getId()));
        return loginReturn;

    }

    public void updateAvatarURL(User user) {
        userMapper.updateAvatarURL(user);
    }

    public void updateInfo(Integer id, String userName, String phone) {
        userMapper.updateInfo(id,userName,phone);
    }
}
