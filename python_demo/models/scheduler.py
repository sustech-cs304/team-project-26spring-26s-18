from sqlalchemy import Integer, String, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, UTC
from .user import Base


class PersonalTodo(Base):
	__tablename__ = "personal_todo"
	__table_args__ = (
		Index("idx_personal_todo_user_id", "user_id"),
		Index("idx_personal_todo_deadline", "deadline"),
	)

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	user_id: Mapped[int] = mapped_column(Integer, nullable=False)
	title: Mapped[str] = mapped_column(String(255), nullable=False)
	content: Mapped[str | None] = mapped_column(Text, nullable=True)
	# status convention: pending / done / cancelled
	status: Mapped[str] = mapped_column(String(50), default="pending")
	# priority convention: 1 low, 2 medium, 3 high
	priority: Mapped[int] = mapped_column(Integer, default=2)
	deadline: Mapped[datetime] = mapped_column(DateTime, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
	updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class OfficialCalendarEvent(Base):
	__tablename__ = "official_calendar_event"
	__table_args__ = (
		Index("idx_official_calendar_event_start_time", "start_time"),
		Index("idx_official_calendar_event_end_time", "end_time"),
	)

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	title: Mapped[str] = mapped_column(String(255), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	event_type: Mapped[str] = mapped_column(String(50), default="event")
	start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
	end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
	location: Mapped[str | None] = mapped_column(String(255), nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
	updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
