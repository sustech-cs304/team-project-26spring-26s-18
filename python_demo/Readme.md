后端项目使用方法:
# 1.如何启动项目
## 1.1 配置阿里云密钥的环境变量（这个信息在群里）
    1.以管理员⾝份打开cmd终端
    2.输⼊：
        set OSS_ACCESS_KEY_ID=xxxxxxxxxxxxxx
        set OSS_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    再输⼊：
        setx OSS_ACCESS_KEY_ID"%OSS_ACCESS_KEY_ID%"
        setx OSS_ACCESS_KEY_SECRET"%OSS_ACCESS_KEY_SECRET%"
        最后输⼊下⾯内容来检验阿⾥云配置是否⽣效了：
        echo%OSS_ACCESS_KEY_ID%
        echo%OSS_ACCESS_KEY_SECRET%

## 1.2 下载anaconda

## 1.3 从你的environment.yml创建环境
conda env create -f environment.yml

## 1.4 激活环境
conda activate fastApi_env

## 1.5 运行项目
uvicorn main:app --reload

## 1.6 以后每次想要运行了，只需要重复3、4两步就行

# 2.项目结构：
项目使用fastApi框架，sql数据库使用ORM，缓存使用redis，图片存储在阿里云OSS
## 2.1 main.py
main.py是启动文件，其中的app是创建的FastAPI实例，
所有的分支路由(router)都会挂载到这个app上，比如user的router,
同时全局拦截器也是通过@app.middleware("http")来实现拦截并在后端校验是否登录了
同时也配置了允许跨域请求:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],#允许的源，开发环境直接允许所有源
        allow_credentials=True,#允许携带cookie
        allow_methods=["*"],#允许的请求方法
        allow_headers=["*"],#允许的请求头
    )

## 2.2 _pycache_
这个是运行过程中报错时生成的缓存内容，没什么实际作用，可以看到每个文件夹下面都有这个内容，
如果觉得影响美观，可以删除掉，但是下次报错时又会生成

## 2.3 config文件夹
这个文件夹下放的是各种配置文件:
db_config.py是mysql数据库的配置文件,
redis.py是redis的配置文件

## 2.4 utils文件夹
里面放的是各种包装好的工具:
jwt_util就是生成用户jwt令牌(用户token)的工具包,
mail_util就是发送邮件的工具包,
oss_util就是将用户发送的图片上传到阿里云OSS并获取访问的url的工具包
## 2.5 routers、crud、models
这三个是主要的业务逻辑文件夹，每个文件夹中都会有一个名字相同文件，以user.py为例:
### 2.5.1 routers
首先定义了routers中的user.py,在其中定义router = APIRouter(prefix="/user", tags=["user"]),
然后在main.py中from routers import user并app.include_router(user.router),这样就将user.py挂载到了app上。
然后在router中定义具体方法,比如@router.post("/sendCode"),
然后前端就可以通过访问http://127.0.0.1:8000/user/sendCode 调用对应的方法了
### 2.5.2 models
router中定义的方法要操作数据库需要先在models中定义与数据库对应的类对象，比如user.py中定义的就是与用户相关的类对象
### 2.5.3 crud
在models定义完类对象后在crud中定义对应增删改查的操作方法，然后在routers文件夹下的user.py类中就可以调用crud文件夹下对应的方法
## 2.6 schemas 和 utils文件夹中的Result
这两个内容是为了包装返回内容
Resutl.py中定义了返回内容必须是Result(code=x, message=xxxxx, data=xxxx)这样的，
code是一位数字，表示返回是否成功，0表示失败，1表示成功,
message是返回失败时的具体报错信息,
data是返回的具体对象类，每个返回对应类是定义在schemas中
比如下面这个(这个不是本项目相关内容，仅供参考):
{
  "code": 1, //1表示成功
  "msg": "success", 
  "data": [ 
    //data中传入一个具体的数据类型，这个数据类型定义在schemas中，或者可以仅在schemas中定义字典中一个单独的数据的类型，然后在router中使用时方法中再定义使用该类型的数组
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
# 3.接口文档
fastapi自带接口文档和调试工具，访问http://127.0.0.1:8000/docs 即可见到