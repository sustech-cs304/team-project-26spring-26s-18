from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from crud.scheduler import create_todo, delete_todo, list_user_todos, list_user_todos_by_status, update_todo
from schemas.scheduler import (
    TodoCreateSchema,
    TodoReturnSchema,
    TodoStatusUpdateSchema,
    TodoUpdateSchema,
)
from utils.Result import Result
from utils.jwt_util import JWTUtil

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

VALID_TODO_STATUS = {"pending", "done", "cancelled"}
VALID_TODO_PRIORITY = {1, 2, 3}


def get_current_user_id(
    token: str | None = Header(None),
    authorization: str | None = Header(None)
) -> int | None:
    final_token = token

    if not final_token and authorization:
        final_token = authorization.strip()
        if final_token.lower().startswith("bearer "):
            final_token = final_token[7:].strip()

    if not final_token:
        return None

    return JWTUtil.parse_token(final_token)


def validate_todo_status(status: str | None) -> str | None:
    if status is None:
        return None
    if status not in VALID_TODO_STATUS:
        return None
    return status


def validate_todo_priority(priority: int | None) -> bool:
    if priority is None:
        return True
    return priority in VALID_TODO_PRIORITY


@router.post("/todo")
async def api_create_todo(
    todo: TodoCreateSchema,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_current_user_id)
):
    if user_id is None:
        return Result.error("请先登录")
    if not validate_todo_status(todo.status):
        return Result.error("状态不合法")
    if not validate_todo_priority(todo.priority):
        return Result.error("优先级不合法")

    try:
        obj = await create_todo(
            db=db,
            user_id=user_id,
            title=todo.title,
            content=todo.content,
            deadline=todo.deadline,
            status=todo.status,
            priority=todo.priority
        )
        return Result.success(TodoReturnSchema.model_validate(obj))
    except Exception:
        await db.rollback()
        return Result.error("数据库操作失败")


@router.get("/todo/list")
async def api_list_todos(
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_current_user_id)
):
    if user_id is None:
        return Result.error("请先登录")
    if status is not None and not validate_todo_status(status):
        return Result.error("状态不合法")

    try:
        if status is None:
            data = await list_user_todos(db, user_id)
        else:
            data = await list_user_todos_by_status(db, user_id, status)
        return Result.success([TodoReturnSchema.model_validate(obj) for obj in data])
    except Exception:
        await db.rollback()
        return Result.error("数据库操作失败")


@router.put("/todo/{todo_id}")
async def api_update_todo(
    todo_id: int,
    todo: TodoUpdateSchema,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_current_user_id)
):
    if user_id is None:
        return Result.error("请先登录")
    if todo.status is not None and not validate_todo_status(todo.status):
        return Result.error("状态不合法")
    if not validate_todo_priority(todo.priority):
        return Result.error("优先级不合法")

    try:
        obj = await update_todo(
            db=db,
            user_id=user_id,
            todo_id=todo_id,
            title=todo.title,
            content=todo.content,
            status=todo.status,
            priority=todo.priority,
            deadline=todo.deadline
        )
        if not obj:
            return Result.error("待办不存在")

        return Result.success(TodoReturnSchema.model_validate(obj))
    except Exception:
        await db.rollback()
        return Result.error("数据库操作失败")


@router.delete("/todo/{todo_id}")
async def api_delete_todo(
    todo_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_current_user_id)
):
    if user_id is None:
        return Result.error("请先登录")

    try:
        deleted = await delete_todo(db, user_id, todo_id)
        if not deleted:
            return Result.error("待办不存在")

        return Result.success()
    except Exception:
        await db.rollback()
        return Result.error("数据库操作失败")


@router.patch("/todo/{todo_id}/status")
async def api_update_todo_status(
    todo_id: int,
    body: TodoStatusUpdateSchema,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_current_user_id)
):
    if user_id is None:
        return Result.error("请先登录")
    if not validate_todo_status(body.status):
        return Result.error("状态不合法")

    try:
        obj = await update_todo(
            db=db,
            user_id=user_id,
            todo_id=todo_id,
            status=body.status
        )
        if not obj:
            return Result.error("待办不存在")

        return Result.success(TodoReturnSchema.model_validate(obj))
    except Exception:
        await db.rollback()
        return Result.error("数据库操作失败")
