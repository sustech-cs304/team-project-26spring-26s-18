from sqlalchemy import desc

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from models.session import Session, SessionContent
from typing import List

# Session 相关的 CRUD 操作
async def create_session(db: AsyncSession, user_id: int, title: str = None) -> Session:
    new_session = Session(user_id=user_id, title=title)
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return new_session

async def get_sessions_by_user_id(db: AsyncSession, user_id: int) -> List[Session]:
    result = await db.execute(select(Session).where(Session.user_id == user_id))
    return result.scalars().all()

async def delete_session_by_id(db: AsyncSession, session_id: int) -> None:
    # 先删除所有相关的 session_content
    await db.execute(delete(SessionContent).where(SessionContent.session_id == session_id))
    # 再删除 session
    await db.execute(delete(Session).where(Session.id == session_id))
    await db.commit()

async def update_session_title_by_id(db: AsyncSession, session_id: int, new_title: str) -> None:
    await db.execute(update(Session).where(Session.id == session_id).values(title=new_title))
    await db.commit()

# SessionContent 相关的 CRUD 操作
async def create_content(db: AsyncSession, session_id: int, role: str, content: str) -> SessionContent:
    new_content = SessionContent(session_id=session_id, role=role, content=content)
    db.add(new_content)
    await db.commit()
    await db.refresh(new_content)
    return new_content

async def get_content_by_session_id(db: AsyncSession, session_id: int) -> List[SessionContent]:
    result = await db.execute(select(SessionContent).where(SessionContent.session_id == session_id))
    return result.scalars().all()

async def delete_content_by_session_id(db: AsyncSession, session_id: int) -> None:
    await db.execute(delete(SessionContent).where(SessionContent.session_id == session_id))
    await db.commit()
# 查询某session最近n条内容
async def get_last_n_content_by_session_id(db: AsyncSession, session_id: int, n: int = 5) -> List[SessionContent]:
    result = await db.execute(
        select(SessionContent)
        .where(SessionContent.session_id == session_id)
        .order_by(desc(SessionContent.created_at))
        .limit(n)
    )
    # 返回按时间升序排列（从旧到新）
    items = result.scalars().all()
    return list(reversed(items))