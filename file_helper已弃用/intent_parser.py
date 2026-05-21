"""
Intent Parser - 自然语言意图解析器

将用户的自然语言解析为函数调用计划。
核心思想：用户输入 → 意图识别 → 参数提取 → 执行计划

支持两种解析模式：
1. 规则解析（快速、离线）→ 默认使用
2. AI解析（百炼兜底）→ 规则失败时自动切换
"""

import re
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Callable

from .file_atomic_ops import (
    get_files, get_file_info, exists, is_dir, get_home_dir,
    get_desktop, get_downloads, get_documents
)
from .file_query import (
    filter_by_extension, filter_by_name_contains, filter_by_name_pattern,
    filter_by_size, filter_by_date, filter_temp_files, filter_empty_files,
    group_by_extension, group_by_date, group_by_size
)
from .file_batch_ops import (
    batch_move, batch_copy, batch_delete, batch_rename,
    batch_add_prefix, batch_add_suffix, batch_numbering,
    organize_by_type, organize_by_date, organize_by_size, organize_by_course,
    clean_temp_files, clean_empty_files, clean_old_files
)


# ===== 意图类型定义 =====

class Intent:
    """意图基类"""
    ACTION = "action"
    QUERY = "query"
    ANALYZE = "analyze"


class ActionType:
    """操作类型"""
    MOVE = "move"
    COPY = "copy"
    DELETE = "delete"
    RENAME = "rename"
    ORGANIZE = "organize"
    CLEAN = "clean"
    SEARCH = "search"
    BACKUP = "backup"
    SYNC = "sync"


class FilterType:
    """过滤条件类型"""
    EXTENSION = "extension"
    NAME_CONTAINS = "name_contains"
    NAME_PATTERN = "name_pattern"
    SIZE = "size"
    DATE = "date"
    TEMP = "temp"
    EMPTY = "empty"


# ===== 意图解析器 =====

