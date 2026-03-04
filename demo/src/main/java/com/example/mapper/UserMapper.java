package com.example.mapper;

import com.example.pojo.User;
import org.apache.ibatis.annotations.*;

@Mapper
public interface UserMapper {
    //用户登录
    @Select("SELECT id,userName,phone,email,avatarURL FROM user WHERE email = #{email} AND password = #{password}")
    User login(@Param("email") String email, @Param("password") String password);
    //插入新用户
    @Insert("INSERT INTO user (userName, phone, email,password,avatarURL) VALUES (#{userName}, #{phone}, #{email},#{password},#{avatarURL})")
    void insert(User user);
    //更新密码
    @Update("UPDATE user SET password = #{password} WHERE email = #{email}")
    void updatePasswordByEmail(User user);
    //通过邮箱查找用户
    @Select("SELECT id,userName,phone,email,avatarURL FROM user WHERE email = #{email}")
    User searchByEmail(String email);

    @Update("UPDATE user SET avatarURL = #{avatarURL} WHERE id = #{id}")
    void updateAvatarURL(User user);

    @Update("UPDATE user SET userName = #{userName}, phone = #{phone} WHERE id = #{id}")
    void updateInfo(Integer id, String userName, String phone);
}
