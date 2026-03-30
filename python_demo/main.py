from fastapi import Request, HTTPException, status
from utils.jwt_util import JWTUtil

from fastapi import FastAPI
# 导入routers文件夹中的各个文件的api
from routers import user, session, test
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],#允许的源，开发环境直接允许所有源
    allow_credentials=True,#允许携带cookie
    allow_methods=["*"],#允许的请求方法
    allow_headers=["*"],#允许的请求头
)
# @app.middleware("http")
# async def token_middleware(request: Request, call_next):
#     # 允许预检请求通过
#     if request.method == "OPTIONS":
#         return await call_next(request)
#     # 登录、注册、验证码、文档等接口不拦截
#     if any(path in str(request.url) for path in [
#         "/login", "/register", "/sendCode", "/test",
#         "/docs", "/openapi.json", "/redoc"
#     ]):
#         return await call_next(request)
#     token = request.headers.get("token")
#     if not token:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少token")
#     user_id = JWTUtil.parse_token(token)
#     if not user_id:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token无效")
#     request.state.user_id = user_id
#     return await call_next(request)
app.include_router(user.router)
app.include_router(session.router)
app.include_router(test.router)