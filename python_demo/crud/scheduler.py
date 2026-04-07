from datetime import datetime
from typing import List

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.scheduler import PersonalTodo, OfficialCalendarEvent


TODO_ORDER_TIME = func.coalesce(PersonalTodo.start_time, PersonalTodo.deadline, PersonalTodo.end_time)


async def create_todo(
    db: AsyncSession,
    user_id: int,
    title: str,
    content: str = None,
    status: str = "pending",
    priority: int = 2,
    deadline: datetime | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None
) -> PersonalTodo:
    new_todo = PersonalTodo(
        user_id=user_id,
        title=title,
        content=content,
        status=status,
        priority=priority,
        deadline=deadline,
        start_time=start_time,
        end_time=end_time,
    )
    db.add(new_todo)
    await db.commit()
    await db.refresh(new_todo)
    return new_todo


async def get_user_todo(db: AsyncSession, user_id: int, todo_id: int) -> PersonalTodo | None:
    result = await db.execute(
        select(PersonalTodo).where(
            PersonalTodo.id == todo_id,
            PersonalTodo.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_user_todos(db: AsyncSession, user_id: int) -> List[PersonalTodo]:
    result = await db.execute(
        select(PersonalTodo)
        .where(PersonalTodo.user_id == user_id)
        .order_by(TODO_ORDER_TIME.asc(), PersonalTodo.id.asc())
    )
    return result.scalars().all()


async def list_user_todos_by_status(db: AsyncSession, user_id: int, status: str) -> List[PersonalTodo]:
    result = await db.execute(
        select(PersonalTodo)
        .where(
            PersonalTodo.user_id == user_id,
            PersonalTodo.status == status,
        )
        .order_by(TODO_ORDER_TIME.asc(), PersonalTodo.id.asc())
    )
    return result.scalars().all()


async def update_todo(
    db: AsyncSession,
    user_id: int,
    todo_id: int,
    updates: dict
) -> PersonalTodo | None:
    todo = await get_user_todo(db, user_id, todo_id)
    if not todo:
        return None

    for field, value in updates.items():
        setattr(todo, field, value)

    await db.commit()
    await db.refresh(todo)
    return todo


async def delete_todo(db: AsyncSession, user_id: int, todo_id: int) -> bool:
    result = await db.execute(
        delete(PersonalTodo).where(
            PersonalTodo.id == todo_id,
            PersonalTodo.user_id == user_id,
        )
    )
    await db.commit()
    return result.rowcount > 0


async def list_official_calendar_events(db: AsyncSession) -> List[OfficialCalendarEvent]:
    result = await db.execute(
        select(OfficialCalendarEvent)
        .order_by(OfficialCalendarEvent.start_time.asc(), OfficialCalendarEvent.id.asc())
    )
    return result.scalars().all()
