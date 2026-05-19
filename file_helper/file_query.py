"""
File Query - 查询过滤原子函数

用于查询和过滤文件集合的原子函数。
这些函数接收文件列表，返回过滤/处理后的文件列表。
"""

import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Callable, Optional, Union

from .file_atomic_ops import (
    get_file_info,
    get_extension,
    get_file_size,
    get_modified_time,
    get_file_hash,
)


# ===== 文件列表过滤 =====

def filter_by_extension(files: List[str], extensions: Union[List[str], str]) -> List[str]:
    """
    按扩展名过滤文件

    Args:
        files: 文件路径列表
        extensions: 扩展名列表或单个扩展名（不区分大小写）

    Returns:
        符合条件的文件列表
    """
    if extensions is None:
        return files
    if isinstance(extensions, str):
        extensions = [extensions]
    if not extensions:
        return files

    ext_set = set()
    for ext in extensions:
        ext_set.add(ext.lower().lstrip("."))

    result = []
    for f in files:
        fext = get_extension(f).lower()
        if fext in ext_set:
            result.append(f)
    return result


def filter_by_name_pattern(files: List[str], pattern: str) -> List[str]:
    """
    按文件名模式过滤（支持通配符 * 和 ?）

    Args:
        files: 文件路径列表
        pattern: 通配符模式

    Returns:
        符合条件的文件列表
    """
    # 将通配符转换为正则表达式
    regex_pattern = pattern.replace(".", r"\.").replace("*", ".*").replace("?", ".")
    regex = re.compile(regex_pattern, re.IGNORECASE)

    return [
        f for f in files
        if regex.search(Path(f).name)
    ]


def filter_by_name_regex(files: List[str], regex_pattern: str) -> List[str]:
    """
    按正则表达式过滤文件名

    Args:
        files: 文件路径列表
        regex_pattern: 正则表达式模式

    Returns:
        符合条件的文件列表
    """
    try:
        regex = re.compile(regex_pattern, re.IGNORECASE)
        return [f for f in files if regex.search(Path(f).name)]
    except re.error:
        return []


def filter_by_size(
    files: List[str],
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    min_mb: Optional[float] = None,
    max_mb: Optional[float] = None
) -> List[str]:
    """
    按文件大小过滤

    Args:
        files: 文件路径列表
        min_size: 最小大小（字节）
        max_size: 最大大小（字节）
        min_mb: 最小大小（MB）
        max_mb: 最大大小（MB）

    Returns:
        符合条件的文件列表
    """
    # 转换MB为字节
    if min_mb is not None:
        min_size = int(min_mb * 1024 * 1024)
    if max_mb is not None:
        max_size = int(max_mb * 1024 * 1024)

    result = []
    for f in files:
        size = get_file_size(f)
        if min_size is not None and size < min_size:
            continue
        if max_size is not None and size > max_size:
            continue
        result.append(f)

    return result


def filter_by_date(
    files: List[str],
    after: Optional[datetime] = None,
    before: Optional[datetime] = None,
    days_ago: Optional[int] = None
) -> List[str]:
    """
    按修改时间过滤

    Args:
        files: 文件路径列表
        after: 在此日期之后
        before: 在此日期之前
        days_ago: 最近N天内

    Returns:
        符合条件的文件列表
    """
    if days_ago is not None:
        after = datetime.now() - timedelta(days=days_ago)

    result = []
    for f in files:
        mtime = get_modified_time(f)
        if mtime is None:
            continue
        if after is not None and mtime < after:
            continue
        if before is not None and mtime > before:
            continue
        result.append(f)

    return result


def filter_by_name_contains(files: List[str], keyword: str, case_sensitive: bool = False) -> List[str]:
    """
    文件名包含关键词（支持多关键词 OR 匹配）

    Args:
        files: 文件路径列表
        keyword: 关键词（str）或关键词列表（list），列表时为 OR 匹配
        case_sensitive: 是否区分大小写

    Returns:
        符合条件的文件列表
    """
    # 支持多关键词 OR 匹配
    if isinstance(keyword, list):
        keywords = keyword
    else:
        keywords = [keyword]

    if case_sensitive:
        return [f for f in files if any(kw in Path(f).name for kw in keywords)]
    else:
        return [f for f in files if any(kw.lower() in Path(f).name.lower() for kw in keywords)]


def filter_by_name_not_contains(files: List[str], keyword: str, case_sensitive: bool = False) -> List[str]:
    """
    文件名不包含关键词

    Args:
        files: 文件路径列表
        keyword: 关键词
        case_sensitive: 是否区分大小写

    Returns:
        符合条件的文件列表
    """
    if case_sensitive:
        return [f for f in files if keyword not in Path(f).name]
    else:
        keyword_lower = keyword.lower()
        return [f for f in files if keyword_lower not in Path(f).name.lower()]


