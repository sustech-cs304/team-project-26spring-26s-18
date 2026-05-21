"""
file_manager.py — 文件管理助手 API

接口列表：
  POST /file/execute    执行自然语言命令（SSE 流式推送思维链 + 结果）
  POST /file/confirm    确认危险操作（删除/移动）
  GET  /file/tree       获取目录树（右侧资源管理器）
  POST /file/workspace  验证并返回工作目录信息
"""

import sys
import io
import os
import json
import uuid
import asyncio
import threading
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, Query
from fastapi.responses import StreamingResponse
from utils.Result import Result

# 将仓库根目录加入 sys.path，使 file_helper 包可被导入
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

router = APIRouter(prefix="/file", tags=["file"])

# 存储待确认的危险操作  {operation_id: {files, action, workspace, ...}}
_pending: dict = {}

# 需要用户确认的动作
_DESTRUCTIVE = {"delete", "move", "clean"}


# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────

def _build_tree(path: str, depth: int = 3) -> dict:
    """递归构建目录树"""
    p = Path(path)
    if not p.exists():
        return {"error": f"路径不存在: {path}"}
    if p.is_file():
        return {
            "name": p.name,
            "path": str(p),
            "type": "file",
            "size": p.stat().st_size,
        }
    node = {"name": p.name, "path": str(p), "type": "dir", "children": []}
    if depth <= 0:
        return node
    try:
        entries = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        for child in entries:
            node["children"].append(_build_tree(str(child), depth - 1))
    except PermissionError:
        pass
    return node


def _get_affected_files(intent: dict, workspace: str) -> list:
    """
    根据解析结果计算受影响的文件列表（不执行操作）。
    用于危险操作的预览确认。
    """
    from file_helper.file_atomic_ops import get_files
    from file_helper.file_query import (
        filter_by_extension, filter_by_name_contains,
        filter_by_content_contains, filter_by_date, filter_by_size,
    )
    from datetime import datetime

    source = intent.get("source") or workspace
    if source in (".", "", None):
        source = workspace
    if not os.path.isabs(source):
        source = os.path.join(workspace, source)
    # 安全校验：不允许超出 workspace
    if not os.path.abspath(source).startswith(os.path.abspath(workspace)):
        source = workspace

    recursive = intent.get("params", {}).get("recursive", False)
    files = get_files(source, recursive)

    for f in intent.get("filters", []):
        ftype = f.get("type", "")
        val = f.get("value")
        if isinstance(val, dict) and "value" in val:
            val = val["value"]

        if ftype == "extension" and val:
            files = filter_by_extension(files, val)
        elif ftype == "name_contains" and val:
            files = filter_by_name_contains(files, val)
        elif ftype == "content_contains" and val:
            files = filter_by_content_contains(files, val)
        elif ftype in ("modified", "date"):
            before = datetime.fromisoformat(f["before"]) if f.get("before") else None
            after = datetime.fromisoformat(f["after"]) if f.get("after") else None
            files = filter_by_date(files, before=before, after=after)
        elif ftype == "size":
            files = filter_by_size(files, **{k: v for k, v in f.items()
                                             if k in ("min_size", "max_size", "min_mb", "max_mb")})
    return files


# ─────────────────────────────────────────────
# SSE 生成器
# ─────────────────────────────────────────────