class IntentParser:
    """
    自然语言意图解析器

    将用户输入的自然语言解析为结构化的操作计划。
    """

    def __init__(self):
        # 操作关键词映射
        self.action_keywords = {
            ActionType.MOVE: ["移动", "移到", "移动到", "搬到", "放到", "转移到"],
            ActionType.COPY: ["复制", "拷贝", "备份", "复制到", "拷贝到"],
            ActionType.DELETE: ["删除", "删掉", "移除", "清除", "清空", "清理"],
            ActionType.RENAME: ["重命名", "改名", "改名为", "重命名为", "改名为"],
            ActionType.ORGANIZE: ["整理", "分类", "归档", "归类", "整理到"],
            ActionType.CLEAN: ["清理", "打扫", "清除垃圾"],
            ActionType.SEARCH: ["搜索", "查找", "找到", "找出", "搜索", "查看"],
            ActionType.BACKUP: ["备份"],
            ActionType.SYNC: ["同步"],
        }

        # 文件类型关键词（关键词不要太泛，避免误匹配）
        self.file_type_keywords = {
            "image": ["图片", "照片", "图像"],
            "video": ["视频", "影片", "录像"],
            "audio": ["音频", "音乐", "歌曲"],
            "document": ["文档", "文档文件"],  # "文件"太泛，已移除
            "code": ["代码", "源代码", "程序"],
            "archive": ["压缩包", "压缩文件"],
            "pdf": ["pdf", "PDF"],
            "doc": ["word", "Word", "文档", "docx"],
            "xls": ["excel", "Excel", "表格", "xlsx"],
            "ppt": ["ppt", "PPT", "演示文稿", "幻灯片"],
            "txt": ["文本", "文本文件", "txt"],
            "zip": ["zip", "ZIP"],
            "rar": ["rar", "RAR"],
            "7z": ["7z", "7-Zip"],
        }

        # 扩展名映射（含高级类型，file_type_keywords 的 key 直接对应这里）
        self.extension_map = {
            # 高级类型（说"图片"→ image → 所有图片扩展名）
            "image":    ["jpg", "jpeg", "png", "gif", "bmp", "webp"],
            "video":    ["mp4", "avi", "mkv", "mov", "wmv", "flv"],
            "audio":    ["mp3", "wav", "flac", "wma", "aac"],
            "document":  ["pdf", "docx", "doc", "txt", "md"],
            "code":      ["py", "js", "java", "c", "cpp", "go", "rs"],
            "archive":   ["zip", "rar", "7z", "tar", "gz"],
            # 具体扩展名（一个扩展名对应一组变体）
            "jpg": ["jpg", "jpeg"], "png": ["png"], "gif": ["gif"],
            "mp4": ["mp4"], "avi": ["avi"], "mkv": ["mkv"], "mov": ["mov"],
            "mp3": ["mp3"], "wav": ["wav"], "flac": ["flac"],
            "pdf": ["pdf"],
            "docx": ["docx"], "doc": ["doc"],
            "xlsx": ["xlsx"], "xls": ["xls"],
            "pptx": ["pptx"], "ppt": ["ppt"],
            "txt": ["txt"],
            "zip": ["zip"], "rar": ["rar"], "7z": ["7z"],
            "py": ["py"], "js": ["js"], "java": ["java"],
        }

        # 时间关键词
        self.time_keywords = {
            "今天": 0,
            "昨天": 1,
            "前天": 2,
            "三天前": 3,
            "一周前": 7,
            "半个月前": 15,
            "一个月前": 30,
            "三个月前": 90,
            "半年前": 180,
            "一年前": 365,
        }

        # 大小关键词
        self.size_keywords = {
            "KB": 1024,
            "MB": 1024 * 1024,
            "GB": 1024 * 1024 * 1024,
        }

    def parse(self, text: str, use_ai: Optional[bool] = None,
              workspace: Optional[str] = None) -> Dict:
        """
        解析用户输入

        Args:
            text: 用户输入的自然语言
            use_ai: 是否使用AI解析。
                    None=自动判断，True=强制AI，False=强制规则
            workspace: 工作目录（用于隔离真实路径）。
                       设置后，"downloads"/"桌面" 等别名会解析为
                       workspace/downloads / workspace/桌面，避免操作真实目录

        Returns:
            解析后的操作计划，包含 "parser" 字段标识来源
        """
        # 自动判断是否需要AI
        if use_ai is None:
            use_ai = self._should_use_ai(text)

        # 强制使用AI（或自动判断为需要AI）
        if use_ai:
            ai_result = self._try_ai_parse(text)
            if ai_result:
                return ai_result

        # 规则解析（默认路径）
        plan = {
            "original": text,
            "action": None,
            "source": None,
            "target": None,
            "filters": [],
            "params": {},
            "raw_plan": text,
            "parser": "rule",  # 标记来源
        }

        # 1. 识别操作类型
        plan["action"] = self._extract_action(text)

        # 2. 提取源路径（workspace 隔离真实路径）
        plan["source"] = self._extract_path(text, workspace=workspace)

        # 3. 提取目标路径
        plan["target"] = self._extract_target(text)

        # 4. 提取过滤条件
        plan["filters"] = self._extract_filters(text)

        # 5. 提取参数
        plan["params"] = self._extract_params(text)

        return plan

    def _should_use_ai(self, text: str) -> bool:
        """
        判断是否应该使用AI解析
        触发条件：
        1. 用户明确说"用AI"/"AI理解"
        2. 规则解析可能不准的复杂表达
        """
        # 用户明确要求AI
        ai_keywords = ["用ai", "ai理解", "智能理解", "大模型", "llm"]
        for kw in ai_keywords:
            if kw in text.lower():
                return True

        # 规则解析对这类表达效果不好
        complex_indicators = ["上周", "上个月", "去年", "相关的", "类似的",
                               "整理一下", "处理一下", "帮我看看"]
        # 但如果有明确的操作关键词，规则解析就够了
        action_keywords_flat = []
        for kws in self.action_keywords.values():
            action_keywords_flat.extend(kws)

        has_action_keyword = any(kw in text for kw in action_keywords_flat)
        has_complex_expr = any(kw in text for kw in complex_indicators)

        # 复杂表达且没有明确操作词 → 用AI
        if has_complex_expr and not has_action_keyword:
            return True

        return False

    def _try_ai_parse(self, text: str) -> Optional[Dict]:
        """尝试用AI解析，失败返回None"""
        try:
            from .ai_parser import ai_parse as ai_parse_fn
            result = ai_parse_fn(text)
            if result:
                result["parser"] = "ai"
                return result
        except Exception:
            pass
        return None

    def _extract_action(self, text: str) -> Optional[str]:
        """提取操作类型"""
        text_lower = text.lower()

        for action, keywords in self.action_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return action

        # 默认搜索
        return ActionType.SEARCH

    def _extract_path(self, text: str, workspace: Optional[str] = None) -> Optional[str]:
        """提取源路径。设置 workspace 后，"downloads" 等别名会解析为 workspace/下的子目录，避免操作真实路径。"""
        # 常见目录关键词
        path_keywords = {
            "桌面": get_desktop,
            "desktop": get_desktop,
            "下载": get_downloads,
            "downloads": get_downloads,
            "文档": get_documents,
            "documents": get_documents,
            "当前目录": os.getcwd,
            "当前文件夹": os.getcwd,
            "这里": os.getcwd,
        }
        # workspace 隔离时的别名映射
        alias_map = {
            "桌面": "桌面", "desktop": "桌面",
            "下载": "downloads", "downloads": "downloads",
            "文档": "文档", "documents": "文档",
            "当前目录": ".", "当前文件夹": ".", "这里": ".",
        }

        for keyword, getter in path_keywords.items():
            if keyword in text:
                if workspace:
                    return os.path.join(workspace, alias_map.get(keyword, "."))
                return getter()

        # 尝试提取引号中的路径
        quotes = re.findall(r'["\']([^"\']+)["\']', text)
        if quotes:
            path = quotes[0]
            if exists(path):
                return path

        # 提取模糊目录引用：如"22文件夹"、"abc文件夹里的文件"
        # 匹配模式：更精确地匹配源目录
        folder_patterns = [
            # "把"字句
            r'把\s*([^\s，。、]+)文件夹里的',     # "把XX文件夹里的文件"
            r'把\s*([^\s，。、]+)里的文件',       # "把XX里的文件"
            r'把\s*([^\s，。、]+)文件夹的内容',   # "把XX文件夹的内容"
            # "复制/拷贝"开头（无"把"字）
            r'复制\s*([^\s，。、]+)文件夹里的',   # "复制XX文件夹里的文件"
            r'复制\s*([^\s，。。、]+)里的文件',     # "复制XX里的文件"
            r'拷贝\s*([^\s，。、]+)文件夹里的',   # "拷贝XX文件夹里的文件"
            r'拷贝\s*([^\s，。、]+)里的文件',     # "拷贝XX里的文件"
            # "从"字句
            r'从\s*([^\s，。、]+)文件夹里的',     # "从XX文件夹里"
            r'从\s*([^\s，。、]+)里的',           # "从XX里的"
            # "在"字句
            r'在\s*([^\s，。、]+)文件夹里的',     # "在XX文件夹里"
            r'在\s*([^\s，。、]+)里的',           # "在XX里的"
            r'把\s*([^\s，。、]+)中的文件',        # "把XX中的文件"
            r'把\s*([^\s，。、]+)中',             # "把XX中"
            r'在\s*([^\s，。、]+)中的文件',        # "在XX中的文件"
            r'在\s*([^\s，。、]+)中',             # "在XX中"
            r'复制\s*([^\s，。、]+)中的',          # "复制XX中的"
            r'从\s*([^\s，。、]+)中',             # "从XX中"
            # "整理"字句
            r'整理\s*([^\s，。、]+)文件夹里的',   # "整理XX文件夹里的文件"
            r'整理\s*([^\s，。、]+)里的文件',     # "整理XX里的文件"
            r'整理\s*([^\s，。、]+)中',           # "整理XX中"
            # "动词 + XX文件夹"（无"里的"后缀，如"删除22文件夹"）
            r'删除\s*([^\s，。、]+)文件夹',        # "删除XX文件夹"
            r'移动\s*([^\s，。、]+)文件夹',        # "移动XX文件夹"
            r'拷贝\s*([^\s，。、]+)文件夹',        # "拷贝XX文件夹"
            r'复制\s*([^\s，。、]+)文件夹',        # "复制XX文件夹"
            r'重命名\s*([^\s，。、]+)文件夹',      # "重命名XX文件夹"
            r'整理\s*([^\s，。、]+)文件夹',        # "整理XX文件夹"
            # 通用兜底：直接匹配"XX文件夹里的"（无动词前缀）
            r'([^\s，。、]+)文件夹里的',           # 通用："XX文件夹里的"
        ]
        for pattern in folder_patterns:
            match = re.search(pattern, text)
            if match:
                folder_name = match.group(1).strip()
                # 返回相对路径（后续代码会拼接 workspace）
                return folder_name

        # 返回当前目录
        return workspace or os.getcwd()

    def _extract_target(self, text: str) -> Optional[str]:
        """提取目标路径（排除"找到"动词中的"到"）"""
        import re as _re

        patterns = [
            r'到\s*["\']?([^"\']+)["\']?',
            r'向\s*["\']?([^"\']+)["\']?',
            r'至\s*["\']?([^"\']+)["\']?',
            r'放进\s*["\']?([^"\']+)["\']?',
            r'放入\s*["\']?([^"\']+)["\']?',
        ]

        for pattern in patterns:
            for match in _re.finditer(pattern, text):
                target = match.group(1).strip()
                # 排除"找到"动词中的"到"：检查匹配位置前一个字符是否为"找"
                start = match.start()
                if start >= 1 and text[start - 1] == "找":
                    continue
                # 去掉"文件夹"后缀
                if target.endswith("文件夹"):
                    target = target[:-3]
                if not Path(target).is_absolute():
                    return target
                return target

        return None

    def _extract_filters(self, text: str) -> List[Dict]:
        """提取过滤条件"""
        filters = []

        # 1. 文件类型过滤
        extensions = self._extract_file_types(text)
        if extensions:
            filters.append({
                "type": FilterType.EXTENSION,
                "value": extensions,
            })

        # 1.5. 文件名关键词：提取 "xxx.pdf" / "xxx.docx" 等格式中的文件名部分
        # 例如 "删除期中.pdf" → 提取 "期中" 作为 name_contains
        name_from_ext = self._extract_name_from_extension(text)
        if name_from_ext:
            filters.append({
                "type": FilterType.NAME_CONTAINS,
                "value": name_from_ext,
            })

        # 2. 文件大小过滤
        size_filter = self._extract_size(text)
        if size_filter:
            filters.append(size_filter)

        # 3. 时间过滤
        date_filter = self._extract_date(text)
        if date_filter:
            filters.append(date_filter)

        # 4. 名称关键词过滤
        keyword = self._extract_keyword(text)
        if keyword:
            filters.append({
                "type": FilterType.NAME_CONTAINS,
                "value": keyword,
            })

        # 5. 临时文件过滤
        if "临时" in text or "垃圾" in text:
            filters.append({
                "type": FilterType.TEMP,
                "value": True,
            })

        # 6. 空文件过滤
        if "空文件" in text or "空白的" in text:
            filters.append({
                "type": FilterType.EMPTY,
                "value": True,
            })

        return filters

    def _extract_file_types(self, text: str) -> Optional[List[str]]:
        """提取文件类型（中英文关键词通用匹配）"""
        extensions = []
        import re as _re

        # 中英文通用的"完整词"匹配
        # 边界 = 字符串开头/结尾，或 非 a-z A-Z 0-9 的字符（含中文）
        # 中文汉字不在 a-z A-Z 0-9 中，所以会被视为边界
        def _word_match(t: str, kw: str) -> bool:
            escaped = _re.escape(kw)
            boundary = r'(?:^|[^a-zA-Z0-9])'
            boundary_end = r'(?:$|[^a-zA-Z0-9])'
            pattern = boundary + escaped + boundary_end
            return _re.search(pattern, t) is not None

        for file_type, keywords in self.file_type_keywords.items():
            for keyword in keywords:
                if _word_match(text, keyword):
                    if file_type in self.extension_map:
                        extensions.extend(self.extension_map[file_type])
                    else:
                        extensions.append(file_type)
                    break

        # 2. 显式扩展名格式（.pdf, .docx 等）
        dot_ext_pattern = r'\.(\w+)'
        dot_exts = _re.findall(dot_ext_pattern, text)
        for e in dot_exts:
            e_lower = e.lower()
            for ext_key, ext_vals in self.extension_map.items():
                if e_lower in ext_vals:
                    extensions.extend(ext_vals)
                    break
            else:
                extensions.append(e_lower)

        return list(set(extensions)) if extensions else None

    def _extract_name_from_extension(self, text: str) -> Optional[str]:
        """
        从 'xxx.扩展名' 格式中提取文件名部分。
        例如：
          "删除期中.pdf" → "期中"
          "找 report.docx" → "report"
          "复制 data.csv" → "data"
        只在明确有操作对象时才提取，避免误触发。
        """
        # 只在操作动词后提取，避免误匹配普通文本
        action_verbs = ["删除", "移动", "复制", "拷贝", "找", "搜索", "重命名", "整理", "清理", "打开"]
        has_action = any(verb in text for verb in action_verbs)
        if not has_action:
            return None

        # 匹配 "xxx.扩展名" 格式（文件名可以是中文/英文/数字/下划线）
        # 排除包含操作动词的开头，只取最后一个匹配
        pattern = r'([\w\u4e00-\u9fff_-]+)\.(\w+)'
        matches = re.findall(pattern, text)
        if matches:
            # 取最后一个匹配（通常是用户实际想操作的文件）
            name_part, ext_part = matches[-1]
            # 排除以操作动词开头的匹配（如"删除期中"）
            action_verbs_exact = ["删除", "移动", "复制", "拷贝", "找", "搜索", "重命名", "整理", "清理", "打开"]
            if not any(name_part.startswith(v) for v in action_verbs_exact) and 1 <= len(name_part) <= 50:
                return name_part
        return None

    def _extract_size(self, text: str) -> Optional[Dict]:
        """提取文件大小条件"""
        # 大于/小于模式
        greater_pattern = r'[大于|超过|超过|大于|以上]\s*(\d+(?:\.\d+)?)\s*(KB|MB|GB|K|M|G)?'
        less_pattern = r'[小于|低于|以下|小于|以内|以下]\s*(\d+(?:\.\d+)?)\s*(KB|MB|GB|K|M|G)?'

        match = re.search(greater_pattern, text)
        if match:
            value = float(match.group(1))
            unit = (match.group(2) or "MB").upper()
            if unit in ["K"]:
                unit = "KB"
            elif unit in ["M"]:
                unit = "MB"
            elif unit in ["G"]:
                unit = "GB"

            multiplier = self.size_keywords.get(unit, 1)
            return {
                "type": FilterType.SIZE,
                "min": int(value * multiplier),
                "min_mb": value if unit == "MB" else None,
            }

        match = re.search(less_pattern, text)
        if match:
            value = float(match.group(1))
            unit = (match.group(2) or "MB").upper()
            if unit in ["K"]:
                unit = "KB"
            elif unit in ["M"]:
                unit = "MB"
            elif unit in ["G"]:
                unit = "GB"

            multiplier = self.size_keywords.get(unit, 1)
            return {
                "type": FilterType.SIZE,
                "max": int(value * multiplier),
                "max_mb": value if unit == "MB" else None,
            }

        return None

    def _extract_date(self, text: str) -> Optional[Dict]:
        """提取时间条件"""
        for keyword, days in self.time_keywords.items():
            if keyword in text:
                return {
                    "type": FilterType.DATE,
                    "days_ago": days,
                }

        return None

    def _extract_keyword(self, text: str) -> Optional[str]:
        """提取名称关键词"""
        # 包含模式
        patterns = [
            r'包含[“"\']([^"\'<]+)[<"\']',
            r'名叫\s*["\']?([^"\'<]+)["\']?',
            r'名为\s*["\']?([^"\'<]+)["\']?',
            r'文件名.*["\']?([^"\'<]+)["\']?',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None

    def _extract_params(self, text: str) -> Dict:
        """提取其他参数"""
        params = {}

        # 递归模式
        if "递归" in text or "包括子目录" in text or "子文件夹" in text:
            params["recursive"] = True

        # 分类模式
        if "按月份" in text or "按照月份" in text:
            params["organize_mode"] = "month"
        elif "按年份" in text or "按照年份" in text:
            params["organize_mode"] = "year"
        elif "按日期" in text or "按照日期" in text:
            params["organize_mode"] = "day"
        elif "按类型" in text or "按照类型" in text:
            params["organize_mode"] = "type"
        elif "按大小" in text or "按照大小" in text:
            params["organize_mode"] = "size"
        elif "按课程" in text or "按学科" in text or "按照学科" in text:
            params["organize_mode"] = "course"
            if "preview" in text or "先看" in text or "预览" in text:
                params["preview"] = True

        # 前缀/后缀
        if "前缀" in text:
            prefix_match = re.search(r'前缀[为:]?\s*["\']?([^"\'<]+)["\']?', text)
            if prefix_match:
                params["prefix"] = prefix_match.group(1)

        if "后缀" in text:
            suffix_match = re.search(r'后缀[为:]?\s*["\']?([^"\'<]+)["\']?', text)
            if suffix_match:
                params["suffix"] = suffix_match.group(1)

        # 编号
        if "编号" in text or "序号" in text:
            params["numbering"] = True
            start_match = re.search(r'从\s*(\d+)\s*开始', text)
            if start_match:
                params["start"] = int(start_match.group(1))

        return params


# ===== 执行计划器 =====

class ExecutionPlanner:
    """
    执行计划器

    将解析后的意图转换为具体的函数调用序列。
    """

    def __init__(self):
        self.parser = IntentParser()

    def create_plan(self, user_input: str) -> List[Dict]:
        """
        创建执行计划

        Args:
            user_input: 用户输入

        Returns:
            函数调用序列
        """
        # 解析意图
        intent = self.parser.parse(user_input)

        # 根据意图生成执行计划
        if intent["action"] == ActionType.DELETE:
            return self._plan_delete(intent)
        elif intent["action"] == ActionType.MOVE:
            return self._plan_move(intent)
        elif intent["action"] == ActionType.COPY:
            return self._plan_copy(intent)
        elif intent["action"] == ActionType.RENAME:
            return self._plan_rename(intent)
        elif intent["action"] == ActionType.ORGANIZE:
            return self._plan_organize(intent)
        elif intent["action"] == ActionType.CLEAN:
            return self._plan_clean(intent)
        elif intent["action"] == ActionType.SEARCH:
            return self._plan_search(intent)
        else:
            return self._plan_search(intent)

    def _plan_delete(self, intent: Dict) -> List[Dict]:
        """生成删除计划"""
        plan = []

        # 1. 获取文件列表
        plan.append({
            "function": "get_files",
            "args": [intent["source"]],
            "kwargs": {"recursive": intent["params"].get("recursive", False)},
            "output_var": "files",
        })

        # 2. 应用过滤条件
        files_var = "files"
        for f in intent["filters"]:
            files_var = f"filtered_{files_var}"
            plan.append(self._create_filter_step(f, files_var, files_var))

        # 3. 执行删除
        plan.append({
            "function": "batch_delete",
            "args": [f"${files_var}"],
            "kwargs": {},
            "output_var": "result",
        })

        return plan

    def _plan_move(self, intent: Dict) -> List[Dict]:
        """生成移动计划"""
        plan = []

        # 1. 获取文件列表
        plan.append({
            "function": "get_files",
            "args": [intent["source"]],
            "kwargs": {"recursive": intent["params"].get("recursive", False)},
            "output_var": "files",
        })

        # 2. 应用过滤条件
        files_var = "files"
        for f in intent["filters"]:
            files_var = f"filtered_{files_var}"
            plan.append(self._create_filter_step(f, files_var, files_var))

        # 3. 执行移动
        plan.append({
            "function": "batch_move",
            "args": [f"${files_var}", intent["target"]],
            "kwargs": {},
            "output_var": "result",
        })

        return plan

    def _plan_copy(self, intent: Dict) -> List[Dict]:
        """生成复制计划"""
        plan = []

        plan.append({
            "function": "get_files",
            "args": [intent["source"]],
            "kwargs": {"recursive": intent["params"].get("recursive", False)},
            "output_var": "files",
        })

        files_var = "files"
        for f in intent["filters"]:
            files_var = f"filtered_{files_var}"
            plan.append(self._create_filter_step(f, files_var, files_var))

        plan.append({
            "function": "batch_copy",
            "args": [f"${files_var}", intent["target"]],
            "kwargs": {},
            "output_var": "result",
        })

        return plan

    def _plan_rename(self, intent: Dict) -> List[Dict]:
        """生成重命名计划"""
        plan = []

        plan.append({
            "function": "get_files",
            "args": [intent["source"]],
            "kwargs": {"recursive": False},
            "output_var": "files",
        })

        # 根据参数决定重命名方式
        if "prefix" in intent["params"]:
            plan.append({
                "function": "batch_add_prefix",
                "args": ["$files", intent["params"]["prefix"]],
                "output_var": "result",
            })
        elif "suffix" in intent["params"]:
            plan.append({
                "function": "batch_add_suffix",
                "args": ["$files", intent["params"]["suffix"]],
                "output_var": "result",
            })
        elif "numbering" in intent["params"]:
            kwargs = {}
            if "start" in intent["params"]:
                kwargs["start"] = intent["params"]["start"]
            plan.append({
                "function": "batch_numbering",
                "args": ["$files"],
                "kwargs": kwargs,
                "output_var": "result",
            })
        else:
            # 默认批量重命名
            plan.append({
                "function": "batch_rename",
                "args": ["$files", "", ""],
                "output_var": "result",
            })

        return plan

    def _plan_organize(self, intent: Dict) -> List[Dict]:
        """生成分类整理计划"""
        plan = []

        plan.append({
            "function": "get_files",
            "args": [intent["source"]],
            "kwargs": {"recursive": intent["params"].get("recursive", False)},
            "output_var": "files",
        })

        # 根据分类模式选择函数
        mode = intent["params"].get("organize_mode", "type")
        target = intent["target"] or intent["source"]

        if mode == "type":
            plan.append({
                "function": "organize_by_type",
                "args": ["$files", target],
                "kwargs": {},
                "output_var": "result",
            })
        elif mode in ["month", "year", "day"]:
            plan.append({
                "function": "organize_by_date",
                "args": ["$files", target],
                "kwargs": {"mode": mode},
                "output_var": "result",
            })
        elif mode == "size":
            plan.append({
                "function": "organize_by_size",
                "args": ["$files", target],
                "kwargs": {},
                "output_var": "result",
            })
        elif mode == "course":
            plan.append({
                "function": "organize_by_course",
                "args": ["$files", target],
                "kwargs": {"use_ai": True},
                "output_var": "result",
            })

        return plan

    def _plan_clean(self, intent: Dict) -> List[Dict]:
        """生成清理计划"""
        plan = []

        if intent["params"].get("recursive", False):
            recursive = True
        else:
            recursive = False

        # 清理临时文件
        if "临时" in intent["raw_plan"] or "垃圾" in intent["raw_plan"]:
            plan.append({
                "function": "clean_temp_files",
                "args": [intent["source"]],
                "kwargs": {"to_trash": True},
                "output_var": "result",
            })

        # 清理空文件
        elif "空文件" in intent["raw_plan"]:
            plan.append({
                "function": "clean_empty_files",
                "args": [intent["source"]],
                "kwargs": {"to_trash": True},
                "output_var": "result",
            })

        # 清理旧文件
        else:
            # 提取天数
            days = 30  # 默认30天
            for keyword, d in self.parser.time_keywords.items():
                if keyword in intent["raw_plan"]:
                    days = d
                    break

            plan.append({
                "function": "clean_old_files",
                "args": [intent["source"], days],
                "kwargs": {"to_trash": True},
                "output_var": "result",
            })

        return plan

    def _plan_search(self, intent: Dict) -> List[Dict]:
        """生成搜索计划"""
        plan = []

        plan.append({
            "function": "get_files",
            "args": [intent["source"]],
            "kwargs": {"recursive": intent["params"].get("recursive", True)},
            "output_var": "files",
        })

        # 如果有过滤条件，返回过滤后的文件
        if intent["filters"]:
            files_var = "files"
            for f in intent["filters"]:
                files_var = f"filtered_{files_var}"
                plan.append(self._create_filter_step(f, files_var, files_var))

        # 否则直接返回所有文件
        plan.append({
            "function": "identity",
            "args": [f"$filtered_{files_var}" if intent["filters"] else "$files"],
            "output_var": "result",
        })

        return plan

    def _create_filter_step(self, filter_def: Dict, output_var: str, input_var: str) -> Dict:
        """创建过滤步骤"""
        filter_type = filter_def["type"]

        if filter_type == FilterType.EXTENSION:
            return {
                "function": "filter_by_extension",
                "args": [f"${input_var}"],
                "kwargs": {"extensions": filter_def["value"]},
                "output_var": output_var,
            }
        elif filter_type == FilterType.NAME_CONTAINS:
            return {
                "function": "filter_by_name_contains",
                "args": [f"${input_var}", filter_def["value"]],
                "output_var": output_var,
            }
        elif filter_type == FilterType.SIZE:
            kwargs = {}
            if "min" in filter_def:
                kwargs["min_size"] = filter_def["min"]
            if "max" in filter_def:
                kwargs["max_size"] = filter_def["max"]
            return {
                "function": "filter_by_size",
                "args": [f"${input_var}"],
                "kwargs": kwargs,
                "output_var": output_var,
            }
        elif filter_type == FilterType.DATE:
            return {
                "function": "filter_by_date",
                "args": [f"${input_var}"],
                "kwargs": {"days_ago": filter_def["days_ago"]},
                "output_var": output_var,
            }
        elif filter_type == FilterType.TEMP:
            return {
                "function": "filter_temp_files",
                "args": [f"${input_var}"],
                "output_var": output_var,
            }
        elif filter_type == FilterType.EMPTY:
            return {
                "function": "filter_empty_files",
                "args": [f"${input_var}"],
                "output_var": output_var,
            }

        return {
            "function": "identity",
            "args": [f"${input_var}"],
            "output_var": output_var,
        }


# ===== 便捷函数 =====

def parse_command(text: str, use_ai: Optional[bool] = None) -> Dict:
    """
    解析用户命令的便捷函数

    Args:
        text: 用户输入的自然语言
        use_ai: 是否使用AI解析。None=自动判断，True=强制AI，False=强制规则

    Returns:
        解析后的操作计划
    """
    parser = IntentParser()
    return parser.parse(text, use_ai=use_ai)


def plan_execution(user_input: str) -> List[Dict]:
    """
    生成执行计划的便捷函数

    Args:
        user_input: 用户输入的自然语言

    Returns:
        函数调用序列
    """
    planner = ExecutionPlanner()
    return planner.create_plan(user_input)


# ===== 示例 =====

if __name__ == "__main__":
    # 测试解析
    parser = IntentParser()

    test_inputs = [
        "把大于100MB的视频移到归档",
        "删除所有临时文件",
        "帮我找一下所有pdf文件",
        "按月份整理图片",
        "把这些文件批量重命名，加上日期前缀",
    ]

    for input_text in test_inputs:
        print(f"\n{'='*50}")
        print(f"输入: {input_text}")
        result = parser.parse(input_text)
        print(f"动作: {result['action']}")
        print(f"源: {result['source']}")
        print(f"目标: {result['target']}")
        print(f"过滤: {result['filters']}")
        print(f"参数: {result['params']}")
