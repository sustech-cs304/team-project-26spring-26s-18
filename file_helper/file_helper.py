"""
File Helper - 文件管理助手主入口

整合所有原子函数和模块，对外提供统一的自然语言文件管理接口。
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Union

# 导入所有模块
from .file_atomic_ops import (
    get_files, get_dirs, get_file_info, exists, is_file, is_dir,
    get_file_size, get_extension, get_file_name, get_file_hash,
    get_created_time, get_modified_time,
    create_dir, delete_dir, is_empty_dir, get_dir_size, get_dir_file_count,
    move_file, copy_file, delete_file, rename_file,
    create_file, read_file, write_file, touch_file,
    ensure_dir, safe_move, safe_copy,
    get_home_dir, get_desktop, get_downloads, get_documents,
)

from .file_query import (
    filter_by_extension, filter_by_name_contains, filter_by_name_pattern,
    filter_by_size, filter_by_date, filter_by_name_regex,
    filter_temp_files, filter_empty_files, filter_existing, filter_hidden,
    sort_by_name, sort_by_size, sort_by_date, sort_by_extension,
    group_by_extension, group_by_date, group_by_size,
    count_files, count_by_extension, total_size, total_size_mb,
    get_largest_files, get_smallest_files, get_newest_files, get_oldest_files,
    get_duplicates, unique_by_name, unique_by_content,
    find_files, get_files_by_type,
)

from .file_batch_ops import (
    batch_move, batch_copy, batch_delete, batch_rename,
    batch_add_prefix, batch_add_suffix, batch_numbering, batch_replace_in_name,
    batch_replace_spaces, batch_change_extension,
    organize_by_type, organize_by_date, organize_by_size, organize_by_course,
    clean_temp_files, clean_empty_files, clean_empty_dirs, clean_old_files,
    backup_files, sync_files,
    BatchResult, print_batch_result,
)

from .ai_only_parser import (
    AIOnlyParser as IntentParser,
    ai_only_parse as ai_parse_command,
)
from .intent_parser import ExecutionPlanner, ActionType, FilterType


def parse_command(command: str, workspace: str = None) -> Dict:
    """解析用户命令的便捷函数（纯AI版本）"""
    return ai_parse_command(command, workspace=workspace)


class FileHelper:
    """
    文件管理助手

    提供自然语言驱动的文件管理功能。
    """

    def __init__(self, workspace: str = None):
        """
        初始化文件助手

        Args:
            workspace: 工作目录，默认为当前目录
        """
        self.workspace = workspace or os.getcwd()
        self.parser = IntentParser()
        self.planner = ExecutionPlanner()

    # ===== 快捷路径 =====

    def desktop(self) -> str:
        """获取桌面路径"""
        return get_desktop()

    def downloads(self) -> str:
        """获取下载目录"""
        return get_downloads()

    def documents(self) -> str:
        """获取文档目录"""
        return get_documents()

    def home(self) -> str:
        """获取用户主目录"""
        return get_home_dir()

    def set_workspace(self, path: str):
        """设置工作目录"""
        self.workspace = path

    # ===== 自然语言接口 =====

    def run(self, command: str, use_ai: Optional[bool] = None, verbose: bool = True) -> BatchResult:
        """
        执行自然语言命令（支持单动作和多动作）

        Args:
            command: 自然语言命令
            use_ai: 是否使用AI解析。None=自动判断，True=强制AI，False=强制规则
            verbose: 是否打印详细信息

        Returns:
            BatchResult 对象
        """
        # 1. 解析命令（纯AI，无视use_ai参数）
        intent = self.parser.parse(command, workspace=self.workspace)

        # 2. 判断是否为多动作
        actions_list = intent.get("actions")
        if actions_list:
            # 多动作：按顺序执行
            total_result = BatchResult()
            for idx, act_intent in enumerate(actions_list):
                act_name = act_intent.get("action") or "unknown"
                if verbose:
                    print(f"\n  --- 步骤 {idx + 1}/{len(actions_list)}: {act_name} ---")
                step_result = self._execute_action(act_intent, command, verbose)
                # 合并结果
                for s in step_result.success:
                    total_result.add_success(s["path"] if isinstance(s, dict) else s)
                for f in step_result.failed:
                    total_result.add_failed(f["path"] if isinstance(f, dict) else f, f.get("reason", ""))
                for s in step_result.skipped:
                    total_result.add_skipped(s["path"] if isinstance(s, dict) else s, s.get("reason", ""))
            if verbose:
                print("\n==================================================")
                print("操作完成:")
                print(f"  成功: {len(total_result.success)}")
                print(f"  失败: {len(total_result.failed)}")
                print("==================================================")
            return total_result
        else:
            # 单动作：直接执行
            result = self._execute_action(intent, command, verbose)
            return result

    def _execute_action(self, intent: Dict, command: str, verbose: bool = True) -> BatchResult:
        """执行单个动作"""
        action = intent.get("action")

        # 获取文件列表
        source = intent.get("source") or self.workspace
        if source == "." or source == "":
            source = self.workspace
        if not os.path.isabs(source):
            source = os.path.join(self.workspace, source)
        recursive = intent.get("params", {}).get("recursive", False)
        files = get_files(source, recursive)

        # 应用过滤条件（name_contains 支持多关键词 OR 合并）
        filters = intent.get("filters", [])
        # 合并多个 name_contains 为一次调用（OR 逻辑）
        name_kw_list = []
        other_filters = []
        for f in filters:
            if f.get("type") == "name_contains":
                val = f.get("value", "")
                if isinstance(val, dict) and "value" in val:
                    val = val["value"]
                if isinstance(val, list):
                    name_kw_list.extend(val)
                else:
                    name_kw_list.append(val)
            else:
                other_filters.append(f)
        # 先处理 OR 合并的 name_contains
        if name_kw_list:
            files = filter_by_name_contains(files, name_kw_list)
        # 再处理其他过滤器
        for f in other_filters:
            files = self._apply_filter(files, f)

        result = None

        # 处理 mkdir（AI专用，ExecutionPlanner 里没有）
        if action == "mkdir":
            target = intent.get("target") or intent.get("source")
            if not target:
                result = BatchResult()
            else:
                if not os.path.isabs(target):
                    target = os.path.join(self.workspace, target)
                # 显示将要创建的目录
                print(f"\n准备创建目录: {Path(target).name}")
                print("-" * 50)
                try:
                    os.makedirs(target, exist_ok=True)
                    result = BatchResult()
                    result.add_success(target, "目录已创建")
                except Exception as e:
                    result = BatchResult()
                    result.add_failed(target, str(e))
            if verbose:
                print_batch_result(result)
            return result

        if action == ActionType.DELETE:
            # 计算绝对路径
            source_abs = source
            if not os.path.isabs(source_abs):
                source_abs = os.path.join(self.workspace, source_abs)
            
            # 特殊判断1：删除空文件夹（先找空目录，再删除）
            if "空" in command and any(k in command for k in ["文件夹", "目录", "空文件夹", "空目录"]):
                result = clean_empty_dirs(source_abs, confirm=True)
            # 特殊判断2：source_abs 本身是一个目录 → 直接删除该目录
            elif os.path.isdir(source_abs):
                result = BatchResult()
                # 确认后再删除
                print(f"\n⚠️ 危险操作：准备删除目录")
                print("-" * 50)
                print(f"  - {Path(source_abs).name}")  # 只显示目录名
                print(f"  完整路径: {source_abs}")
                print("-" * 50)
                choice = input("确认删除此目录（包含所有内容）？输入 Y 确认: ").strip().lower()
                if choice == 'y':
                    if delete_dir(source_abs, recursive=True):
                        result.add_success(source_abs, "目录已删除")
                    else:
                        result.add_failed(source_abs, "删除失败")
                else:
                    result.add_skipped(source_abs, "用户取消")
            else:
                result = batch_delete(files, confirm=True)
        elif action == ActionType.MOVE:
            target = intent.get("target")
            if target:
                if not os.path.isabs(target):
                    target = os.path.join(self.workspace, target)
                result = batch_move(files, target)
            else:
                raise ValueError("缺少目标路径")
        elif action == ActionType.COPY:
            target = intent.get("target")
            if target:
                if not os.path.isabs(target):
                    target = os.path.join(self.workspace, target)
                result = batch_copy(files, target)
            else:
                raise ValueError("缺少目标路径")
        elif action == ActionType.RENAME:
            target = intent.get("target")
            params = intent.get("params", {})
            if "prefix" in params:
                result = batch_add_prefix(files, params["prefix"])
            elif "suffix" in params:
                result = batch_add_suffix(files, params["suffix"])
            elif "numbering" in params:
                result = batch_numbering(files, start=params.get("start", 1))
            elif target and len(files) == 1:
                # 单文件重命名：原文件名作为pattern，目标作为replacement
                old_name = Path(files[0]).name
                result = batch_rename(files, pattern=old_name, replacement=target)
            elif target and os.path.isdir(source):
                # 目录重命名
                result = BatchResult()
                new_dir_name = os.path.join(os.path.dirname(source), target)
                try:
                    os.rename(source, new_dir_name)
                    result.add_success(source, f"重命名为 {target}")
                except Exception as e:
                    result.add_failed(source, str(e))
            else:
                result = BatchResult()
        elif action == ActionType.ORGANIZE:
            target = intent.get("target") or source
            if not os.path.isabs(target):
                target = os.path.join(self.workspace, target)
            mode = intent.get("params", {}).get("organize_mode", "type")
            if mode == "type":
                result = organize_by_type(files, target)
            elif mode in ["month", "year", "day"]:
                result = organize_by_date(files, target, mode=mode)
            elif mode == "size":
                result = organize_by_size(files, target)
            elif mode == "course":
                use_ai = intent.get("params", {}).get("use_ai", True)
                preview = intent.get("params", {}).get("preview", False)
                result = organize_by_course(files, target, use_ai=use_ai, preview=preview)
            else:
                result = organize_by_type(files, target)
        elif action == ActionType.CLEAN:
            if "临时" in command or "垃圾" in command:
                result = clean_temp_files(source, confirm=True)
            elif "空文件" in command:
                result = clean_empty_files(source, confirm=True)
            elif "空目录" in command:
                result = clean_empty_dirs(source, confirm=True)
            else:
                days = 30
                for keyword, d in getattr(self.parser, "time_keywords", {}).items():
                    if keyword in command:
                        days = d
                        break
                result = clean_old_files(source, days, confirm=True)
        elif action == ActionType.SEARCH:
            result = BatchResult()
            for f in files:
                result.add_success(f)
        else:
            result = BatchResult()

        if verbose and result is not None:
            print_batch_result(result)

        return result

    def _apply_filter(self, files: List[str], filter_def: Dict) -> List[str]:
        """应用过滤条件（兼容枚举和字符串类型）"""
        ftype = filter_def["type"]

        # 统一：枚举或字符串都可以比较
        def match(ft):
            return ftype == ft or str(ftype) == ft

        if match(FilterType.EXTENSION) or ftype == "extension":
            val = filter_def["value"]
            if isinstance(val, dict) and "value" in val:
                val = val["value"]
            return filter_by_extension(files, val)
        elif match(FilterType.NAME_CONTAINS) or ftype == "name_contains":
            val = filter_def["value"]
            if isinstance(val, dict) and "value" in val:
                val = val["value"]
            return filter_by_name_contains(files, val)
        elif match(FilterType.NAME_PATTERN) or ftype == "name_pattern":
            return filter_by_name_pattern(files, filter_def["value"])
        elif match(FilterType.SIZE) or ftype == "size":
            kwargs = {}
            val = filter_def.get("value")
            if isinstance(val, dict) and "value" in val:
                val = val["value"]
            # 解析 "8MB" / "100MB" / "1GB" 等格式
            if isinstance(val, str) and val:
                val_lower = val.strip().lower()
                import re
                m = re.match(r"^([\d.]+)\s*(kb|mb|gb|b|bytes?)?$", val_lower)
                if m:
                    num = float(m.group(1))
                    unit = m.group(2) or "b"
                    if unit in ("b", "bytes"):
                        kwargs["min_size"] = int(num)
                    elif unit == "kb":
                        kwargs["min_size"] = int(num * 1024)
                    elif unit == "mb":
                        kwargs["min_size"] = int(num * 1024 * 1024)
                    elif unit == "gb":
                        kwargs["min_size"] = int(num * 1024 * 1024 * 1024)
            # 也支持原始的 min/max 字段
            if "min" in filter_def:
                kwargs["min_size"] = filter_def["min"]
            if "max" in filter_def:
                kwargs["max_size"] = filter_def["max"]
            if "min_mb" in filter_def:
                kwargs["min_mb"] = filter_def["min_mb"]
            if "max_mb" in filter_def:
                kwargs["max_mb"] = filter_def["max_mb"]
            return filter_by_size(files, **kwargs)
        elif match(FilterType.DATE) or ftype == "date" or ftype == "modified":
            days_ago = filter_def.get("days_ago")
            return filter_by_date(files, days_ago=days_ago)
        elif match(FilterType.TEMP) or ftype == "temp":
            return filter_temp_files(files)
        elif match(FilterType.EMPTY) or ftype == "empty":
            return filter_empty_files(files)

        return files

    def parse(self, command: str) -> Dict:
        """解析命令但不执行（纯AI）"""
        return self.parser.parse(command)

    def plan(self, command: str) -> List[Dict]:
        """生成执行计划"""
        return self.planner.create_plan(command)

    # ===== 直接接口（不经过自然语言解析） =====

    def list_files(self, path: str = None, recursive: bool = False) -> List[str]:
        """列出文件"""
        return get_files(path or self.workspace, recursive)

    def find(self, name: str = None, ext: str = None,
             recursive: bool = True) -> List[str]:
        """搜索文件"""
        return find_files(self.workspace, name_contains=name,
                         extension=ext, recursive=recursive)

    def move(self, files: List[str], target: str) -> BatchResult:
        """移动文件"""
        return batch_move(files, target)

    def copy(self, files: List[str], target: str) -> BatchResult:
        """复制文件"""
        return batch_copy(files, target)

    def delete(self, files: List[str], to_trash: bool = True) -> BatchResult:
        """删除文件"""
        return batch_delete(files, to_trash)

    def rename(self, files: List[str], pattern: str,
               replacement: str = "") -> BatchResult:
        """批量重命名"""
        return batch_rename(files, pattern, replacement)

    def organize_by_type(self, files: List[str] = None,
                         target: str = None) -> BatchResult:
        """按类型分类"""
        if files is None:
            files = self.list_files(recursive=True)
        return organize_by_type(files, target or self.workspace)

    def organize_by_date(self, files: List[str] = None,
                        target: str = None,
                        mode: str = "month") -> BatchResult:
        """按日期分类"""
        if files is None:
            files = self.list_files(recursive=True)
        return organize_by_date(files, target or self.workspace, mode)

    def organize_by_size(self, files: List[str] = None,
                         target: str = None) -> BatchResult:
        """按大小分类"""
        if files is None:
            files = self.list_files(recursive=True)
        return organize_by_size(files, target or self.workspace)

    def organize_by_course(self, files: List[str] = None,
                          target: str = None,
                          use_ai: bool = True,
                          preview: bool = False) -> BatchResult:
        """按课程分类（纯 AI 识别）"""
        if files is None:
            files = self.list_files(recursive=True)
        return organize_by_course(files, target or self.workspace, use_ai=use_ai, preview=preview)

    def clean_temp(self, path: str = None) -> BatchResult:
        """清理临时文件"""
        return clean_temp_files(path or self.workspace)

    def clean_empty(self, path: str = None) -> BatchResult:
        """清理空文件"""
        return clean_empty_files(path or self.workspace)

    def find_duplicates(self, path: str = None) -> Dict[str, List[str]]:
        """查找重复文件"""
        files = self.list_files(path or self.workspace, recursive=True)
        return get_duplicates(files)

    def analyze(self, path: str = None) -> Dict:
        """分析目录"""
        files = self.list_files(path or self.workspace, recursive=True)
        return {
            "total_files": count_files(files),
            "total_size": total_size_mb(files),
            "by_extension": count_by_extension(files),
            "largest_files": get_largest_files(files, 5),
            "duplicates": get_duplicates(files),
        }


# ===== 全局便捷函数 =====

# 创建一个默认实例
_default_helper = None

def get_helper(workspace: str = None) -> FileHelper:
    """获取默认的 FileHelper 实例"""
    global _default_helper
    if _default_helper is None:
        _default_helper = FileHelper(workspace)
    return _default_helper


def run_command(command: str, workspace: str = None, verbose: bool = True) -> BatchResult:
    """执行自然语言命令的便捷函数（纯AI）"""
    helper = get_helper(workspace)
    return helper.run(command, verbose=verbose)


# ===== 示例用法 =====

if __name__ == "__main__":
    # 示例1: 使用自然语言
    print("\n=== 示例1: 自然语言命令 ===")
    helper = FileHelper()
    helper.set_workspace(".")

    # 解析但不执行
    plan = helper.parse("把大于100MB的视频移到归档")
    print(f"解析结果: {plan}")

    # 示例2: 直接使用API
    print("\n=== 示例2: 直接使用API ===")
    files = helper.list_files(recursive=True)
    print(f"找到 {len(files)} 个文件")

    # 示例3: 按类型过滤
    print("\n=== 示例3: 按类型过滤 ===")
    py_files = find_files(".", extension="py", recursive=True)
    print(f"找到 {len(py_files)} 个 Python 文件")

    # 示例4: 分析目录
    print("\n=== 示例4: 分析目录 ===")
    stats = helper.analyze()
    print(f"总文件数: {stats['total_files']}")
    print(f"总大小: {stats['total_size']} MB")
    print(f"按类型统计: {stats['by_extension']}")
