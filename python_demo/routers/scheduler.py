import traceback
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from crud.scheduler import (
    build_blackboard_todo_payloads,
    build_term_label,
    build_course_schedule_payloads,
    build_official_calendar_payloads,
    create_todo,
    delete_todo,
    ensure_course_schedule_schema,
    expand_course_schedule_payloads,
    get_term_start_monday,
    get_user_todo,
    list_blackboard_todos,
    list_course_schedule_events,
    list_official_calendar_events,
    list_user_todos,
    list_user_todos_by_status,
    parse_import_rows,
    parse_course_schedule_xlsx,
    replace_blackboard_todos,
    replace_course_schedule_events,
    replace_official_calendar_events,
    update_todo,
)
from schemas.scheduler import (
    CourseScheduleEventSchema,
    OfficialCalendarEventSchema,
    SourceImportPayloadSchema,
    SourceImportResultSchema,
    has_datetime_range_overlap,
    is_range_todo_payload,
    TodoCreateSchema,
    TodoReturnSchema,
    TodoStatusUpdateSchema,
    TodoUpdateSchema,
    validate_todo_time_combination,
)
from utils.Result import Result
from utils.jwt_util import JWTUtil

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

VALID_TODO_STATUS = {"pending", "done", "cancelled"}
VALID_TODO_PRIORITY = {1, 2, 3}
VALID_OFFICIAL_DISPLAY_MODES = {"background", "event"}


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


def validate_merged_todo_times(todo_data: dict) -> str | None:
    return validate_todo_time_combination(
        deadline=todo_data.get("deadline"),
        start_time=todo_data.get("start_time"),
        end_time=todo_data.get("end_time"),
    )


def find_conflicting_range_todo(
    candidate_start,
    candidate_end,
    todos,
    exclude_todo_id: int | None = None,
):
    if not is_range_todo_payload(candidate_start, candidate_end):
        return None

    for todo in todos:
        if exclude_todo_id is not None and todo.id == exclude_todo_id:
            continue
        if todo.status == "cancelled":
            continue
        if not is_range_todo_payload(todo.start_time, todo.end_time):
            continue
        if has_datetime_range_overlap(candidate_start, candidate_end, todo.start_time, todo.end_time):
            return todo

    return None


def build_range_conflict_message(todo) -> str:
    return f"该日程时间块与现有专注事项冲突：{todo.title}"


def build_import_result(items, skipped_rows: list[str], replace_existing: bool, serializer):
    preview = [serializer.model_validate(item).model_dump(mode="json") for item in items[:20]]
    return SourceImportResultSchema(
        imported_count=len(items),
        skipped_count=len(skipped_rows),
        replace_existing=replace_existing,
        preview_count=len(preview),
        preview=preview,
        skipped_rows=skipped_rows[:20],
    )


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

    time_error = todo.get_time_validation_error()
    if time_error:
        return Result.error(time_error)

    try:
        existing_todos = await list_user_todos(db, user_id)
        conflict_todo = find_conflicting_range_todo(todo.start_time, todo.end_time, existing_todos)
        if conflict_todo:
            return Result.error(build_range_conflict_message(conflict_todo))

        obj = await create_todo(
            db=db,
            user_id=user_id,
            title=todo.title,
            content=todo.content,
            deadline=todo.deadline,
            start_time=todo.start_time,
            end_time=todo.end_time,
            status=todo.status,
            priority=todo.priority,
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
        existing = await get_user_todo(db, user_id, todo_id)
        if not existing:
            return Result.error("待办不存在")

        updates = todo.to_update_dict()
        merged_data = {
            "deadline": existing.deadline,
            "start_time": existing.start_time,
            "end_time": existing.end_time,
        }
        merged_data.update({key: updates[key] for key in ("deadline", "start_time", "end_time") if key in updates})

        time_error = validate_merged_todo_times(merged_data)
        if time_error:
            return Result.error(time_error)

        existing_todos = await list_user_todos(db, user_id)
        conflict_todo = find_conflicting_range_todo(
            merged_data.get("start_time"),
            merged_data.get("end_time"),
            existing_todos,
            exclude_todo_id=todo_id,
        )
        if conflict_todo:
            return Result.error(build_range_conflict_message(conflict_todo))

        obj = await update_todo(
            db=db,
            user_id=user_id,
            todo_id=todo_id,
            updates=updates,
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
            updates={"status": body.status},
        )
        if not obj:
            return Result.error("待办不存在")

        return Result.success(TodoReturnSchema.model_validate(obj))
    except Exception:
        await db.rollback()
        return Result.error("数据库操作失败")


@router.post("/official-calendar/import")
async def api_import_official_calendar(
    body: SourceImportPayloadSchema,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_current_user_id),
):
    if user_id is None:
        return Result.error("请先登录")

    try:
        rows = parse_import_rows(body.rows, body.content, body.content_type)
        payloads, skipped_rows = build_official_calendar_payloads(rows)
        if not payloads:
            return Result.error("没有可导入的官方校历数据")

        created = await replace_official_calendar_events(
            db=db,
            events=payloads,
            replace_existing=body.replace_existing,
        )
        return Result.success(
            build_import_result(created, skipped_rows, body.replace_existing, OfficialCalendarEventSchema)
        )
    except ValueError as error:
        await db.rollback()
        return Result.error(str(error))
    except Exception:
        await db.rollback()
        return Result.error("数据库操作失败")


