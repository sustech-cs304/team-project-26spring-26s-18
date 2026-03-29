from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
	pass

class User(Base):
	__tablename__ = "user"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	userName: Mapped[str] = mapped_column(String(255), nullable=False)
	phone: Mapped[str] = mapped_column(String(255), nullable=False)
	email: Mapped[str] = mapped_column(String(255), nullable=True)
	password: Mapped[str] = mapped_column(String(255), nullable=False)
	avatarURL: Mapped[str] = mapped_column(String(255), nullable=False)

