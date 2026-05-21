"""
File Helper Flask API Server

提供前端调用的 RESTful API：
- POST /api/files/chat     执行自然语言命令
- POST /api/files/preview  预览命令结果（不实际执行）
- GET  /api/files/tree      获取目录树结构
- POST /api/files/analyze   分析目录统计信息
- GET  /api/files/list      列出目录内容（浅层，用于展开）
"""

import os
import sys
import io
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr

from flask import Flask, request, jsonify
from flask_cors import CORS

# ── 切换到项目根目录，确保 file_helper 包能被正确导入 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

# ── 从已安装的 file_helper 包导入 ─────────────────────
from file_helper import FileHelper, run_command
from file_helper.file_batch_ops import BatchResult, organize_by_course
from file_helper.file_atomic_ops import get_files, exists, is_file, is_dir

app = Flask(__name__)
CORS(app, supports_credentials=True)


# ── 工具函数 ─────────────────────────────────────────────────

def capture_output(func, *args, **kwargs):
    """
    执行 func，捕获 stdout/stderr，返回 (返回值, 输出日志列表)
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    result = None
    logs = []

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            result = func(*args, **kwargs)
    except Exception as e:
        logs.append({"type": "error", "text": f"执行异常: {e}"})
        return None, logs

    output = stdout_capture.getvalue()
    err_output = stderr_capture.getvalue()

    for line in output.splitlines():
        line = line.rstrip()
        if not line:
            continue
        log_type = "step"
        if "===" in line or "---" in line:
            log_type = "info"
        elif "\u2705" in line or "成功" in line or "已创建" in line or "已删除" in line:
            log_type = "success"
        elif "\u26a0\ufe0f" in line or "警告" in line:
            log_type = "warn"
        elif "\u274c" in line or "失败" in line or "Error" in line:
            log_type = "error"
        elif line.startswith("  \u2192") or line.startswith("  -"):
            log_type = "step"
        logs.append({"type": log_type, "text": line})

    if err_output:
        for line in err_output.splitlines():
            line = line.rstrip()
            if line:
                logs.append({"type": "error", "text": line})

    return result, logs


def _build_thinking_chain(intent: dict, workspace: str) -> list:
    """
    根据解析后的意图，构建 AI 思维链日志。
    展示：意图识别 -> 文件查找 -> 执行方法选择
    """
    thinking_logs = []
    action = intent.get("action") or ""
    summary = intent.get("summary", "")
    source = intent.get("source", "") or workspace
    target = intent.get("target", "")
    filters = intent.get("filters", [])
    params = intent.get("params", {})

    action_names = {
        "search": "搜索/查找文件",
        "move": "移动文件",
        "copy": "复制文件",
        "delete": "删除文件",
        "rename": "重命名文件",
        "organize": "整理/分类文件",
        "clean": "清理文件",
        "mkdir": "创建目录",
        "analyze": "分析文件",
    }
    action_display = action_names.get(action, action) if action else "未知操作"
    thinking_logs.append({
        "type": "thinking",
        "text": "💭 理解用户意图：「" + (summary or intent.get("original", "")) + "」"
    })
    thinking_logs.append({
        "type": "info",
        "text": "📋 识别的操作类型：" + action_display
    })
    if source:
        thinking_logs.append({"type": "info", "text": "📂 源目录：" + source})
    if filters:
        filter_desc = []
        for f in filters:
            ftype = f.get("type", "")
            val = f.get("value", "")
            if ftype == "extension":
                desc = ", ".join(val) if isinstance(val, list) else str(val)
                filter_desc.append("扩展名：" + desc)
            elif ftype == "name_contains":
                filter_desc.append("名称包含：" + str(val))
            elif ftype == "size":
                filter_desc.append("文件大小条件：" + str(val))
            elif ftype == "date":
                filter_desc.append("修改时间：" + str(val) + " 天前")
        if filter_desc:
            thinking_logs.append({"type": "info", "text": "🔍 过滤条件：" + (" | ".join(filter_desc))})
    if target:
        thinking_logs.append({"type": "info", "text": "🎯 目标目录：" + target})
    if params:
        param_items = []
        if params.get("organize_mode"):
            param_items.append("整理模式：" + params["organize_mode"])
        if params.get("preview"):
            param_items.append("【预览模式】不实际移动文件")
        if params.get("recursive"):
            param_items.append("包含子目录")
        if param_items:
            thinking_logs.append({"type": "info", "text": "⚙️ 参数：" + (" | ".join(param_items))})
    func_names = {
        "search": "find_files() → 搜索文件",
        "move": "batch_move() → 批量移动",
        "copy": "batch_copy() → 批量复制",
        "delete": "batch_delete() → 批量删除",
        "rename": "batch_rename() → 批量重命名",
        "organize": "organize_by_*() → 按规则分类",
        "clean": "clean_*() → 清理文件",
        "mkdir": "os.makedirs() → 创建目录",
        "analyze": "analyze() → 分析统计",
    }
    if action and action in func_names:
        thinking_logs.append({"type": "thinking", "text": "🔧 将执行函数：" + func_names[action]})
    thinking_logs.append({"type": "info", "text": "─── 开始执行 ───"})
    return thinking_logs


def build_tree(path, max_depth=3, current_depth=0):
    """递归构建目录树结构（字典列表）"""
    path = Path(path)
    if not path.exists():
        return []

    items = []
    try:
        entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    except PermissionError:
        return []

    for entry in entries:
        item = {
            "name": entry.name,
            "path": str(entry),
            "type": "dir" if entry.is_dir() else "file",
            "size": entry.stat().st_size if entry.is_file() else 0,
        }
        if entry.is_dir() and current_depth < max_depth:
            item["children"] = build_tree(entry, max_depth, current_depth + 1)
            item["expanded"] = False
        items.append(item)

    return items


def result_to_dict(result):
    """将 BatchResult 转为可 JSON 序列化的字典"""
    if result is None:
        return {"success": [], "failed": [], "skipped": [],
                "success_count": 0, "failed_count": 0, "skipped_count": 0}
    d = result.to_dict()
    for key in ["success", "failed", "skipped"]:
        for item in d.get(key, []):
            if "path" in item and isinstance(item["path"], (Path,)):
                item["path"] = str(item["path"])
    return d


# ── API 路由 ────────────────────────────────────────────────

@app.route("/api/files/chat", methods=["POST"])
def api_chat():
    """
    执行自然语言文件管理命令

    Body:
        workspace: str   工作目录
        command:   str   自然语言命令
        confirmed: bool  是否已确认（用户看过文件列表后确认）

    Returns:
        { logs: [...], result: {...} }
    """
    data = request.get_json(force=True, silent=True) or {}
    workspace = data.get("workspace", "")
    command = data.get("command", "").strip()
    confirmed = data.get("confirmed", False)

    if not workspace or not Path(workspace).exists():
        return jsonify({"error": "invalid workspace: " + workspace}), 400
    if not command:
        return jsonify({"error": "please input command"}), 400

    helper = FileHelper(workspace=workspace)

    # 1. 解析意图，构建思维链
    intent = helper.parse(command)
    thinking_logs = _build_thinking_chain(intent, workspace)

    # 2. 判断是否是危险操作（delete, move, clean）
    dangerous_actions = {"delete", "move", "clean"}
    action = intent.get("action", "") or ""
    is_dangerous = action in dangerous_actions or \
                   any(a.get("action") in dangerous_actions for a in intent.get("actions", []))

    # 3. 危险操作需要用户确认
    if is_dangerous and not confirmed:
        # 返回预览信息，提示用户确认
        result = _preview_intent(intent, workspace)
        thinking_logs.append({
            "type": "warn",
            "text": "⚠️ 检测到危险操作！请确认后再执行。"
        })
        thinking_logs.append({
            "type": "info",
            "text": "📋 预览结果（实际执行请按「确认执行」按钮）"
        })
        preview_logs = result.get("preview_logs", [])
        thinking_logs.extend(preview_logs)

        return jsonify({
            "logs": thinking_logs,
            "result": result.get("result", {}),
            "need_confirm": True,  # 告诉前端需要确认
            "files_to_affect": result.get("files_to_affect", []),  # 将要操作的文件列表
        })

    # 4. 已确认或非危险操作，执行
    result, exec_logs = capture_output(helper.run, command, True, skip_confirm=True)

    # 5. 合并日志：思维链在前，执行日志在后
    all_logs = thinking_logs + exec_logs

    return jsonify({
        "logs": all_logs,
        "result": result_to_dict(result),
        "need_confirm": False,
    })


@app.route("/api/files/chat_stream", methods=["POST"])
def api_chat_stream():
    """
    流式执行自然语言文件管理命令（SSE 实时推送日志）

    使用 queue 在后台线程和 Flask SSE 之间传递日志，
    实现真正的边执行边推送。
    """
    import json as _json
    import queue
    import threading
    from flask import Response

    # ── 调试：打印收到的原始数据 ─────────────────────
    raw_body = request.get_data(as_text=True)
    print(f"[DEBUG] Raw body: {raw_body[:200]}", flush=True)
    # ─────────────────────────────────────────────────────

    data = request.get_json(force=True, silent=True) or {}
    print(f"[DEBUG] Parsed JSON: workspace={data.get('workspace')!r}, command={data.get('command')!r}", flush=True)
    workspace = data.get("workspace", "")
    workspace = workspace.replace(chr(92), chr(47))
    command = data.get("command", "").strip()
    confirmed = data.get("confirmed", False)

    if not workspace or not Path(workspace).exists():
        def err_gen():
            yield f"event: error\ndata: {_json.dumps({'type': 'error', 'text': 'invalid workspace'}, ensure_ascii=False)}\n\n"
        return Response(err_gen(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})

    if not command:
        def err_gen():
            yield f"event: error\ndata: {_json.dumps({'type': 'error', 'text': 'please input command'}, ensure_ascii=False)}\n\n"
        return Response(err_gen(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})

    helper = FileHelper(workspace=workspace)

    def event_stream():
        """SSE 事件流生成器"""
        # 1. 解析意图（同步，先给用户看到解析结果）
        try:
            intent = helper.parse(command)
        except Exception as e:
            yield f"event: error\ndata: {_json.dumps({'type': 'error', 'text': f'解析失败：{e}'}, ensure_ascii=False)}\n\n"
            return

        thinking_logs = _build_thinking_chain(intent, workspace)
        for log in thinking_logs:
            yield f"event: log\ndata: {_json.dumps(log, ensure_ascii=False)}\n\n"

        # 2. 危险操作需要确认
        dangerous_actions = {"delete", "move", "clean"}
        action = intent.get("action", "") or ""
        is_dangerous = action in dangerous_actions or \
                       any(a.get("action") in dangerous_actions for a in intent.get("actions", []))

        if is_dangerous and not confirmed:
            result = _preview_intent(intent, workspace)
            yield f"event: log\ndata: {_json.dumps({'type': 'warn', 'text': '⚠️ 检测到危险操作！请确认后再执行。'}, ensure_ascii=False)}\n\n"
            for log in result.get("preview_logs", []):
                yield f"event: log\ndata: {_json.dumps(log, ensure_ascii=False)}\n\n"
            yield f"event: confirm_required\ndata: {_json.dumps({'files': result.get('files_to_affect', [])}, ensure_ascii=False)}\n\n"
            return

        # 3. 创建日志队列和结果容器
        log_queue = queue.Queue()
        exec_result = [None]
        exec_error = [None]

        def run_with_progress():
            """在后台线程中执行，实时推送日志"""
            try:
                result = helper.run(
                    command, True, skip_confirm=True,
                    progress_callback=log_queue.put
                )
                exec_result[0] = result
            except Exception as e:
                exec_error[0] = e

        # 启动后台线程
        thread = threading.Thread(target=run_with_progress)
        thread.start()

        # 4. 实时推送执行日志（从 queue 中读取）
        while True:
            try:
                log = log_queue.get(timeout=60)
                yield f"event: log\ndata: {_json.dumps(log, ensure_ascii=False)}\n\n"
            except queue.Empty:
                if not thread.is_alive():
                    break
                continue

        thread.join()

        # 5. 检查执行错误
        if exec_error[0]:
            yield f"event: log\ndata: {_json.dumps({'type': 'error', 'text': f'执行异常：{exec_error[0]}'}, ensure_ascii=False)}\n\n"
            yield f"event: done\ndata: {_json.dumps({'error': str(exec_error[0])}, ensure_ascii=False)}\n\n"
            return

        # 6. 推送最终结果
        yield f"event: done\ndata: {_json.dumps(result_to_dict(exec_result[0]), ensure_ascii=False)}\n\n"

    return Response(event_stream(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})


def _preview_intent(intent, workspace):
    """
    预览意图操作的文件列表（不实际执行）
    返回将要操作的文件列表
    """
    files_to_affect = []
    preview_logs = []
    action = intent.get("action", "") or ""
    source = intent.get("source", "") or workspace
    target = intent.get("target", "")
    filters = intent.get("filters", [])

    from file_helper.file_atomic_ops import get_files
    from file_helper.file_query import (
        filter_by_extension, filter_by_name_contains,
        filter_by_size, filter_by_date
    )

    def apply_filters(file_list, filter_list):
        """将过滤器依次应用到文件列表（路径字符串列表）"""
        result = file_list
        for f in filter_list:
            ftype = f.get("type", "")
            val = f.get("value", "")
            if isinstance(val, dict) and "value" in val:
                val = val["value"]
            if ftype == "extension":
                if isinstance(val, str):
                    val = [v.strip().lower().lstrip(".") for v in val.split(",") if v.strip()]
                result = filter_by_extension(result, val)
            elif ftype == "name_contains":
                if isinstance(val, list):
                    result = filter_by_name_contains(result, val)
                else:
                    result = filter_by_name_contains(result, [val])
            elif ftype == "size":
                kwargs = {}
                if "min" in val:
                    kwargs["min_size"] = val["min"]
                if "max" in val:
                    kwargs["max_size"] = val["max"]
                result = filter_by_size(result, **kwargs)
            elif ftype == "date":
                result = filter_by_date(result, days_ago=val.get("days_ago", 0))
        return result

    try:
        if action in ("delete", "move", "copy"):
            # 先获取所有文件，再手动应用过滤条件（get_files 不支持 filters 参数）
            # 处理相对路径：拼接 workspace
            base_path = source if source and source != "." else workspace
            if not os.path.isabs(base_path):
                base_path = os.path.join(workspace, base_path)
            found = get_files(base_path, recursive=True)
            found = apply_filters(found, filters)

            if action == "delete":
                preview_logs.append({"type": "info", "text": f"📁 将删除以下文件（共 {len(found)} 个）："})
                for f in found[:50]:
                    preview_logs.append({"type": "step", "text": f"  - {f}"})
                if len(found) > 50:
                    preview_logs.append({"type": "info", "text": f"  ... 还有 {len(found) - 50} 个文件"})
                files_to_affect = found

            elif action == "move":
                preview_logs.append({"type": "info", "text": f"📁 将移动以下文件到「{target}」（共 {len(found)} 个）："})
                for f in found[:50]:
                    preview_logs.append({"type": "step", "text": f"  - {f}"})
                if len(found) > 50:
                    preview_logs.append({"type": "info", "text": f"  ... 还有 {len(found) - 50} 个文件"})
                files_to_affect = found

            elif action == "copy":
                preview_logs.append({"type": "info", "text": f"📁 将复制以下文件到「{target}」（共 {len(found)} 个）："})
                for f in found[:50]:
                    preview_logs.append({"type": "step", "text": f"  - {f}"})
                if len(found) > 50:
                    preview_logs.append({"type": "info", "text": f"  ... 还有 {len(found) - 50} 个文件"})
                files_to_affect = found

        elif action == "clean":
            preview_logs.append({"type": "info", "text": f"🧹 将执行清理操作"})
            files_to_affect = []

        else:
            preview_logs.append({"type": "info", "text": f"📋 将执行操作：{action}"})

    except Exception as e:
        import traceback
        preview_logs.append({"type": "error", "text": f"预览失败：{e}"})

    return {
        "preview_logs": preview_logs,
        "files_to_affect": files_to_affect,
        "result": {"success": [], "failed": [], "skipped": [],
                   "success_count": 0, "failed_count": 0, "skipped_count": 0}
    }


@app.route("/api/files/preview", methods=["POST"])
def api_preview():
    """
    预览命令执行结果（不实际移动/删除文件）

    Body:
        workspace: str
        command:   str

    Returns:
        { logs: [...], result: {...} }
    """
    data = request.get_json(force=True, silent=True) or {}
    workspace = data.get("workspace", "")
    command = data.get("command", "").strip()

    if not workspace or not Path(workspace).exists():
        return jsonify({"error": "invalid workspace: " + workspace}), 400
    if not command:
        return jsonify({"error": "please input command"}), 400

    helper = FileHelper(workspace=workspace)

    # 1. 解析意图，构建思维链
    intent = helper.parse(command)
    thinking_logs = _build_thinking_chain(intent, workspace)

    # 2. 执行预览（跳过确认）
    stdout_capture = io.StringIO()
    logs = []

    try:
        with redirect_stdout(stdout_capture):
            # 对所有 organize 动作注入 preview=True
            if isinstance(intent, dict):
                if intent.get("actions"):
                    for act in intent["actions"]:
                        if act.get("action") == "organize":
                            act.setdefault("params", {})
                            act["params"]["preview"] = True
                elif intent.get("action") == "organize":
                    intent.setdefault("params", {})
                    intent["params"]["preview"] = True
            result = helper._execute_action(intent, command, verbose=True, skip_confirm=True)

        output = stdout_capture.getvalue()
        for line in output.splitlines():
            line = line.rstrip()
            if not line:
                continue
            log_type = "step"
            if "===" in line or "---" in line:
                log_type = "info"
            elif "\u2705" in line or "\u6210\u529f" in line:
                log_type = "success"
            elif "\u26a0\ufe0f" in line or "\u8b66\u544a" in line:
                log_type = "warn"
            elif "\u274c" in line or "\u5931\u8d25" in line:
                log_type = "error"
            logs.append({"type": log_type, "text": line})

    except Exception as e:
        logs.append({"type": "error", "text": "preview failed: " + str(e)})
        return jsonify({"logs": logs, "result": None}), 500

    all_logs = thinking_logs + logs
    return jsonify({
        "logs": all_logs,
        "result": result_to_dict(result),
    })


@app.route("/api/files/tree", methods=["GET"])
def api_tree():
    """
    获取目录树结构

    Query Params:
        path:   str   目标目录（默认使用 workspace）
        depth: int   最大递归深度（默认 3）

    Returns:
        { tree: [...], path: str }
    """
    path = request.args.get("path", "")
    depth = int(request.args.get("depth", 3))

    if not path or not Path(path).exists():
        return jsonify({"error": "\u65e0\u6548\u7684\u76ee\u5f55\u8def\u5f84"}), 400

    tree = build_tree(path, max_depth=depth)
    return jsonify({
        "tree": tree,
        "path": str(Path(path).resolve()),
    })


@app.route("/api/files/analyze", methods=["POST"])
def api_analyze():
    """
    分析目录（文件数量、大小、类型分布等）

    Body:
        workspace: str

    Returns:
        { total_files, total_size_mb, by_extension, largest_files, duplicates }
    """
    data = request.get_json(force=True, silent=True) or {}
    workspace = data.get("workspace", "")

    if not workspace or not Path(workspace).exists():
        return jsonify({"error": "\u65e0\u6548\u7684\u5de5\u4f5c\u76ee\u5f55"}), 400

    helper = FileHelper(workspace=workspace)
    stats = helper.analyze()

    if "largest_files" in stats:
        stats["largest_files"] = [str(f) for f in stats["largest_files"]]
    if "duplicates" in stats:
        stats["duplicates"] = {
            k: [str(f) for f in v]
            for k, v in stats["duplicates"].items()
        }

    return jsonify(stats)


@app.route("/api/files/list", methods=["GET"])
def api_list():
    """
    列出目录下的文件和子目录（浅层，用于点击展开）

    Query Params:
        path: str   目标目录

    Returns:
        { items: [...], path: str }
    """
    path = request.args.get("path", "")
    if not path or not Path(path).exists():
        return jsonify({"error": "\u65e0\u6548\u7684\u76ee\u5f55\u8def\u5f84"}), 400

    items = build_tree(path, max_depth=1)
    return jsonify({
        "items": items,
        "path": str(Path(path).resolve()),
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "file-helper-api"})


if __name__ == "__main__":
    print("File Helper API \u542f\u52a8")
    print("\u9ed8\u8ba4\u5de5\u4f5c\u76ee\u5f55: D:\\file_helper_demo")
    print("API \u7aef\u70b9:")
    print("  POST /api/files/chat        \u6267\u884c\u547d\u4ee4")
    print("  POST /api/files/preview   \u9884\u89c8\u547d\u4ee4")
    print("  GET  /api/files/tree      \u83b7\u53d6\u76ee\u5f55\u6811")
    print("  POST /api/files/analyze  \u5206\u6790\u76ee\u5f55")
    print("  GET  /api/files/list      \u5217\u51fa\u76ee\u5f55\u5185\u5bb9")
    app.run(host="0.0.0.0", port=5000, debug=False)