async def _execute_stream(command: str, workspace: str, operation_id: str):
    """SSE 生成器：在子线程运行 file_helper，通过 asyncio.Queue 推送事件"""
    loop = asyncio.get_event_loop()
    q: asyncio.Queue = asyncio.Queue()

    class _SSECapture(io.TextIOBase):
        """重定向 stdout，将 print 内容塞入 SSE 队列"""
        def write(self, text: str):
            if text and text.strip():
                loop.call_soon_threadsafe(q.put_nowait, {
                    "type": "log",
                    "message": text.rstrip("\n"),
                })
            return len(text) if text else 0
        def flush(self):
            pass

    def _run():
        old_stdout = sys.stdout
        sys.stdout = _SSECapture()
        try:
            from file_helper.agent import FileAgent

            agent = FileAgent(workspace)

            for step in agent.run(command):
                stype = step["type"]

                if stype == "tis_required":
                    # 存储待整理操作，供 /file/resumeOrganize 使用
                    _pending[operation_id] = {
                        "type": "tis_organize",
                        "files": step.get("files", []),
                        "target_dir": step.get("target_dir"),
                        "workspace": workspace,
                    }
                    loop.call_soon_threadsafe(q.put_nowait, {
                        **step,
                        "operation_id": operation_id,
                    })
                elif stype == "confirm_required":
                    # 存储待确认操作，供 /file/confirm 使用
                    _pending[operation_id] = {
                        "action": step["action"],
                        "files": [f["path"] for f in step["files"]],
                        "target_dir": step.get("target_dir"),
                        "workspace": workspace,
                    }
                    loop.call_soon_threadsafe(q.put_nowait, {
                        "type": "confirm_required",
                        "operation_id": operation_id,
                        **step,
                    })
                else:
                    loop.call_soon_threadsafe(q.put_nowait, step)

        except Exception as e:
            loop.call_soon_threadsafe(q.put_nowait, {
                "type": "error",
                "message": str(e),
            })
        finally:
            sys.stdout = old_stdout
            loop.call_soon_threadsafe(q.put_nowait, None)

    threading.Thread(target=_run, daemon=True).start()

    # 从队列读取并 yield SSE 事件
    while True:
        msg = await q.get()
        if msg is None:
            break
        yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'type': 'end'}, ensure_ascii=False)}\n\n"


# ─────────────────────────────────────────────
# 接口定义
# ─────────────────────────────────────────────