def filter_by_name_startswith(files: List[str], prefix: str, case_sensitive: bool = False) -> List[str]:
    """
    文件名以指定前缀开头

    Args:
        files: 文件路径列表
        prefix: 前缀
        case_sensitive: 是否区分大小写

    Returns:
        符合条件的文件列表
    """
    if case_sensitive:
        return [f for f in files if Path(f).name.startswith(prefix)]
    else:
        prefix_lower = prefix.lower()
        return [f for f in files if Path(f).name[:len(prefix)].lower() == prefix_lower]


def filter_by_name_endswith(files: List[str], suffix: str, case_sensitive: bool = False) -> List[str]:
    """
    文件名以指定后缀结尾

    Args:
        files: 文件路径列表
        suffix: 后缀（包括扩展名）
        case_sensitive: 是否区分大小写

    Returns:
        符合条件的文件列表
    """
    if case_sensitive:
        return [f for f in files if Path(f).name.endswith(suffix)]
    else:
        suffix_lower = suffix.lower()
        return [f for f in files if Path(f).name[-len(suffix):].lower() == suffix_lower]


def filter_by_path_contains(files: List[str], keyword: str) -> List[str]:
    """
    文件路径包含关键词

    Args:
        files: 文件路径列表
        keyword: 关键词

    Returns:
        符合条件的文件列表
    """
    keyword_lower = keyword.lower()
    return [f for f in files if keyword_lower in f.lower()]


def filter_existing(files: List[str]) -> List[str]:
    """过滤掉不存在的文件"""
    return [f for f in files if Path(f).exists()]


def filter_hidden(files: List[str]) -> List[str]:
    """过滤隐藏文件（以.开头或Windows隐藏属性）"""
    import os
    result = []
    for f in files:
        name = Path(f).name
        if name.startswith("."):
            continue
        # Windows 隐藏文件检查
        if os.name == "nt":
            try:
                import ctypes
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(Path(f).resolve()))
                if attrs != -1 and attrs & 2:  # FILE_ATTRIBUTE_HIDDEN
                    continue
            except Exception:
                pass
        result.append(f)
    return result


# ===== 文件列表排序 =====

def sort_by_name(files: List[str], reverse: bool = False) -> List[str]:
    """按文件名排序"""
    return sorted(files, key=lambda x: Path(x).name.lower(), reverse=reverse)


def sort_by_size(files: List[str], reverse: bool = True) -> List[str]:
    """按文件大小排序"""
    return sorted(files, key=lambda x: get_file_size(x), reverse=reverse)


def sort_by_date(files: List[str], reverse: bool = True) -> List[str]:
    """按修改时间排序"""
    return sorted(files, key=lambda x: get_modified_time(x) or datetime.min, reverse=reverse)


def sort_by_extension(files: List[str]) -> List[str]:
    """按扩展名分组排序（先按扩展名，再按名称）"""
    return sorted(files, key=lambda x: (get_extension(x).lower(), Path(x).name.lower()))


def sort_by_path(files: List[str], reverse: bool = False) -> List[str]:
    """按路径排序"""
    return sorted(files, key=lambda x: x.lower(), reverse=reverse)


# ===== 文件列表分组 =====

def group_by_extension(files: List[str]) -> Dict[str, List[str]]:
    """
    按扩展名分组

    Returns:
        {"pdf": [文件1, 文件2], "docx": [文件3], ...}
    """
    groups = {}
    for f in files:
        ext = get_extension(f).lower() or "no_extension"
        if ext not in groups:
            groups[ext] = []
        groups[ext].append(f)
    return groups


def group_by_date(files: List[str], mode: str = "month") -> Dict[str, List[str]]:
    """
    按修改日期分组

    Args:
        mode: "year" | "month" | "day"

    Returns:
        {"2024": {"/path/to/file1"}, ...}
        或 {"2024-01": [...], ...}
        或 {"2024-01-15": [...], ...}
    """
    groups = {}
    for f in files:
        mtime = get_modified_time(f)
        if mtime is None:
            key = "unknown"
        elif mode == "year":
            key = str(mtime.year)
        elif mode == "month":
            key = f"{mtime.year}-{mtime.month:02d}"
        else:  # day
            key = f"{mtime.year}-{mtime.month:02d}-{mtime.day:02d}"

        if key not in groups:
            groups[key] = []
        groups[key].append(f)

    return groups


