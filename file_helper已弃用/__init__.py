"""
File Helper - 文件管理助手

一个基于自然语言的文件管理工具包。
采用原子化函数 + 灵活组合的设计理念。

使用示例:
    from file_helper import FileHelper, run_command

    # 使用自然语言
    run_command("把大于100MB的视频移到归档")

    # 或使用 Python API
    helper = FileHelper()
    files = helper.find(ext="pdf")
"""

from .file_atomic_ops import *
from .file_query import *
from .file_batch_ops import *
from .intent_parser import *
from .file_helper import FileHelper, get_helper, run_command
from .tis_course_fetcher import TISCourseFetcher

__version__ = "0.1.0"
__all__ = [
    # 原子操作
    "get_files", "get_dirs", "get_file_info", "exists", "is_file", "is_dir",
    "move_file", "copy_file", "delete_file", "rename_file",
    "create_dir", "delete_dir", "get_dir_size",

    # 查询过滤
    "filter_by_extension", "filter_by_name_contains", "filter_by_size",
    "filter_by_date", "filter_temp_files", "filter_empty_files",
    "group_by_extension", "group_by_date",
    "find_files", "get_duplicates",

    # 批量操作
    "batch_move", "batch_copy", "batch_delete", "batch_rename",
    "organize_by_type", "organize_by_date", "organize_by_size", "organize_by_course",
    "clean_temp_files", "clean_empty_files", "BatchResult",

    # 意图解析
    "parse_command", "plan_execution",

    # 主入口
    "FileHelper", "get_helper", "run_command",

    # TIS 选课数据爬取
    "TISCourseFetcher",
]
