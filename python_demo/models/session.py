from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, UTC
from .user import Base


class Session(Base):
	__tablename__ = "session"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	user_id: Mapped[int] = mapped_column(Integer, nullable=False)
	title: Mapped[str | None] = mapped_column(String(255), nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
	updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class SessionContent(Base):
	__tablename__ = "session_content"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	session_id: Mapped[int] = mapped_column(Integer, ForeignKey("session.id"), nullable=False)
	role: Mapped[str] = mapped_column(String(50), nullable=False)
	content: Mapped[str] = mapped_column(Text, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
	updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
