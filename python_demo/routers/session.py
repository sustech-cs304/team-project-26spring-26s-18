import time
print("[启动分析] routers/session.py 开始导入", time.time())
from fastapi import APIRouter, Depends, HTTPException,Body
from sqlalchemy.orm import Session as DBSession
from typing import List, Optional
from schemas.session import Session as SessionSchema, SessionContent as SessionContentSchema
from utils.Result import Result
from schemas.session import Session as SessionSchema, SessionContent as SessionContentSchema
from crud.session import (
    get_sessions_by_user_id,
    get_content_by_session_id,
    create_session,
    create_content,
    delete_content_by_session_id,
    delete_session_by_id,
    update_session_title_by_id,
    get_last_n_content_by_session_id
)
from config.db_config import get_db
from utils.ai_util import ai_chat

router = APIRouter(prefix="/session", tags=["session"])

@router.get("/user/{user_id}")
async def api_get_sessions_by_user_id(user_id: int, db: DBSession = Depends(get_db)):
    data = await get_sessions_by_user_id(db, user_id)
    data = [SessionSchema.model_validate(obj) for obj in data]
    return Result.success(data)

@router.get("/{session_id}/content")
async def api_get_content_by_session_id(session_id: int, db: DBSession = Depends(get_db)):
    data = await get_content_by_session_id(db, session_id)
    data = [SessionContentSchema.model_validate(obj) for obj in data]
    return Result.success(data)

@router.post("/create")
async def api_create_session(
    user_id: int = Body(..., embed=True),
    title: str = Body(None, embed=True),
    db: DBSession = Depends(get_db)
):
    obj = await create_session(db, user_id, title)
    data = SessionSchema.model_validate(obj)
    return Result.success(data)


@router.post("/aicontent")
async def api_create_ai_content(
    session_id: int = Body(..., embed=True),
    content: str = Body(..., embed=True),
    files: Optional[List[str]] = Body(None, embed=True),         # base64内容数组
    file_types: Optional[List[str]] = Body(None, embed=True),    # 文件类型数组
    file_names: Optional[List[str]] = Body(None, embed=True),    # 文件名数组
    db: DBSession = Depends(get_db)
):
    # 统一由ai_chat处理消息存储和AI回复
    msgs = await ai_chat(
        db=db,
        session_id=session_id,
        content=content,
        files=files,
        file_types=file_types,
        file_names=file_names
    )
    from schemas.session import SessionContent as SessionContentSchema
    return Result.success([
        SessionContentSchema.model_validate(m) for m in msgs
    ])

@router.delete("/content/{content_id}")
async def api_delete_content(content_id: int, db: DBSession = Depends(get_db)):
    await db.execute(delete(SessionContent).where(SessionContent.id == content_id))
    await db.commit()
    return Result.success()

@router.delete("/{session_id}")
async def api_delete_session(session_id: int, db: DBSession = Depends(get_db)):
    await delete_session_by_id(db, session_id)
    return Result.success()

@router.put("/{session_id}/title")
async def api_update_session_title(session_id: int, new_title: str, db: DBSession = Depends(get_db)):
    await update_session_title_by_id(db, session_id, new_title)
    return Result.success()