def group_by_size(files: List[str], thresholds: List[int] = None) -> Dict[str, List[str]]:
    """
    按文件大小区间分组

    Args:
        thresholds: 大小区间（字节），如 [1024*1024, 10*1024*1024, 100*1024*1024]
                    表示: <1MB, 1-10MB, 10-100MB, >100MB

    Returns:
        {"<1MB": [...], "1-10MB": [...], ...}
    """
    if thresholds is None:
        # 默认阈值: 1MB, 10MB, 100MB
        thresholds = [1024*1024, 10*1024*1024, 100*1024*1024]

    groups = {f"<{thresholds[0]//(1024*1024)}MB": []}

    for i in range(len(thresholds) - 1):
        min_mb = thresholds[i] // (1024*1024)
        max_mb = thresholds[i+1] // (1024*1024)
        groups[f"{min_mb}-{max_mb}MB"] = []

    groups[f">{thresholds[-1]//(1024*1024)}MB"] = []

    for f in files:
        size = get_file_size(f)
        placed = False

        for i, threshold in enumerate(thresholds):
            if size < threshold:
                if i == 0:
                    groups[f"<{threshold//(1024*1024)}MB"].append(f)
                else:
                    min_mb = thresholds[i-1] // (1024*1024)
                    max_mb = threshold // (1024*1024)
                    groups[f"{min_mb}-{max_mb}MB"].append(f)
                placed = True
                break

        if not placed:
            groups[f">{thresholds[-1]//(1024*1024)}MB"].append(f)

    return groups


def group_by_first_letter(files: List[str]) -> Dict[str, List[str]]:
    """按文件名首字母分组"""
    groups = {}
    for f in files:
        name = Path(f).name
        letter = name[0].upper() if name and name[0].isalpha() else "#"
        if letter not in groups:
            groups[letter] = []
        groups[letter].append(f)
    return groups


# ===== 去重 =====

def unique_by_name(files: List[str]) -> List[str]:
    """按文件名去重（保留第一个）"""
    seen = set()
    result = []
    for f in files:
        name = Path(f).name
        if name not in seen:
            seen.add(name)
            result.append(f)
    return result


def unique_by_content(files: List[str]) -> List[str]:
    """
    按文件内容去重（通过哈希）

    Returns:
        不重复的文件列表
    """
    seen = {}
    result = []
    for f in files:
        try:
            hash_val = get_file_hash(f)
            if hash_val not in seen:
                seen[hash_val] = f
                result.append(f)
        except Exception:
            # 无法读取的文件，跳过
            pass
    return result


def get_duplicates(files: List[str]) -> Dict[str, List[str]]:
    """
    查找重复文件（按内容哈希）

    Returns:
        {哈希值: [文件1, 文件2, ...], ...}
        只返回有重复的组
    """
    hash_to_files = {}
    for f in files:
        try:
            hash_val = get_file_hash(f)
            if hash_val not in hash_to_files:
                hash_to_files[hash_val] = []
            hash_to_files[hash_val].append(f)
        except Exception:
            pass

    # 只返回有重复的
    return {k: v for k, v in hash_to_files.items() if len(v) > 1}


# ===== 统计计算 =====

def count_files(files: List[str]) -> int:
    """统计文件数量"""
    return len(files)


def count_by_extension(files: List[str]) -> Dict[str, int]:
    """统计各类型文件数量"""
    counts = {}
    for f in files:
        ext = get_extension(f).lower() or "no_extension"
        counts[ext] = counts.get(ext, 0) + 1
    return counts


def total_size(files: List[str]) -> int:
    """计算文件总大小（字节）"""
    return sum(get_file_size(f) for f in files)


def total_size_mb(files: List[str]) -> float:
    """计算文件总大小（MB）"""
    return round(total_size(files) / (1024 * 1024), 2)


def average_size(files: List[str]) -> int:
    """计算文件平均大小（字节）"""
    if not files:
        return 0
    return total_size(files) // len(files)


def average_size_mb(files: List[str]) -> float:
    """计算文件平均大小（MB）"""
    if not files:
        return 0.0
    return round(total_size_mb(files) / len(files), 2)


def get_largest_files(files: List[str], n: int = 10) -> List[tuple]:
    """
    获取最大的N个文件

    Returns:
        [(文件路径, 大小), ...] 按大小降序
    """
    files_with_size = [(f, get_file_size(f)) for f in files]
    files_with_size.sort(key=lambda x: x[1], reverse=True)
    return files_with_size[:n]


def get_smallest_files(files: List[str], n: int = 10) -> List[tuple]:
    """
    获取最小的N个文件

    Returns:
        [(文件路径, 大小), ...] 按大小升序
    """
    files_with_size = [(f, get_file_size(f)) for f in files]
    files_with_size.sort(key=lambda x: x[1])
    return files_with_size[:n]


def get_newest_files(files: List[str], n: int = 10) -> List[tuple]:
    """
    获取最新修改的N个文件

    Returns:
        [(文件路径, 修改时间), ...]
    """
    files_with_time = [(f, get_modified_time(f)) for f in files]
    files_with_time.sort(key=lambda x: x[1] or datetime.min, reverse=True)
    return files_with_time[:n]


