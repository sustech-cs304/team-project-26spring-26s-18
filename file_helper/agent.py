"""
agent.py — ReAct Agent for File Management

架构：
  Perception  → 接收自然语言命令
  Reasoning   → LLM 思考：用哪个工具、为什么
  Tool Use    → 调用真实文件操作函数
  Observation → LLM 读取工具结果，决定下一步
  Loop        → 重复直到任务完成或需要用户确认

使用方式：
    agent = FileAgent("D:/file_helper_demo")
    for step in agent.run("找到所有区块链相关文件"):
        print(step)
    # 如果有 confirm_required：
    result = agent.confirm(True)
"""

import json
import os
import urllib.request
from datetime import date
from pathlib import Path
from typing import Generator, Optional

# API 配置（使用 qwen-plus 支持 function calling）
_API_KEY = "sk-66bfacdf2a9a49dc9c7cf6ff4e537eef"
_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
_MODEL = "qwen-turbo"
_MAX_ITERATIONS = 8

# ─────────────────────────────────────────────
# 工具定义（Tool Schema）
# ─────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "列出目录中的文件和子目录，用于了解当前目录结构",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "目录路径，'.' 代表工作目录"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "是否递归列出子目录文件，默认 false",
                        "default": False
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "搜索文件，支持按文件名、扩展名、内容关键词、修改日期过滤",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "搜索目录，'.' 代表工作目录"
                    },
                    "name_contains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "文件名必须包含这些关键词之一（OR 匹配）"
                    },
                    "extensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "扩展名列表，如 ['pdf', 'docx']"
                    },
                    "content_keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "文件内容必须包含这些关键词之一（中英文均可）"
                    },
                    "before_date": {
                        "type": "string",
                        "description": "只返回此日期之前修改的文件，格式 YYYY-MM-DD"
                    },
                    "after_date": {
                        "type": "string",
                        "description": "只返回此日期之后修改的文件，格式 YYYY-MM-DD"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "是否递归搜索子目录，默认 false",
                        "default": False
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_files",
            "description": (
                "删除文件（移到回收站）。需要用户确认。"
                "支持两种方式：(1) 直接传 file_paths 列表；"
                "(2) 传 source_dir + 过滤条件（after_date/before_date/extensions/name_contains），系统自动搜索再删除。"
                "对于'清理X年的文件'这类操作，直接用 source_dir + 日期参数，无需先单独 search_files。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要删除的文件完整路径列表（与 source_dir 二选一）"
                    },
                    "source_dir": {
                        "type": "string",
                        "description": "从该目录搜索要删除的文件（与 file_paths 二选一）"
                    },
                    "after_date": {
                        "type": "string",
                        "description": "只删除此日期之后修改的文件，格式 YYYY-MM-DD"
                    },
                    "before_date": {
                        "type": "string",
                        "description": "只删除此日期之前修改的文件，格式 YYYY-MM-DD"
                    },
                    "extensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "只删除这些扩展名的文件"
                    },
                    "name_contains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "只删除文件名包含这些关键词的文件"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "copy_files",
            "description": "复制文件到目标目录，原文件保留。可以直接指定源目录（source_dir）复制其中所有文件，也可以指定具体文件列表（file_paths）",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_dir": {
                        "type": "string",
                        "description": "源目录路径，将复制该目录下所有文件。与 file_paths 二选一"
                    },
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要复制的文件完整路径列表。与 source_dir 二选一"
                    },
                    "target_dir": {
                        "type": "string",
                        "description": "目标目录路径"
                    }
                },
                "required": ["target_dir"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_files",
            "description": "移动文件到目标目录（原文件会被删除）。需要用户确认。可以直接指定源目录（source_dir）或具体文件列表（file_paths）",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_dir": {
                        "type": "string",
                        "description": "源目录路径，将移动该目录下所有文件。与 file_paths 二选一"
                    },
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要移动的文件完整路径列表。与 source_dir 二选一"
                    },
                    "target_dir": {
                        "type": "string",
                        "description": "目标目录路径"
                    }
                },
                "required": ["target_dir"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "organize_files",
            "description": "整理文件到分类子目录。可以用 source_dir 指定来源目录（自动读取其中所有文件），也可以用 file_paths 指定具体文件列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_dir": {
                        "type": "string",
                        "description": "来源目录，整理该目录下所有文件。与 file_paths 二选一"
                    },
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要整理的文件完整路径列表。与 source_dir 二选一"
                    },
                    "target_dir": {
                        "type": "string",
                        "description": "整理后文件存放的根目录（不填则整理到来源目录本身）"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["type", "date", "size", "course"],
                        "description": "分类方式：type=按文件类型, date=按日期, size=按大小, course=按学科课程"
                    }
                },
                "required": ["mode"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "创建目录",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要创建的目录路径"
                    }
                },
                "required": ["path"]
            }
        }
    },
]