@router.get("/official-calendar/list")
async def api_list_official_calendar(
    source_year: int | None = Query(None),
    display_mode: str | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_current_user_id),
):
    if user_id is None:
        return Result.error("请先登录")
    if display_mode is not None and display_mode not in VALID_OFFICIAL_DISPLAY_MODES:
        return Result.error("display_mode 仅支持 background 或 event")

    try:
        data = await list_official_calendar_events(
            db,
            source_year=source_year,
            display_mode=display_mode,
            start_time=start_time,
            end_time=end_time,
        )
        return Result.success([OfficialCalendarEventSchema.model_validate(obj) for obj in data])
    except Exception:
        await db.rollback()
        return Result.error("数据库操作失败")


@router.post("/course-schedule/import")
async def api_import_course_schedule(
    body: SourceImportPayloadSchema,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_current_user_id),
):
    if user_id is None:
        return Result.error("请先登录")

    try:
        await ensure_course_schedule_schema(db)
        rows = parse_import_rows(body.rows, body.content, body.content_type)
        payloads, skipped_rows = build_course_schedule_payloads(user_id, rows)
        if not payloads:
            return Result.error("没有可导入的课程表数据")

        created = await replace_course_schedule_events(
            db=db,
            user_id=user_id,
            events=payloads,
            replace_existing=body.replace_existing,
        )
        return Result.success(
            build_import_result(created, skipped_rows, body.replace_existing, CourseScheduleEventSchema)
        )
    except ValueError as error:
        await db.rollback()
        return Result.error(str(error))
    except Exception:
        await db.rollback()
        return Result.error("数据库操作失败")


@router.post("/course-schedule/import/xlsx")
async def api_import_course_schedule_xlsx(
    file: UploadFile = File(...),
    replace_existing: bool = Form(True),
    term: str = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_current_user_id),
):
    if user_id is None:
        return Result.error("请先登录")

    filename = (file.filename or "").lower()
    if not filename.endswith(".xlsx"):
        return Result.error("仅支持导入 .xlsx 课程表文件")

    try:
        await ensure_course_schedule_schema(db)
        term_start_monday = get_term_start_monday(term, year)
        import_term_label = build_term_label(term, year)
        content = await file.read()
        template_payloads, skipped_rows = parse_course_schedule_xlsx(content)
        payloads = expand_course_schedule_payloads(template_payloads, term_start_monday=term_start_monday)
        course_payloads = [
            {
                **payload,
                "term_label": payload.get("term_label") or import_term_label,
                "user_id": user_id,
                "import_source": "course_schedule_xlsx",
                "import_uid": (
                    f"{filename}:{term}:{year}:w{payload.get('week_start') or 'template'}"
                    f":d{payload.get('weekday') or 0}"
                    f":{payload.get('section_text') or 'unknown'}"
                    f":{payload.get('start_time')}"
                    f":{index}"
                ),
            }
            for index, payload in enumerate(payloads, start=1)
        ]
        created = await replace_course_schedule_events(
            db=db,
            user_id=user_id,
            events=course_payloads,
            replace_existing=replace_existing,
        )
        return Result.success(
            build_import_result(created, skipped_rows, replace_existing, CourseScheduleEventSchema)
        )
    except ValueError as error:
        await db.rollback()
        print("xlsx import ValueError:", repr(error))
        traceback.print_exc()
        return Result.error(str(error))
    except Exception as error:
        await db.rollback()
        print("xlsx import Exception:", repr(error))
        traceback.print_exc()
        return Result.error(f"数据库操作失败: {error}")

@router.get("/course-schedule/list")
async def api_list_course_schedule(
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_current_user_id),
):
    if user_id is None:
        return Result.error("请先登录")

    try:
        await ensure_course_schedule_schema(db)
        data = await list_course_schedule_events(db, user_id=user_id, start_time=start_time, end_time=end_time)
        return Result.success([CourseScheduleEventSchema.model_validate(obj) for obj in data])
    except Exception as error:
        await db.rollback()
        print("course schedule list Exception:", repr(error))
        traceback.print_exc()
        return Result.error(f"数据库操作失败: {error}")


@router.post("/blackboard/import")
async def api_import_blackboard_ics(
    body: SourceImportPayloadSchema,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_current_user_id),
):
    if user_id is None:
        return Result.error("请先登录")

    try:
        if not body.content:
            return Result.error("请提供 Blackboard ICS 内容")

        payloads, skipped_rows = build_blackboard_todo_payloads(user_id, body.content)
        if not payloads:
            return Result.error("没有可导入的 Blackboard 事项")

        created = await replace_blackboard_todos(
            db=db,
            user_id=user_id,
            todos=payloads,
            replace_existing=body.replace_existing,
        )
        return Result.success(
            build_import_result(created, skipped_rows, body.replace_existing, TodoReturnSchema)
        )
    except ValueError as error:
        await db.rollback()
        return Result.error(str(error))
    except Exception:
        await db.rollback()
        return Result.error("数据库操作失败")


@router.get("/blackboard/list")
async def api_list_blackboard_todos(
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_current_user_id),
):
    if user_id is None:
        return Result.error("请先登录")

    try:
        data = await list_blackboard_todos(db, user_id=user_id)
        return Result.success([TodoReturnSchema.model_validate(obj) for obj in data])
    except Exception:
        await db.rollback()
        return Result.error("数据库操作失败")
