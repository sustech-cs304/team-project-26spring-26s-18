from sqlalchemy.orm import Session
from models.user import User

# 用户登录
def login(db: Session, email: str, password: str):
	return db.query(User).filter(User.email == email, User.password == password).first()

# 插入新用户
def insert_user(db: Session, user: User):
	db.add(user)
	db.commit()
	db.refresh(user)
	return user

# 更新密码
def update_password_by_email(db: Session, email: str, password: str):
	user = db.query(User).filter(User.email == email).first()
	if user:
		user.password = password
		db.commit()
		db.refresh(user)
	return user

# 通过邮箱查找用户
def search_by_email(db: Session, email: str):
	return db.query(User).filter(User.email == email).first()

# 更新头像URL
def update_avatar_url(db: Session, user_id: int, avatar_url: str):
	user = db.query(User).filter(User.id == user_id).first()
	if user:
		user.avatarURL = avatar_url
		db.commit()
		db.refresh(user)
	return user

# 更新用户名和手机号
def update_info(db: Session, user_id: int, user_name: str, phone: str):
	user = db.query(User).filter(User.id == user_id).first()
	if user:
		user.userName = user_name
		user.phone = phone
		db.commit()
		db.refresh(user)
	return user
