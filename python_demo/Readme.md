
# 后端项目使用方法

## 1. 如何启动项目

### 1.1 配置阿里云密钥的环境变量（这个信息在群里）
1. 以管理员身份打开 cmd 终端
2. 输入：
   ```cmd
   set OSS_ACCESS_KEY_ID=xxxxxxxxxxxxxx
   set OSS_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   再输入：
   ```cmd
   setx OSS_ACCESS_KEY_ID "%OSS_ACCESS_KEY_ID%"
   setx OSS_ACCESS_KEY_SECRET "%OSS_ACCESS_KEY_SECRET%"
   ```
   最后输入下面内容来检验阿里云配置是否生效了：
   ```cmd
   echo %OSS_ACCESS_KEY_ID%
   echo %OSS_ACCESS_KEY_SECRET%
   ```

### 1.2 配置百炼大模型密钥
密钥在微信群里，直接配置在“高级系统设置”的“环境变量”里就行。

### 1.3 下载 anaconda

### 1.4 使用本项目的 environment.yml 创建环境
```bash
conda env create -f environment.yml
```

### 1.5 激活环境
```bash
conda activate fastApi_env
```

### 1.6 运行项目
```bash
uvicorn main:app --reload
```

### 1.7 以后每次想要运行了，只需要重复 3、4 两步就行

### 1.8 添加依赖后更新environment.yml
如果自己添加了新的依赖，在上传之前先conda env export > environment.yml更新environment.yml文件
---

## 2. 项目结构
项目使用 FastAPI 框架，SQL 数据库使用 ORM，缓存使用 Redis，图片存储在阿里云 OSS。

### 2.1 main.py
main.py 是启动文件，其中的 app 是创建的 FastAPI 实例，所有的分支路由（router）都会挂载到这个 app 上，比如 user 的 router。
同时全局拦截器也是通过 `@app.middleware("http")` 来实现拦截并在后端校验是否登录了。
同时也配置了允许跨域请求：
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许的源，开发环境直接允许所有源
    allow_credentials=True,  # 允许携带 cookie
    allow_methods=["*"],  # 允许的请求方法
    allow_headers=["*"],  # 允许的请求头
)
```
这个在开发环境下是注释掉的，方便调试，真实使用环境需要取消注释。

### 2.2 _pycache_
这个是运行过程中报错时生成的缓存内容，没什么实际作用，可以看到每个文件夹下面都有这个内容。如果觉得影响美观，可以删除掉，但是下次报错时又会生成。

### 2.3 config 文件夹
这个文件夹下放的是各种配置文件：
- db_config.py 是 mysql 数据库的配置文件
- redis.py 是 redis 的配置文件

### 2.4 utils 文件夹
里面放的是各种包装好的工具：
- jwt_util 就是生成用户 jwt 令牌（用户 token）的工具包
- mail_util 就是发送邮件的工具包
- oss_util 就是将用户发送的图片上传到阿里云 OSS 并获取访问的 url 的工具包
- ai_util 就是调用 ai 的工具

### 2.5 routers、crud、models
这三个是主要的业务逻辑文件夹，每个文件夹中都会有一个名字相同文件，以 user.py 为例：

#### 2.5.1 routers
首先定义了 routers 中的 user.py，在其中定义：
```python
router = APIRouter(prefix="/user", tags=["user"])
```
然后在 main.py 中：
```python
from routers import user
app.include_router(user.router)
```
这样就将 user.py 挂载到了 app 上。
然后在 router 中定义具体方法，比如：
```python
@router.post("/sendCode")
```
前端就可以通过访问 `http://127.0.0.1:8000/user/sendCode` 调用对应的方法了。

#### 2.5.2 models
router 中定义的方法要操作数据库需要先在 models 中定义与数据库对应的类对象，比如 user.py 中定义的就是与用户相关的类对象。

#### 2.5.3 crud
在 models 定义完类对象后，在 crud 中定义对应增删改查的操作方法，然后在 routers 文件夹下的 user.py 类中就可以调用 crud 文件夹下对应的方法。

### 2.6 schemas 和 utils 文件夹中的 Result
这两个内容是为了包装返回内容。
Result.py 中定义了返回内容必须是：
```python
Result(code=x, message=xxxxx, data=xxxx)
```
这样的，code 是一位数字，表示返回是否成功，0 表示失败，1 表示成功，message 是返回失败时的具体报错信息，data 是返回的具体对象类，每个返回对应类是定义在 schemas 中。
比如下面这个（这个不是本项目相关内容，仅供参考）：
```json
{
  "code": 1, // 1表示成功
  "msg": "success", 
  "data": [ 
    // data中传入一个具体的数据类型，这个数据类型定义在schemas中，或者可以仅在schemas中定义字典中一个单独的数据的类型，然后在router中使用时方法中再定义使用该类型的数组
    {
      "id": 1,
      "name": "学工部",
      "createTime": "2022-09-01T23:06:29",
      "updateTime": "2022-09-01T23:06:29"
    },
    {
      "id": 2,
      "name": "教研部",
      "createTime": "2022-09-01T23:06:29",
      "updateTime": "2022-09-01T23:06:29"
    }
  ]
}
```

---

## 3. 接口文档
FastAPI 自带接口文档和调试工具，访问：
```
http://127.0.0.1:8000/docs
```
即可见到。