# ─────────────────────────────────────────────
# FileAgent
# ─────────────────────────────────────────────

class FileAgent:
    """
    ReAct 文件管理 Agent。

    run(command) 是一个生成器，每一步 yield 一个 dict：
      {"type": "thought",          "content": "..."}       # LLM 推理过程
      {"type": "action",           "tool": "...", "args": {...}}  # 调用工具
      {"type": "observation",      "result": {...}}         # 工具返回结果
      {"type": "confirm_required", "action": "...", "files": [...]}  # 等待用户确认
      {"type": "done",             "summary": "...", "files": [...]}  # 任务完成
      {"type": "error",            "message": "..."}        # 出错
    """

    def __init__(self, workspace: str = None):
        self.workspace = os.path.abspath(workspace or os.getcwd())
        self._pending: Optional[dict] = None  # 待确认的危险操作

    # ── 主循环 ──────────────────────────────

    def run(self, command: str) -> Generator:
        """ReAct agent loop，生成器形式逐步输出推理 + 执行过程"""
        messages = [
            {
                "role": "system",
                "content": (
                    f"你是一个文件管理助手，采用 ReAct（推理+行动）模式工作。今天是 {date.today()}。"
                    f"工作目录：{self.workspace}。\n\n"
                    "【强制要求】每次调用工具前，必须先在 content 字段输出你的推理过程，格式：\n"
                    "思考：[分析用户需求，说明为什么要调用这个工具，预期会得到什么结果]\n"
                    "每次收到工具结果后，也必须在 content 字段输出观察总结，格式：\n"
                    "观察：[描述工具返回了什么，是否符合预期，下一步怎么做]\n"
                    "这些推理过程会直接展示给用户，请用中文清晰表达。\n\n"
                    "重要原则：\n"
                    "1. 【并行工具调用】可以在一次回复中同时调用多个工具，能并行的就并行\n"
                    "   例如：'创建A，把B里文件复制到A' → 第一轮同时 create_directory(A) + search_files(B)，第二轮 copy_files\n"
                    "2. 【路径名称提取】用户说'XX文件夹'、'XX目录'、'XX文件夹里'时，路径只取'XX'，不要把'文件夹'/'目录'带进路径\n"
                    "   例：'整理11文件夹' → path='11'，不是'11文件夹'\n"
                    "   例：'把cp文件夹的文件移到33' → source_dir='cp', target_dir='33'\n"
                    "3. 【不要多余探索】路径直接用，不必先 list_directory 验证\n"
                    "3. 【复制 vs 移动】copy_files=原文件保留；move_files=原文件删除，不要混淆\n"
                    "4. 【递归搜索】search_files 默认 recursive=false；只有用户明确说'递归'、'所有子文件夹'时才设为 true\n"
                    "5. 【语义搜索关键词扩展】当用户找'XX相关文件'、'关于XX的文件'时：\n"
                    "   - 必须用 content_keywords 而不是 name_contains\n"
                    "   - 必须把主题扩展为 5-10 个关键词，同时包含中文和英文\n"
                    "   - 例：'区块链' → content_keywords=['区块链','blockchain','智能合约','smart contract','分布式账本','共识机制','比特币','以太坊']\n"
                    "   - 例：'机器学习' → content_keywords=['机器学习','machine learning','深度学习','神经网络','训练','模型','neural network']\n"
                    "   - 例：'操作系统' → content_keywords=['操作系统','operating system','进程','线程','内存管理','调度','OS']\n"
                    "6. 【关键】删除和移动操作：\n"
                    "   - 找到文件后，必须立即调用 delete_files 或 move_files 工具\n"
                    "   - 绝对不要在文字里问'是否删除'——系统会自动弹出确认，不需要你问\n"
                    "   - 用户说'清理/删除/移动'就是授权你调工具，直接调即可\n"
                    "   - 复制、整理、创建目录直接执行，不需确认"
                ),
            },
            {"role": "user", "content": command},
        ]

        # 递归关键词：只有命令里出现这些词才允许递归搜索
        _recursive_keywords = ["递归", "所有子文件夹", "包含子目录", "全部文件夹", "所有目录"]
        user_wants_recursive = any(kw in command for kw in _recursive_keywords)

        for _ in range(_MAX_ITERATIONS):
            # 调用 LLM（带工具定义）
            response = self._call_llm(messages)
            if response is None:
                yield {"type": "error", "message": "AI 接口调用失败"}
                return

            thought = response.get("content") or ""
            tool_calls = response.get("tool_calls") or []

            # 没有工具调用 → LLM 认为任务完成，直接输出 done（不重复输出 thought）
            if not tool_calls:
                yield {"type": "done", "summary": thought.strip(), "files": []}
                return

            # 有工具调用时才输出推理过程
            if thought and thought.strip():
                yield {"type": "thought", "content": thought.strip()}

            # 将 assistant 消息加入历史
            messages.append({
                "role": "assistant",
                "content": thought,
                "tool_calls": tool_calls,
            })

            # 执行每个工具调用
            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                try:
                    tool_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    tool_args = {}

                # 强制覆盖：用户没说递归就不递归
                if tool_name in ("search_files", "list_directory"):
                    tool_args["recursive"] = user_wants_recursive

                yield {"type": "action", "tool": tool_name, "args": tool_args}

                # 执行工具
                obs = self._execute_tool(tool_name, tool_args)
                yield {"type": "observation", "result": obs}

                # 按课程整理：先询问是否爬取 TIS，暂停循环
                if obs.get("requires_tis"):
                    self._pending = {
                        "type": "tis_organize",
                        "files": obs["files"],
                        "target_dir": obs["target_dir"],
                    }
                    yield {
                        "type": "tis_required",
                        "files_count": len(obs["files"]),
                        "target_dir": obs["target_dir"],
                        "message": obs["message"],
                    }
                    return  # 暂停，等待 TIS 获取后调用 resume_after_tis()

                # 危险操作需要确认：存储待执行操作，暂停循环
                if obs.get("requires_confirmation"):
                    self._pending = {
                        "action": obs["action"],
                        "files": obs["files"],
                        "target_dir": obs.get("target_dir"),
                    }
                    yield {
                        "type": "confirm_required",
                        "action": obs["action"],
                        "target_dir": obs.get("target_dir"),
                        "files": [
                            {"name": Path(f).name, "path": f}
                            for f in obs["files"]
                        ],
                    }
                    return  # 暂停，等待 confirm()

                # 将工具结果加入历史，供 LLM 观察
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": json.dumps(obs, ensure_ascii=False),
                })

        yield {"type": "error", "message": "超过最大迭代次数，任务未完成"}

    def confirm(self, confirmed: bool) -> dict:
        """执行或取消待确认的危险操作"""
        if not self._pending:
            return {"success": False, "message": "没有待确认的操作"}

        op = self._pending
        self._pending = None

        if not confirmed:
            return {"success": True, "message": "已取消", "success_count": 0, "failed_count": 0}

        try:
            from .file_batch_ops import batch_delete, batch_move, BatchResult

            files = op["files"]
            action = op["action"]

            if action == "delete":
                result: BatchResult = batch_delete(files, to_trash=True, confirm=False)
            elif action == "move":
                target = op.get("target_dir") or self.workspace
                if not os.path.isabs(target):
                    target = os.path.join(self.workspace, target)
                result: BatchResult = batch_move(files, target, overwrite=True)
            else:
                return {"success": False, "message": f"未知操作: {action}"}

            skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
            msg = f"执行完成"
            if skipped > 0:
                msg += f"（{skipped} 个文件已存在目标位置，已跳过）"
            return {
                "success": True,
                "message": msg,
                "success_count": len(result.success),
                "failed_count": len(result.failed),
                "skipped_count": skipped,
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ── LLM 调用 ────────────────────────────

    def _call_llm(self, messages: list) -> Optional[dict]:
        """调用 DashScope function calling API，返回 assistant message dict"""
        payload = {
            "model": _MODEL,
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
            "temperature": 0.1,
        }
        try:
            req = urllib.request.Request(
                _API_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {_API_KEY}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]
        except Exception as e:
            print(f"[错误] LLM 调用失败: {e}")
            return None

    # ── 工具执行 ────────────────────────────

    def _resolve_path(self, path: str) -> str:
        """将相对路径解析为绝对路径，并确保在 workspace 内"""
        if not path or path in (".", ""):
            return self.workspace
        if not os.path.isabs(path):
            path = os.path.join(self.workspace, path)
        path = os.path.abspath(path)
        # 安全校验：不允许超出 workspace
        if not path.startswith(self.workspace):
            return self.workspace
        return path

    def _execute_tool(self, name: str, args: dict) -> dict:
        """分发工具调用，返回结构化 observation"""
        try:
            if name == "list_directory":
                return self._tool_list_directory(args)
            elif name == "search_files":
                return self._tool_search_files(args)
            elif name == "delete_files":
                return self._tool_delete_files(args)
            elif name == "copy_files":
                return self._tool_copy_files(args)
            elif name == "move_files":
                return self._tool_move_files(args)
            elif name == "organize_files":
                return self._tool_organize_files(args)
            elif name == "create_directory":
                return self._tool_create_directory(args)
            else:
                return {"success": False, "error": f"未知工具: {name}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def resume_after_tis(self) -> dict:
        """TIS 获取完成后继续执行课程整理"""
        if not self._pending or self._pending.get("type") != "tis_organize":
            return {"success": False, "message": "没有待处理的整理操作"}

        op = self._pending
        self._pending = None

        try:
            from .file_batch_ops import organize_by_course
            result = organize_by_course(op["files"], op["target_dir"])
            return {
                "success": True,
                "success_count": len(result.success),
                "failed_count": len(result.failed),
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _tool_list_directory(self, args: dict) -> dict:
        from .file_atomic_ops import get_files, get_dirs
        path = self._resolve_path(args.get("path", "."))
        recursive = args.get("recursive", False)

        if not os.path.isdir(path):
            return {"success": False, "error": f"目录不存在: {path}"}

        files = get_files(path, recursive=recursive)
        dirs = get_dirs(path)
        return {
            "success": True,
            "path": path,
            "file_count": len(files),
            "dir_count": len(dirs),
            "files": [Path(f).name for f in files[:50]],  # 最多展示50个
            "dirs": [Path(d).name for d in dirs],
            "truncated": len(files) > 50,
        }

    def _tool_search_files(self, args: dict) -> dict:
        from .file_atomic_ops import get_files
        from .file_query import (
            filter_by_extension, filter_by_name_contains,
            filter_by_content_contains, filter_by_date,
        )
        from datetime import datetime

        path = self._resolve_path(args.get("path", "."))
        recursive = args.get("recursive", False)

        if not os.path.isdir(path):
            return {"success": False, "error": f"目录不存在: {path}"}

        print(f"[步骤] 扫描目录: {path}{'（含子目录）' if recursive else ''}")
        files = get_files(path, recursive=recursive)
        print(f"[步骤] 找到 {len(files)} 个文件，开始过滤...")

        # 扩展名过滤
        if args.get("extensions"):
            files = filter_by_extension(files, args["extensions"])

        # 文件名过滤
        if args.get("name_contains"):
            files = filter_by_name_contains(files, args["name_contains"])

        # 内容关键词（先检查文件名 OR 内容）
        if args.get("content_keywords"):
            kws = args["content_keywords"]
            name_hits = set(filter_by_name_contains(files, kws))
            content_hits = set(filter_by_content_contains(files, kws))
            matched = name_hits | content_hits
            files = [f for f in files if f in matched]

        # 日期过滤
        before = args.get("before_date")
        after = args.get("after_date")
        if before or after:
            files = filter_by_date(
                files,
                before=datetime.fromisoformat(before) if before else None,
                after=datetime.fromisoformat(after) if after else None,
            )

        return {
            "success": True,
            "count": len(files),
            "files": files,  # 完整路径，供后续操作使用
            "file_names": [Path(f).name for f in files],
        }

    def _get_files_from_args(self, args: dict) -> list:
        """从 source_dir 或 file_paths 中获取文件列表"""
        from .file_atomic_ops import get_files
        if args.get("source_dir"):
            source = self._resolve_path(args["source_dir"])
            return get_files(source, recursive=False)
        return [f for f in args.get("file_paths", []) if os.path.exists(f)]

    def _tool_copy_files(self, args: dict) -> dict:
        from .file_batch_ops import batch_copy
        files = self._get_files_from_args(args)
        target = self._resolve_path(args.get("target_dir", "."))
        if not files:
            return {"success": False, "error": "没有找到可复制的文件，请检查源目录或文件路径"}
        os.makedirs(target, exist_ok=True)
        result = batch_copy(files, target)
        return {
            "success": True,
            "success_count": len(result.success),
            "failed_count": len(result.failed),
            "message": f"复制完成，成功 {len(result.success)} 个，失败 {len(result.failed)} 个",
        }

    def _tool_delete_files(self, args: dict) -> dict:
        """不立即执行，返回 requires_confirmation"""
        from .file_atomic_ops import get_files
        from .file_query import (
            filter_by_extension, filter_by_name_contains, filter_by_date,
        )
        from datetime import datetime

        # 方式1：直接给 file_paths
        if args.get("file_paths"):
            files = [f for f in args["file_paths"] if os.path.exists(f)]
        # 方式2：source_dir + 过滤条件
        elif args.get("source_dir"):
            source = self._resolve_path(args["source_dir"])
            files = get_files(source, recursive=False)
            if args.get("extensions"):
                files = filter_by_extension(files, args["extensions"])
            if args.get("name_contains"):
                files = filter_by_name_contains(files, args["name_contains"])
            after = args.get("after_date")
            before = args.get("before_date")
            if after or before:
                files = filter_by_date(
                    files,
                    after=datetime.fromisoformat(after) if after else None,
                    before=datetime.fromisoformat(before) if before else None,
                )
        else:
            files = []

        if not files:
            return {"success": True, "message": "没有找到符合条件的文件", "count": 0}

        return {
            "requires_confirmation": True,
            "action": "delete",
            "files": files,
            "message": f"准备删除 {len(files)} 个文件，等待用户确认",
        }

    def _tool_move_files(self, args: dict) -> dict:
        """不立即执行，返回 requires_confirmation"""
        files = self._get_files_from_args(args)
        target_dir = self._resolve_path(args.get("target_dir", "."))
        if not files:
            return {"success": True, "message": "没有找到可移动的文件", "count": 0}
        return {
            "requires_confirmation": True,
            "action": "move",
            "files": files,
            "target_dir": target_dir,
            "message": f"准备将 {len(files)} 个文件移动到 {target_dir}，等待用户确认",
        }

    def _tool_organize_files(self, args: dict) -> dict:
        from .file_batch_ops import (
            organize_by_type, organize_by_date, organize_by_size, organize_by_course,
        )
        # 支持 source_dir 或 file_paths
        files = self._get_files_from_args(args)
        # target_dir 默认等于 source_dir（整理到来源目录本身）
        if args.get("target_dir"):
            target = self._resolve_path(args["target_dir"])
        elif args.get("source_dir"):
            target = self._resolve_path(args["source_dir"])
        else:
            target = self.workspace
        mode = args.get("mode", "type")

        if not files:
            return {"success": False, "error": "文件列表为空，请检查来源目录是否存在且有文件"}

        if mode == "type":
            result = organize_by_type(files, target)
        elif mode == "date":
            result = organize_by_date(files, target)
        elif mode == "size":
            result = organize_by_size(files, target)
        elif mode == "course":
            # 检查是否已有课程数据；没有才需要 TIS 登录
            try:
                from .course_config import load_courses
                existing = load_courses()
            except Exception:
                existing = []
            if not existing:
                return {
                    "requires_tis": True,
                    "files": files,
                    "target_dir": target,
                    "message": f"尚未配置课程数据（共 {len(files)} 个文件待整理），是否从 TIS 获取课程信息以提高分类准确率？",
                }
            result = organize_by_course(files, target)
        else:
            return {"success": False, "error": f"不支持的整理模式: {mode}"}

        return {
            "success": True,
            "success_count": len(result.success),
            "failed_count": len(result.failed),
            "message": f"整理完成，成功 {len(result.success)} 个，失败 {len(result.failed)} 个",
        }

    def _tool_create_directory(self, args: dict) -> dict:
        path = self._resolve_path(args.get("path", ""))
        try:
            os.makedirs(path, exist_ok=True)
            return {"success": True, "path": path, "message": f"目录已创建: {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
