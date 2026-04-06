from datetime import datetime
from typing import List

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.scheduler import PersonalTodo, OfficialCalendarEvent


async def create_todo(
    db: AsyncSession,
    user_id: int,
    title: str,
    deadline: datetime,
    content: str = None,
    status: str = "pending",
    priority: int = 2
) -> PersonalTodo:
    new_todo = PersonalTodo(
        user_id=user_id,
        title=title,
        content=content,
        status=status,
        priority=priority,
        deadline=deadline
    )
    db.add(new_todo)
    await db.commit()
    await db.refresh(new_todo)
    return new_todo


async def list_user_todos(db: AsyncSession, user_id: int) -> List[PersonalTodo]:
    result = await db.execute(
        select(PersonalTodo)
        .where(PersonalTodo.user_id == user_id)
        .order_by(PersonalTodo.deadline.asc(), PersonalTodo.id.asc())
    )
    return result.scalars().all()


async def update_todo(
    db: AsyncSession,
    user_id: int,
    todo_id: int,
    title: str = None,
    content: str = None,
    status: str = None,
    priority: int = None,
    deadline: datetime = None
) -> PersonalTodo | None:
    result = await db.execute(
        select(PersonalTodo).where(
            PersonalTodo.id == todo_id,
            PersonalTodo.user_id == user_id
        )
    )
    todo = result.scalar_one_or_none()
    if not todo:
        return None

    if title is not None:
        todo.title = title
    if content is not None:
        todo.content = content
    if status is not None:
        todo.status = status
    if priority is not None:
        todo.priority = priority
    if deadline is not None:
        todo.deadline = deadline

    await db.commit()
    await db.refresh(todo)
    return todo


async def delete_todo(db: AsyncSession, user_id: int, todo_id: int) -> bool:
    result = await db.execute(
        delete(PersonalTodo).where(
            PersonalTodo.id == todo_id,
            PersonalTodo.user_id == user_id
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
