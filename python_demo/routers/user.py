import time
print("[启动分析] routers/user.py 开始导入", time.time())
from utils.oss_util import OSSUtil
import base64

from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from config.db_config import get_db
from crud import user as crud_user

from schemas.login_return import LoginReturn
from utils.Result import Result

from utils.jwt_util import JWTUtil
from utils.mail_util import MailUtil
import random
from config.redis import set_key, get_key

router = APIRouter(prefix="/user", tags=["user"])

@router.post("/sendCode")
async def send_code(
	email: str = Body(..., embed=True)
):
	if not email:
		return Result.error("邮箱不能为空")
	# 生成六位验证码
	code = random.randint(100000, 999999)
	# 存储到redis并设置5分钟有效期
	try:
		await set_key(email, str(code), ex=300)
	except Exception as e:
		return Result.error(f"验证码存储失败: {str(e)}")
	print(f"验证码: {code}")
	# 发送邮件
	try:
		MailUtil.send_email(email, "验证码", f"您的验证码是: {code}")
	except Exception as e:
		return Result.error(f"邮件发送失败: {str(e)}")
	return Result.success()

@router.post("/register")
async def register(
	email: str = Body(..., embed=True),
	password: str = Body(..., embed=True),
	code: str = Body(..., embed=True),
	db: AsyncSession = Depends(get_db)
):
	# 验证验证码
	redis_code = await get_key(email)
	if redis_code != code:
		return Result.error("验证码错误")
	# 移除redis中的验证码
	await set_key(email, "", ex=1)
	# 查找用户
	db_user = await db.run_sync(lambda s: crud_user.search_by_email(s, email))
	if db_user:
		# 已存在则更新密码
		await db.run_sync(lambda s: crud_user.update_password_by_email(s, email, password))
	else:
		# 新用户注册
		from models.user import User
		new_user = User(email=email, password=password, userName="", phone="", avatarURL="")
		await db.run_sync(lambda s: crud_user.insert_user(s, new_user))
	# 获取最新用户信息
	user_return = await db.run_sync(lambda s: crud_user.search_by_email(s, email))
	login_return = LoginReturn(
		id=user_return.id,
		userName=user_return.userName,
		phone=user_return.phone,
		email=user_return.email,
		avatarURL=user_return.avatarURL,
		token=JWTUtil.generate_token(user_return.id)
	)
	return Result.success(login_return)

@router.post("/login")
async def login(
    email: str = Body(..., embed=True),
    password: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
	# 查询用户
	db_user = await db.run_sync(lambda s: crud_user.login(s, email, password))
	if db_user:
		login_return = LoginReturn(
			id=db_user.id,
			userName=db_user.userName,
			phone=db_user.phone,
			email=db_user.email,
			avatarURL=db_user.avatarURL,
			token=JWTUtil.generate_token(db_user.id)
		)
		return Result.success(login_return)
	else:
		return Result.error("没有该邮箱或密码错误")

@router.post("/updateInfo")
async def update_info(
	id: int = Body(..., embed=True),
	userName: str = Body(..., embed=True),
	phone: str = Body(..., embed=True),
	db: AsyncSession = Depends(get_db)
):
	# 调用crud层更新
	await db.run_sync(lambda s: crud_user.update_info(s, id, userName, phone))
	return Result.success()

@router.post("/updateAvatar")
async def update_avatar(
	id: int = Body(..., embed=True),
	image: str = Body(..., embed=True),
	db: AsyncSession = Depends(get_db)
):
	# 去掉前缀，获取纯base64数据
	if "," in image:
		base64_data = image.split(",", 1)[1]
	else:
		base64_data = image
	try:
		avatar_bytes = base64.b64decode(base64_data)
		file_name = f"avatars/user_{id}.png"
		url = OSSUtil.upload(avatar_bytes, file_name)
		# 更新数据库头像URL
		await db.run_sync(lambda s: crud_user.update_avatar_url(s, id, url))
		return Result.success(url)
	except Exception as e:
		print("上传文件失败", e)
		return Result.error("上传头像失败")


@router.post("/fetchCourses")
async def fetch_courses(
	user_id: int = Body(..., embed=True),
	tis_username: str = Body(..., embed=True),
	tis_password: str = Body(..., embed=True),
	db: AsyncSession = Depends(get_db)
):
	"""
	从 TIS 获取课程列表，上传到 OSS，URL 存入数据库。
	"""
	try:
		from utils.tis_util import fetch_courses_from_tis, courses_to_oss

		# 1. 登录 TIS 获取课程
		courses = fetch_courses_from_tis(tis_username, tis_password)

		# 2. 上传到 OSS，得到 URL
		url = courses_to_oss(user_id, courses)

		# 3. 将 URL 存入数据库
		await db.run_sync(lambda s: crud_user.update_course_config_url(s, user_id, url))

		return Result.success({"url": url, "course_count": len(courses)})
	except ValueError as e:
		return Result.error(str(e))
	except Exception as e:
		print("获取课程失败", e)
		return Result.error("获取课程失败，请检查 TIS 账号密码")