package com.example.controller;


import com.aliyun.oss.ClientBuilderConfiguration;
import com.aliyun.oss.OSS;
import com.aliyun.oss.OSSClientBuilder;
import com.aliyun.oss.common.auth.CredentialsProviderFactory;
import com.aliyun.oss.common.auth.EnvironmentVariableCredentialsProvider;
import com.aliyun.oss.common.comm.SignVersion;
import com.aliyun.oss.model.PutObjectResult;
import com.example.pojo.LoginReturn;
import com.example.pojo.Result;
import com.example.pojo.User;
import com.example.service.UserService;
import jakarta.mail.MessagingException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.web.bind.annotation.*;

import java.io.ByteArrayInputStream;
import java.util.Map;
import java.util.Objects;
import java.util.Random;

//解决跨域请求问题
@Slf4j
@CrossOrigin(origins = "*")
@RestController
@RequestMapping("/user")
public class UserController {
    @Autowired
    private UserService userService;
    @Autowired
    private RedisTemplate<Object, Object> redisTemplate;
    @Autowired
    private JavaMailSender mailSender;
    //阿里云OSS配置
    private static final String OSS_ENDPOINT = "https://oss-cn-beijing.aliyuncs.com";
    private static final String OSS_REGION = "cn-beijing";
//    private static final String OSS_ACCESS_KEY_ID = System.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"); // 从环境变量获取
//    private static final String OSS_ACCESS_KEY_SECRET = System.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"); // 从环境变量获取
    private static final String OSS_BUCKET_NAME = "experience-tree"; //
    //登录/注册方法
    @PostMapping("/login")
    public Result login(@RequestBody Map<String, String> loginInfo) {
        String email = loginInfo.get("email");
        String password = loginInfo.get("password");
        LoginReturn loginReturn = userService.login(email,password);
        if (loginReturn!=null) {
            return Result.success(loginReturn);
        } else {
            return Result.error("没有该邮箱或密码错误");
        }
    }
    //注册或者更新密码方法
    @PostMapping("/register")
    public Result register(@RequestBody Map<String, String> registerInfo) {
        String email = registerInfo.get("email");
        String password = registerInfo.get("password");
        String code = registerInfo.get("code");
        User user = new User();
        user.setEmail(email);
        user.setPassword(password);
        //验证验证码
        if(Objects.equals(redisTemplate.opsForValue().get(email), code)){
            //移除redis中的验证码
            redisTemplate.delete(email);
            LoginReturn loginReturn= userService.register(user);
            System.out.println(loginReturn);
            return Result.success(loginReturn);
        }else{
            return Result.error("验证码错误");
        }
    }
    //发送验证码方法
    @PostMapping("/sendCode")
    public Result sendCode(@RequestBody Map<String, String> requestInfo) throws MessagingException {
        String email = requestInfo.get("email");
        //生成六位验证码并存储
        Random random = new Random();
        int code = 100000 + random.nextInt(900000); // 保证6位
        System.out.println(code);
        redisTemplate.opsForValue().set(email, String.valueOf(code),5,java.util.concurrent.TimeUnit.MINUTES);
        //使用SMTP发送验证码到用户邮箱
        SimpleMailMessage message = new SimpleMailMessage();
        message.setFrom("17692267492@163.com");
        message.setTo(email);
        message.setSubject("验证码");
        message.setText("您的验证码是: " + code);
        mailSender.send(message);
        return Result.success();
    }
    //更新用户头像并上传到OSS方法
    @PostMapping("/updateAvatar")
    public Result updateAvatar(@RequestBody Map<String, String> avatarInfo) {
        Integer id = Integer.valueOf(avatarInfo.get("id"));
        String avatarData = avatarInfo.get("image");//这个是Base64编码的字符串
        //前端用的是readAsDataURL，它生成的字符串是data:image/png;base64,xxxxxx格式，去掉前缀
        String base64Data = avatarData.substring(avatarData.indexOf(",") + 1);
        byte[] avatarBytes = java.util.Base64.getDecoder().decode(base64Data);
        String fileName = "avatars/user_" + id + ".png"; // OSS上的路径和文件名
        try {
            String url = uploadToOSS(avatarBytes, fileName);
            //更新用户头像URL到数据库
            User user = new User();
            user.setId(id);
            user.setAvatarURL(url);
            userService.updateAvatarURL(user);
            log.info("用户{}头像上传成功，URL：{}", id, url);
            return Result.success(url);
        } catch (Exception e) {
            System.out.println("上传文件失败");
            System.out.println(e);
            return Result.error("上传头像失败");
        }
    }
    @PostMapping("/updateInfo")
    public Result updateInfo(@RequestBody Map<String, String> info) {
        System.out.println("进入更新用户信息接口，接收到的数据：" + info);
        Integer id = Integer.valueOf(info.get("id"));
        String userName = info.get("userName");
        String phone = info.get("phone");
        User user = new User();
        userService.updateInfo(id,userName,phone);
        return Result.success();
    }


    //其中fileName是文件名，同时也是文件在OSS上的存储路径
    private String uploadToOSS(byte[] fileBytes, String fileName) throws Exception {
        // 从环境变量中获取访问凭证。运行本代码示例之前，请先配置环境变量
        EnvironmentVariableCredentialsProvider credentialsProvider = CredentialsProviderFactory
                .newEnvironmentVariableCredentialsProvider();

        // 创建 OSSClient 实例
        ClientBuilderConfiguration clientBuilderConfiguration = new ClientBuilderConfiguration();
        // 显式声明使用 V4 签名算法
        clientBuilderConfiguration.setSignatureVersion(SignVersion.V4);
        OSS ossClient = OSSClientBuilder.create()
                .endpoint(OSS_ENDPOINT)
                .credentialsProvider(credentialsProvider)
                .region(OSS_REGION)
                .build();

        try {
            // 2. 上传文件
            PutObjectResult result = ossClient.putObject(OSS_BUCKET_NAME, fileName, new ByteArrayInputStream(fileBytes));
            //打印result中所有信息
            System.out.println("ETag: " + result.getETag());
            System.out.println("RequestId: " + result.getRequestId());
            System.out.println("Response: " + result.getResponse());
            if (result.getResponse() != null) {
                System.out.println("StatusCode: " + result.getResponse().getStatusCode());
                System.out.println("Headers: " + result.getResponse().getHeaders());
                System.out.println("Content: " + result.getResponse().getContent());
            }

            // 生成文件访问URL
            return "https://" + OSS_BUCKET_NAME + "." + OSS_ENDPOINT.substring(8) + "/" + fileName;
        } finally {
            // 关闭OSSClient
            if (ossClient != null) {
                ossClient.shutdown();
            }
        }
    }
}