def get_oldest_files(files: List[str], n: int = 10) -> List[tuple]:
    """
    获取最旧修改的N个文件

    Returns:
        [(文件路径, 修改时间), ...]
    """
    files_with_time = [(f, get_modified_time(f)) for f in files]
    files_with_time.sort(key=lambda x: x[1] or datetime.max)
    return files_with_time[:n]


# ===== 条件过滤 =====

def filter_by_condition(files: List[str], condition: Callable[[str], bool]) -> List[str]:
    """
    按自定义条件过滤

    Args:
        files: 文件路径列表
        condition: 条件函数，接收文件路径，返回bool

    Returns:
        符合条件的文件列表
    """
    return [f for f in files if condition(f)]


def reject_by_condition(files: List[str], condition: Callable[[str], bool]) -> List[str]:
    """
    按自定义条件排除

    Args:
        files: 文件路径列表
        condition: 条件函数，接收文件路径，返回bool

    Returns:
        不符合条件（即被排除）的文件列表
    """
    return [f for f in files if not condition(f)]


# ===== 临时文件检测 =====

TEMP_PATTERNS = [
    "tmp", "temp", "bak", "backup", "old", "cache",
    "~", ".swp", ".swo", ".log", "thumbs.db", "desktop.ini",
    ".ds_store", ".icloud",
]

TEMP_EXTENSIONS = [
    "tmp", "temp", "bak", "cache", "log", "swp", "swo",
]


def is_temp_file(file_path: str) -> bool:
    """
    判断是否为临时文件

    Args:
        file_path: 文件路径

    Returns:
        是否为临时文件
    """
    name = Path(file_path).name.lower()

    # 检查文件名模式
    for pattern in TEMP_PATTERNS:
        if pattern in name:
            return True

    # 检查扩展名
    ext = get_extension(file_path).lower()
    if ext in TEMP_EXTENSIONS:
        return True

    return False


def filter_temp_files(files: List[str]) -> List[str]:
    """过滤出临时文件"""
    return [f for f in files if is_temp_file(f)]


def filter_non_temp_files(files: List[str]) -> List[str]:
    """过滤掉临时文件"""
    return [f for f in files if not is_temp_file(f)]


# ===== 空文件检测 =====

def is_empty_file(file_path: str) -> bool:
    """判断是否为空文件"""
    return get_file_size(file_path) == 0


def filter_empty_files(files: List[str]) -> List[str]:
    """过滤出空文件"""
    return [f for f in files if is_empty_file(f)]


def filter_non_empty_files(files: List[str]) -> List[str]:
    """过滤掉空文件"""
    return [f for f in files if not is_empty_file(f)]


# ===== 复合过滤 =====

def compose_filters(*filters) -> Callable[[List[str]], List[str]]:
    """
    组合多个过滤函数

    Usage:
        combined = compose_filters(
            filter_by_extension,
            filter_by_size,
            filter_by_name_contains
        )
        result = combined(files, ["pdf"], min_mb=1)
    """
    def combined(files: List[str]) -> List[str]:
        result = list(files)
        for f in filters:
            result = f(result)
        return result
    return combined


# ===== 便捷函数 =====

def get_files_by_type(directory: str, file_type: str, recursive: bool = True) -> List[str]:
    """
    获取指定类型的文件

    Args:
        directory: 目录路径
        file_type: 文件类型 (image/video/audio/document/code等)
        recursive: 是否递归

    Returns:
        文件路径列表
    """
    from file_atomic_ops import get_files

    type_extensions = {
        "image": ["jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "ico", "tiff"],
        "video": ["mp4", "avi", "mkv", "mov", "wmv", "flv", "webm", "m4v"],
        "audio": ["mp3", "wav", "flac", "aac", "ogg", "wma", "m4a"],
        "document": ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "rtf"],
        "code": ["py", "js", "java", "cpp", "c", "h", "cs", "go", "rs", "php", "rb", "swift", "kt", "ts"],
        "archive": ["zip", "rar", "7z", "tar", "gz", "bz2", "xz"],
        "executable": ["exe", "msi", "dmg", "app", "apk", "deb", "rpm"],
    }

    extensions = type_extensions.get(file_type.lower(), [])

    files = get_files(directory, recursive)
    return filter_by_extension(files, extensions)


def find_files(directory: str, name_contains: str = None,
               extension: str = None, recursive: bool = True) -> List[str]:
    """
    综合搜索文件

    Args:
        directory: 目录路径
        name_contains: 文件名包含的关键词
        extension: 扩展名
        recursive: 是否递归

    Returns:
        符合条件的文件列表
    """
    from file_atomic_ops import get_files

    files = get_files(directory, recursive)

    if extension:
        files = filter_by_extension(files, extension)

    if name_contains:
        files = filter_by_name_contains(files, name_contains)

    return files
