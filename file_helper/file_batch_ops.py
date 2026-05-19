"""
File Batch Operations - 批量操作封装

基于原子操作的批量封装，但仍保持可拆分性。
每个批量操作都可以分解为原子操作的组合。
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Union, Callable

from .file_atomic_ops import (
    move_file, copy_file, delete_file, rename_file,
    get_file_info, get_file_name, get_extension, get_parent_dir,
    create_dir, is_dir, exists, ensure_dir
)
from .file_query import (
    filter_by_extension, filter_by_name_contains, filter_by_date,
    filter_by_size, group_by_extension, group_by_date, group_by_size,
    get_files_by_type, filter_temp_files, filter_empty_files
)


# ===== 操作结果容器 =====

class BatchResult:
    """批量操作结果"""

    def __init__(self):
        self.success = []
        self.failed = []
        self.skipped = []

    def add_success(self, path: str, info: str = ""):
        self.success.append({"path": path, "info": info})

    def add_failed(self, path: str, reason: str = ""):
        self.failed.append({"path": path, "reason": reason})

    def add_skipped(self, path: str, reason: str = ""):
        self.skipped.append({"path": path, "reason": reason})

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "failed": self.failed,
            "skipped": self.skipped,
            "total": len(self.success) + len(self.failed) + len(self.skipped),
            "success_count": len(self.success),
            "failed_count": len(self.failed),
            "skipped_count": len(self.skipped),
        }

    def __repr__(self):
        return f"BatchResult(success={len(self.success)}, failed={len(self.failed)}, skipped={len(self.skipped)})"


# ===== 批量移动/复制/删除 =====

def batch_move(files: List[str], dest_dir: str, overwrite: bool = False) -> BatchResult:
    """
    批量移动文件

    Args:
        files: 文件路径列表
        dest_dir: 目标目录
        overwrite: 是否覆盖已存在的文件

    Returns:
        BatchResult 对象
    """
    result = BatchResult()
    ensure_dir(dest_dir)

    # 列出要移动的文件
    valid_files = [f for f in files if exists(f)]
    if not valid_files:
        print("没有找到需要移动的文件")
        return result

    print(f"\n准备移动 {len(valid_files)} 个文件到 {dest_dir}")
    print("-" * 50)
    for f in valid_files:
        print(f"  → {Path(f).name}")
    print("-" * 50)

    for f in valid_files:
        dest_path = Path(dest_dir) / Path(f).name
        if dest_path.exists() and not overwrite:
            result.add_skipped(f, f"目标文件已存在: {dest_path}")
            continue

        if move_file(f, dest_dir):
            result.add_success(f, f"移动到 {dest_dir}")
        else:
            result.add_failed(f, "移动失败")

    return result


def batch_copy(files: List[str], dest_dir: str, overwrite: bool = False) -> BatchResult:
    """
    批量复制文件

    Args:
        files: 文件路径列表
        dest_dir: 目标目录
        overwrite: 是否覆盖已存在的文件

    Returns:
        BatchResult 对象
    """
    result = BatchResult()
    ensure_dir(dest_dir)

    # 列出要复制的文件
    valid_files = [f for f in files if exists(f)]
    if not valid_files:
        print("没有找到需要复制的文件")
        return result

    print(f"\n准备复制 {len(valid_files)} 个文件到 {dest_dir}")
    print("-" * 50)
    for f in valid_files:
        print(f"  → {Path(f).name}")
    print("-" * 50)

    for f in valid_files:
        dest_path = Path(dest_dir) / Path(f).name
        if dest_path.exists() and not overwrite:
            result.add_skipped(f, f"目标文件已存在: {dest_path}")
            continue

        if copy_file(f, dest_dir):
            result.add_success(f, f"复制到 {dest_dir}")
        else:
            result.add_failed(f, "复制失败")

    return result


def batch_delete(files: List[str], to_trash: bool = True, confirm: bool = True) -> BatchResult:
    """
    批量删除文件

    Args:
        files: 文件路径列表
        to_trash: 是否移至回收站
        confirm: 是否需要确认（默认True，危险操作）

    Returns:
        BatchResult 对象
    """
    result = BatchResult()

    # 过滤掉不存在的文件
    valid_files = [f for f in files if exists(f)]
    
    if not valid_files:
        print("没有找到需要删除的文件")
        return result

    # 显示要删除的文件
    print(f"\n⚠️ 危险操作：准备删除 {len(valid_files)} 个文件")
    print("-" * 50)
    for f in valid_files:
        print(f"  - {Path(f).name}")
    print("-" * 50)
    
    if confirm:
        # 询问确认（支持 Y/y）
        choice = input(f"确认删除这 {len(valid_files)} 个文件？输入 Y 确认: ").strip().lower()
        if choice != 'y':
            print("操作已取消")
            for f in valid_files:
                result.add_skipped(f, "用户取消")
            return result

    for f in valid_files:
        if delete_file(f, to_trash=to_trash):
            result.add_success(f, "已删除" if not to_trash else "已移至回收站")
        else:
            result.add_failed(f, "删除失败")

    return result


def batch_rename(files: List[str], pattern: str, replacement: str = "") -> BatchResult:
    """
    批量重命名（正则替换）

    Args:
        files: 文件路径列表
        pattern: 要替换的模式（正则表达式）
        replacement: 替换为的字符串

    Returns:
        BatchResult 对象
    """
    result = BatchResult()

    try:
        regex = re.compile(pattern)
    except re.error as e:
        result.add_failed("", f"无效的正则表达式: {e}")
        return result

    for f in files:
        old_name = Path(f).name
        new_name = regex.sub(replacement, old_name)

        if new_name == old_name:
            result.add_skipped(f, "名称未改变")
            continue

        if rename_file(f, new_name):
            result.add_success(f, f"重命名为 {new_name}")
        else:
            result.add_failed(f, "重命名失败")

    return result


def batch_add_prefix(files: List[str], prefix: str) -> BatchResult:
    """
    批量添加前缀

    Args:
        files: 文件路径列表
        prefix: 前缀字符串

    Returns:
        BatchResult 对象
    """
    result = BatchResult()

    for f in files:
        old_name = Path(f).name
        new_name = prefix + old_name

        if rename_file(f, new_name):
            result.add_success(f, f"添加前缀: {new_name}")
        else:
            result.add_failed(f, "重命名失败")

    return result


def batch_add_suffix(files: List[str], suffix: str, before_extension: bool = True) -> BatchResult:
    """
    批量添加后缀

    Args:
        files: 文件路径列表
        suffix: 后缀字符串
        before_extension: 是否在扩展名前添加（默认True）

    Returns:
        BatchResult 对象
    """
    result = BatchResult()

    for f in files:
        path = Path(f)
        old_name = path.name

        if before_extension:
            new_name = path.stem + suffix + path.suffix
        else:
            new_name = old_name + suffix

        if rename_file(f, new_name):
            result.add_success(f, f"添加后缀: {new_name}")
        else:
            result.add_failed(f, "重命名失败")

    return result


def batch_remove_pattern(files: List[str], pattern: str) -> BatchResult:
    """
    批量移除匹配的模式

    Args:
        files: 文件路径列表
        pattern: 要移除的模式（字符串或正则）

    Returns:
        BatchResult 对象
    """
    return batch_rename(files, re.escape(pattern), "")


def batch_numbering(files: List[str], start: int = 1, pattern: str = "{n}_{name}",
                   keep_extension: bool = True) -> BatchResult:
    """
    批量编号

    Args:
        files: 文件路径列表
        start: 起始编号
        pattern: 命名模式，支持 {n}（序号）、{name}（原名）、{ext}（扩展名）
        keep_extension: 是否保留原扩展名

    Returns:
        BatchResult 对象
    """
    result = BatchResult()

    for i, f in enumerate(files, start=start):
        path = Path(f)
        old_name = path.name

        if keep_extension:
            name_part = path.stem
            ext_part = path.suffix
        else:
            name_part = old_name
            ext_part = ""

        new_name = pattern.format(n=i, name=name_part, ext=ext_part)
        if keep_extension:
            new_name = new_name + ext_part

        if rename_file(f, new_name):
            result.add_success(f, f"编号为 {new_name}")
        else:
            result.add_failed(f, "重命名失败")

    return result


def batch_change_extension(files: List[str], new_extension: str) -> BatchResult:
    """
    批量更改扩展名

    Args:
        files: 文件路径列表
        new_extension: 新扩展名（不含点）

    Returns:
        BatchResult 对象
    """
    result = BatchResult()

    if new_extension:
        new_extension = "." + new_extension.lstrip(".")
    else:
        new_extension = ""

    for f in files:
        path = Path(f)
        new_name = path.stem + new_extension

        if rename_file(f, new_name):
            result.add_success(f, f"扩展名改为 {new_extension}")
        else:
            result.add_failed(f, "重命名失败")

    return result


def batch_replace_in_name(files: List[str], old: str, new: str,
                          case_sensitive: bool = False) -> BatchResult:
    """
    批量替换文件名中的字符串

    Args:
        files: 文件路径列表
        old: 要替换的字符串
        new: 替换为的字符串
        case_sensitive: 是否区分大小写

    Returns:
        BatchResult 对象
    """
    result = BatchResult()

    for f in files:
        old_name = Path(f).name

        if case_sensitive:
            new_name = old_name.replace(old, new)
        else:
            # 不区分大小写的替换
            pattern = re.compile(re.escape(old), re.IGNORECASE)
            new_name = pattern.sub(new, old_name)

        if new_name == old_name:
            result.add_skipped(f, "名称未改变")
            continue

        if rename_file(f, new_name):
            result.add_success(f, f"替换为 {new_name}")
        else:
            result.add_failed(f, "重命名失败")

    return result


def batch_replace_spaces(files: List[str], replacement: str = "_") -> BatchResult:
    """
    批量替换空格为其他字符

    Args:
        files: 文件路径列表
        replacement: 替换为空格为什么字符

    Returns:
        BatchResult 对象
    """
    return batch_replace_in_name(files, " ", replacement)


# ===== 分类整理 =====

def organize_by_type(files: List[str], base_dir: str,
                     create_subdirs: bool = True) -> BatchResult:
    """
    按文件类型分类

    Args:
        files: 文件路径列表
        base_dir: 基础目录（分类后的文件将放在这里）
        create_subdirs: 是否为每种类型创建子目录

    Returns:
        BatchResult 对象
    """
    result = BatchResult()

    # 类型到中文目录名的映射
    type_mapping = {
        "image": "图片",
        "video": "视频",
        "audio": "音频",
        "document": "文档",
        "code": "代码",
        "archive": "压缩包",
        "pdf": "PDF文档",
        "docx": "Word文档",
        "xlsx": "Excel文档",
        "pptx": "PPT文档",
        "txt": "文本文件",
        "jpg": "图片",
        "png": "图片",
        "gif": "图片",
        "mp4": "视频",
        "mp3": "音频",
        "zip": "压缩包",
        "rar": "压缩包",
    }

    # 按扩展名分组
    groups = group_by_extension(files)

    # 显示总览
    print(f"\n准备将 {len(files)} 个文件按类型分类")
    print("-" * 50)

    if create_subdirs:
        ensure_dir(base_dir)
        created_dirs = set()

        for ext, ext_files in groups.items():
            # 跳过没有扩展名的文件
            if ext == "no_extension":
                for f in ext_files:
                    print(f"  → {Path(f).name} → (根目录)")
                    dest_dir = base_dir
                    if move_file(f, dest_dir):
                        result.add_success(f, f"移动到 {dest_dir}")
                    else:
                        result.add_failed(f, "移动失败")
                continue

            # 获取目标目录名
            dir_name = type_mapping.get(ext, f"{ext.upper()}文件")
            target_dir = Path(base_dir) / dir_name

            if str(target_dir) not in created_dirs:
                ensure_dir(str(target_dir))
                created_dirs.add(str(target_dir))

            # 移动文件
            for f in ext_files:
                print(f"  → {Path(f).name} → {dir_name}/")
                if move_file(f, str(target_dir)):
                    result.add_success(f, f"移动到 {target_dir}")
                else:
                    result.add_failed(f, "移动失败")
    else:
        # 不创建子目录，只收集结果
        for ext, ext_files in groups.items():
            for f in ext_files:
                result.add_success(f, f"属于 {ext} 类型")

    print("-" * 50)
    return result


def organize_by_date(files: List[str], base_dir: str,
                    mode: str = "month",
                    date_format: str = None) -> BatchResult:
    """
    按日期分类

    Args:
        files: 文件路径列表
        base_dir: 基础目录
        mode: "year" | "month" | "day"
        date_format: 自定义日期格式，默认根据mode自动设置

    Returns:
        BatchResult 对象
    """
    result = BatchResult()

    if date_format is None:
        if mode == "year":
            date_format = "%Y"
        elif mode == "month":
            date_format = "%Y-%m"
        else:
            date_format = "%Y-%m-%d"

    # 按日期分组
    groups = group_by_date(files, mode)

    # 显示总览
    print(f"\n准备将 {len(files)} 个文件按日期({mode})分类")
    print("-" * 50)

    ensure_dir(base_dir)
    created_dirs = set()

    for date_key, date_files in groups.items():
        # 使用日期作为目录名
        target_dir = Path(base_dir) / date_key

        if str(target_dir) not in created_dirs:
            ensure_dir(str(target_dir))
            created_dirs.add(str(target_dir))

        for f in date_files:
            print(f"  → {Path(f).name} → {date_key}/")
            if move_file(f, str(target_dir)):
                result.add_success(f, f"移动到 {target_dir}")
            else:
                result.add_failed(f, "移动失败")

    print("-" * 50)
    return result


def organize_by_size(files: List[str], base_dir: str,
                    thresholds: List[int] = None) -> BatchResult:
    """
    按文件大小分类

    Args:
        files: 文件路径列表
        base_dir: 基础目录
        thresholds: 大小区间（MB），如 [1, 10, 100] 表示: 小文件(<1MB)、中文件(1-10MB)、大文件(10-100MB)、超大文件(>100MB)

    Returns:
        BatchResult 对象
    """
    result = BatchResult()

    if thresholds is None:
        thresholds = [1, 10, 100]  # MB

    # 转换为字节
    thresholds_bytes = [t * 1024 * 1024 for t in thresholds]

    # 创建目录名
    size_names = [f"小于{thresholds[0]}MB"]
    for i in range(len(thresholds) - 1):
        size_names.append(f"{thresholds[i]}-{thresholds[i+1]}MB")
    size_names.append(f"大于{thresholds[-1]}MB")

    # 按大小分组
    groups = group_by_size(files, thresholds_bytes)

    # 显示总览
    print(f"\n准备将 {len(files)} 个文件按大小分类")
    print("-" * 50)

    ensure_dir(base_dir)
    created_dirs = set()

    for (size_range, size_files), dir_name in zip(groups.items(), size_names):
        target_dir = Path(base_dir) / dir_name

        if str(target_dir) not in created_dirs:
            ensure_dir(str(target_dir))
            created_dirs.add(str(target_dir))

        for f in size_files:
            print(f"  → {Path(f).name} → {dir_name}/")
            if move_file(f, str(target_dir)):
                result.add_success(f, f"移动到 {target_dir}")
            else:
                result.add_failed(f, "移动失败")

    print("-" * 50)
    return result


def organize_by_custom(files: List[str], base_dir: str,
                       categorizer: Callable[[str], str]) -> BatchResult:
    """
    按自定义规则分类

    Args:
        files: 文件路径列表
        base_dir: 基础目录
        categorizer: 分类函数，接收文件路径，返回分类目录名

    Returns:
        BatchResult 对象
    """
    result = BatchResult()

    ensure_dir(base_dir)
    created_dirs = set()

    for f in files:
        try:
            category = categorizer(f)
        except Exception:
            category = "其他"

        target_dir = Path(base_dir) / category

        if str(target_dir) not in created_dirs:
            ensure_dir(str(target_dir))
            created_dirs.add(str(target_dir))

        if move_file(f, str(target_dir)):
            result.add_success(f, f"移动到 {target_dir}")
        else:
            result.add_failed(f, "移动失败")

    return result


# ===== 创建目录结构 =====

def create_structure(base_dir: str, categories: List[str]) -> BatchResult:
    """
    创建分类目录结构

    Args:
        base_dir: 基础目录
        categories: 子目录名称列表

    Returns:
        BatchResult 对象
    """
    result = BatchResult()

    ensure_dir(base_dir)

    for category in categories:
        target_dir = Path(base_dir) / category
        if ensure_dir(str(target_dir)):
            result.add_success(str(target_dir), "目录已创建")
        else:
            result.add_failed(str(target_dir), "创建失败")

    return result


def create_date_structure(base_dir: str, years: List[int] = None) -> BatchResult:
    """
    创建按年份整理的目录结构

    Args:
        base_dir: 基础目录
        years: 年份列表，默认当前年份

    Returns:
        BatchResult 对象
    """
    if years is None:
        years = [datetime.now().year]

    categories = [str(year) for year in years]
    return create_structure(base_dir, categories)


# ===== 清理操作 =====

def clean_temp_files(directory: str, to_trash: bool = True, confirm: bool = True) -> BatchResult:
    """
    清理临时文件

    Args:
        directory: 目录路径
        to_trash: 是否移至回收站（强烈建议 True）
        confirm: 是否需要确认（默认 True）

    Returns:
        BatchResult 对象
    """
    from file_atomic_ops import get_files

    files = get_files(directory, recursive=True)
    temp_files = filter_temp_files(files)

    if not temp_files:
        print("没有找到临时文件")
        return BatchResult()

    # 强制使用回收站，除非明确指定 to_trash=False
    return batch_delete(temp_files, to_trash=True, confirm=confirm)


def clean_empty_files(directory: str, to_trash: bool = True, confirm: bool = True) -> BatchResult:
    """
    清理空文件

    Args:
        directory: 目录路径
        to_trash: 是否移至回收站（强烈建议 True）
        confirm: 是否需要确认（默认 True）

    Returns:
        BatchResult 对象
    """
    from file_atomic_ops import get_files

    files = get_files(directory, recursive=True)
    empty_files = filter_empty_files(files)

    if not empty_files:
        print("没有找到空文件")
        return BatchResult()

    # 强制使用回收站，除非明确指定 to_trash=False
    return batch_delete(empty_files, to_trash=True, confirm=confirm)


def clean_empty_dirs(directory: str, confirm: bool = True) -> BatchResult:
    """
    清理空目录

    Args:
        directory: 目录路径
        confirm: 是否需要确认（默认True，危险操作）

    Returns:
        BatchResult 对象
    """
    from file_atomic_ops import get_dirs, is_empty_dir, delete_dir

    result = BatchResult()
    dirs = get_dirs(directory, recursive=True)

    # 找出所有空目录
    empty_dirs = []
    for d in sorted(dirs, key=lambda x: x.count(os.sep), reverse=True):
        if is_empty_dir(d):
            empty_dirs.append(d)

    if not empty_dirs:
        print("没有找到空目录")
        return result

    # 显示要删除的空目录
    print(f"\n⚠️ 危险操作：准备删除 {len(empty_dirs)} 个空目录")
    print("-" * 50)
    for d in empty_dirs:
        print(f"  - {d}")
    print("-" * 50)
    
    if confirm:
        # 询问确认（支持 Y/y）
        choice = input(f"确认删除这 {len(empty_dirs)} 个空目录？输入 Y 确认: ").strip().lower()
        if choice != 'y':
            print("操作已取消")
            for d in empty_dirs:
                result.add_skipped(d, "用户取消")
            return result

    # 从最深层开始检查，逐层删除
    for d in empty_dirs:
        if delete_dir(d, recursive=False):
            result.add_success(d, "已删除空目录")
        else:
            result.add_failed(d, "删除失败")

    return result


def clean_old_files(directory: str, days: int, to_trash: bool = True,
                   extensions: List[str] = None, confirm: bool = True) -> BatchResult:
    """
    清理旧文件

    Args:
        directory: 目录路径
        days: 多少天前的文件
        to_trash: 是否移至回收站（强烈建议 True）
        extensions: 只清理指定扩展名的文件
        confirm: 是否需要确认（默认 True）

    Returns:
        BatchResult 对象
    """
    from file_atomic_ops import get_files

    files = get_files(directory, recursive=True)

    # 按扩展名过滤
    if extensions:
        files = filter_by_extension(files, extensions)

    # 按日期过滤
    old_files = filter_by_date(files, days_ago=days)

    if not old_files:
        print(f"没有找到 {days} 天前的文件")
        return BatchResult()

    # 强制使用回收站，除非明确指定 to_trash=False
    return batch_delete(old_files, to_trash=True, confirm=confirm)


def clean_large_files(directory: str, size_mb: int,
                     to_trash: bool = True) -> BatchResult:
    """
    清理大于指定大小的文件

    Args:
        directory: 目录路径
        size_mb: 大小阈值（MB）
        to_trash: 是否移至回收站

    Returns:
        BatchResult 对象
    """
    from file_atomic_ops import get_files

    files = get_files(directory, recursive=True)
    large_files = filter_by_size(files, min_mb=size_mb)

    return batch_delete(large_files, to_trash=to_trash)


# ===== 备份操作 =====

def backup_files(files: List[str], backup_dir: str) -> BatchResult:
    """
    备份文件到指定目录

    Args:
        files: 文件路径列表
        backup_dir: 备份目录

    Returns:
        BatchResult 对象
    """
    result = BatchResult()
    ensure_dir(backup_dir)

    for f in files:
        dest = Path(backup_dir) / Path(f).name

        # 如果文件名冲突，加上时间戳
        if dest.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = Path(backup_dir) / f"{Path(f).stem}_{timestamp}{Path(f).suffix}"

        if copy_file(f, str(dest)):
            result.add_success(f, f"备份到 {dest}")
        else:
            result.add_failed(f, "备份失败")

    return result


# ===== 同步操作 =====

def sync_files(src_dir: str, dst_dir: str,
              direction: str = "copy") -> BatchResult:
    """
    同步两个目录

    Args:
        src_dir: 源目录
        dst_dir: 目标目录
        direction: "copy"（复制新文件到目标）| "move"（移动新文件到目标）

    Returns:
        BatchResult 对象
    """
    from file_atomic_ops import get_files

    result = BatchResult()
    ensure_dir(dst_dir)

    src_files = set(get_files(src_dir))
    dst_files = set(get_files(dst_dir))

    # 找出源目录中有但目标目录没有的文件
    files_to_sync = []
    for f in src_files:
        rel_path = Path(f).name  # 简化版，只处理同名文件
        dst_file = Path(dst_dir) / Path(f).name
        if not dst_file.exists():
            files_to_sync.append(f)

    if direction == "copy":
        return batch_copy(files_to_sync, dst_dir)
    else:  # move
        return batch_move(files_to_sync, dst_dir)


def organize_by_course(files: List[str], base_dir: str,
                      use_ai: bool = True, preview: bool = False):
    """
    按课程分类文件（纯 AI 识别）。

    识别成功 → 移动到对应课程文件夹（CS307_数据库原理/）
    无法识别 → 移动到 "其它/"

    Args:
        files: 文件路径列表
        base_dir: 基础目录
        use_ai: 是否调用 AI（推荐开启）
        preview: True=只打印预览不移动，False=实际移动

    Returns:
        BatchResult 对象（preview 模式下 success 包含预览信息）
    """
    from .course_config import identify_course_for_file, get_folder_name, load_courses

    result = BatchResult()
    ensure_dir(base_dir)

    # 加载已知课程代码
    known_codes = {c['code'] for c in load_courses()}

    course_map, other_files = {}, []

    for f in files:
        code, name, conf = identify_course_for_file(f, use_ai=use_ai)
        if code != "OTHER":
            folder = get_folder_name(code, name)
            course_map.setdefault(folder, []).append(f"{f} → {folder}/")
        else:
            other_files.append(f"{f} → 其它/")

    # ===== 预览模式 =====
    if preview:
        print(f"\n{'='*50}")
        print(f"[预览] 分类结果（{len(files)} 个文件）")
        print(f"{'='*50}")
        for folder, flist in sorted(course_map.items()):
            print(f"\n📁 {folder}/ ({len(flist)} 个)")
            for fi in flist:
                print(f"   {fi.split(' → ')[0]}")
        if other_files:
            print(f"\n📁 其它/ ({len(other_files)} 个)")
            for fi in other_files:
                print(f"   {fi.split(' → ')[0]}")
        print(f"\n{'='*50}")
        print(f"提示：preview=False 时会实际移动文件")
        return result

    # ===== 执行模式 =====
    total_files = len(files)
    print(f"\n准备将 {total_files} 个文件按课程分类")
    print("-" * 50)
    
    for folder, flist in sorted(course_map.items()):
        target = Path(base_dir) / folder
        ensure_dir(str(target))
        for fi in flist:
            src = fi.split(" → ")[0]
            print(f"  → {Path(src).name} → {folder}/")
            if move_file(src, str(target)):
                result.add_success(src, f"移动到 {target}")
            else:
                result.add_failed(src, "移动失败")

    if other_files:
        target = Path(base_dir) / "其它"
        ensure_dir(str(target))
        for fi in other_files:
            src = fi.split(" → ")[0]
            print(f"  → {Path(src).name} → 其它/")
            if move_file(src, str(target)):
                result.add_success(src, "移动到 其它")
            else:
                result.add_failed(src, "移动失败")

    print("-" * 50)
    return result


# ===== 打印结果 =====

def print_batch_result(result: BatchResult, verbose: bool = False):
    """
    打印批量操作结果

    Args:
        result: BatchResult 对象
        verbose: 是否打印详细信息
    """
    print(f"\n{'='*50}")
    print(f"操作完成:")
    print(f"  成功: {len(result.success)}")
    print(f"  失败: {len(result.failed)}")

    if verbose:
        if result.success:
            print(f"\n成功列表:")
            for item in result.success[:10]:
                info = item.get('info', '')
                print(f"  [OK] {item['path']}" + (f" - {info}" if info else ""))
            if len(result.success) > 10:
                print(f"  ... 还有 {len(result.success) - 10} 个")

        if result.failed:
            print(f"\n失败列表:")
            for item in result.failed[:10]:
                reason = item.get('reason', '')
                print(f"  [X] {item['path']}" + (f" - {reason}" if reason else ""))
            if len(result.failed) > 10:
                print(f"  ... 还有 {len(result.failed) - 10} 个")

        skipped = getattr(result, 'skipped', None)
        if skipped:
            print(f"\n跳过列表:")
            for item in skipped[:5]:
                print(f"  [-] {item.get('path', '')} - {item.get('reason', '')}")
            if len(skipped) > 5:
                print(f"  ... 还有 {len(skipped) - 5} 个")

    print(f"{'='*50}\n")
