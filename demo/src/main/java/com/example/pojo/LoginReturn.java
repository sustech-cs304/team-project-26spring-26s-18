package com.example.pojo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class LoginReturn {
    private Integer id;
    private String userName;
    private String phone;
    private String email;
    private String avatarURL;
    private String token;
}