@router.post("/execute")
async def execute(
    command: str = Body(..., embed=True),
    workspace: str = Body(..., embed=True),
):
    """
    执行自然语言文件命令。
    以 SSE 流式返回思维链日志和最终结果。

    非破坏性操作（search/organize/analyze）直接返回结果。
    破坏性操作（delete/move/clean）返回待确认文件列表，需调用 /file/confirm。
    """
    operation_id = str(uuid.uuid4())
    return StreamingResponse(
        _execute_stream(command, workspace, operation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/confirm")
async def confirm(
    operation_id: str = Body(..., embed=True),
    confirmed: bool = Body(..., embed=True),
):
    """
    确认或取消危险操作。

    confirmed=true  → 执行之前预览的文件操作
    confirmed=false → 取消操作
    """
    if operation_id not in _pending:
        return Result.error("操作已过期或不存在，请重新执行命令")

    op = _pending.pop(operation_id)

    if not confirmed:
        return Result.success({"success_count": 0, "failed_count": 0, "skipped_count": 0, "cancelled": True})

    try:
        from file_helper.file_batch_ops import batch_delete, batch_move, BatchResult

        files = op["files"]
        action = op["action"]

        if action == "delete":
            result: BatchResult = batch_delete(files, to_trash=True, confirm=False)
        elif action == "move":
            target = op.get("target_dir") or op["workspace"]
            if not os.path.isabs(target):
                target = os.path.join(op["workspace"], target)
            result: BatchResult = batch_move(files, target, overwrite=True)
        elif action == "clean":
            result: BatchResult = batch_delete(files, to_trash=True, confirm=False)
        else:
            return Result.error(f"不支持的操作: {action}")

        skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
        return Result.success({
            "success_count": len(result.success),
            "failed_count": len(result.failed),
            "skipped_count": skipped,
        })
    except Exception as e:
        return Result.error(f"执行失败: {e}")


@router.get("/tree")
async def tree(
    path: str = Query(..., description="目录路径"),
    depth: int = Query(3, description="展开深度，默认3层"),
):
    """
    获取指定路径的目录树（用于右侧资源管理器）。
    """
    if not os.path.exists(path):
        return Result.error(f"路径不存在: {path}")
    return Result.success(_build_tree(path, depth=max(1, min(depth, 5))))


@router.post("/workspace")
async def workspace(
    path: str = Body(..., embed=True),
):
    """
    验证工作目录是否存在，返回目录基本信息。
    """
    if not os.path.isdir(path):
        return Result.error(f"目录不存在: {path}")

    p = Path(path)
    try:
        file_count = sum(1 for _ in p.rglob("*") if _.is_file())
    except Exception:
        file_count = -1

    return Result.success({
        "path": str(p.resolve()),
        "name": p.name,
        "file_count": file_count,
    })


# ─────────────────────────────────────────────
# TIS 课程爬取（SSE 流式推送）
# ─────────────────────────────────────────────

async def _fetch_tis_stream(tis_username: str, tis_password: str, operation_id: str):
    """SSE 生成器：运行 TIS 爬虫，边爬边推送日志，完成后更新 user_config.json"""
    loop = asyncio.get_event_loop()
    q: asyncio.Queue = asyncio.Queue()

    class _TISCapture(io.TextIOBase):
        def write(self, text: str):
            if text and text.strip():
                loop.call_soon_threadsafe(q.put_nowait, {
                    "type": "log",
                    "message": text.rstrip("\n"),
                })
            return len(text) if text else 0
        def flush(self): pass

    def _run():
        old_stdout = sys.stdout
        sys.stdout = _TISCapture()
        try:
            from utils.tis_util import fetch_courses_from_tis
            import json as _json

            courses = fetch_courses_from_tis(tis_username, tis_password)

            # 更新 file_helper/user_config.json
            config_path = os.path.join(_REPO_ROOT, "file_helper", "user_config.json")
            config = {"courses": []}
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = _json.load(f)
            config["courses"] = courses
            with open(config_path, "w", encoding="utf-8") as f:
                _json.dump(config, f, ensure_ascii=False, indent=2)

            print(f"[完成] 课程数据已更新，共 {len(courses)} 门课程")
            loop.call_soon_threadsafe(q.put_nowait, {
                "type": "tis_done",
                "course_count": len(courses),
                "operation_id": operation_id,
            })
        except ValueError as e:
            loop.call_soon_threadsafe(q.put_nowait, {"type": "error", "message": str(e)})
        except Exception as e:
            loop.call_soon_threadsafe(q.put_nowait, {"type": "error", "message": f"TIS 获取失败: {e}"})
        finally:
            sys.stdout = old_stdout
            loop.call_soon_threadsafe(q.put_nowait, None)

    threading.Thread(target=_run, daemon=True).start()

    while True:
        msg = await q.get()
        if msg is None:
            break
        yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'type': 'end'}, ensure_ascii=False)}\n\n"


@router.post("/fetchTIS")
async def fetch_tis(
    tis_username: str = Body(..., embed=True),
    tis_password: str = Body(..., embed=True),
    operation_id: str = Body(..., embed=True),
):
    """SSE：运行 TIS 爬虫，实时推送日志到思维链，完成后更新课程数据"""
    return StreamingResponse(
        _fetch_tis_stream(tis_username, tis_password, operation_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.post("/resumeOrganize")
async def resume_organize(
    operation_id: str = Body(..., embed=True),
):
    """TIS 获取成功后，继续执行课程整理操作"""
    if operation_id not in _pending:
        return Result.error("操作已过期，请重新执行命令")

    op = _pending.pop(operation_id)
    if op.get("type") != "tis_organize":
        return Result.error("操作类型不匹配")

    try:
        from file_helper.file_batch_ops import organize_by_course
        result = organize_by_course(op["files"], op["target_dir"])
        return Result.success({
            "success_count": len(result.success),
            "failed_count": len(result.failed),
        })
    except Exception as e:
        return Result.error(f"整理失败: {e}")
