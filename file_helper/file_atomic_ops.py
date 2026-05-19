"""
File Atomic Operations - 最小粒度的文件操作原子函数

每个函数只做一件事，专注于基础的文件系统操作。
这些原子函数是整个文件管理系统的基石。
"""

import os
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Union


# ===== 文件系统基础查询 =====

def get_files(path: str, recursive: bool = False) -> list:
    """
    获取目录下所有文件（不包括目录）

    Args:
        path: 目标路径（可以是文件或目录）
        recursive: 是否递归扫描子目录

    Returns:
        文件绝对路径列表
    """
    path = Path(path)
    if not path.exists():
        return []

    # 如果是文件，直接返回
    if path.is_file():
        return [str(path)]

    # 如果是目录，遍历内容
    if recursive:
        return [str(f) for f in path.rglob("*") if f.is_file()]
    else:
        return [str(f) for f in path.iterdir() if f.is_file()]


def get_dirs(path: str, recursive: bool = False) -> list:
    """
    获取目录下所有子目录

    Args:
        path: 目标路径
        recursive: 是否递归扫描

    Returns:
        目录绝对路径列表
    """
    path = Path(path)
    if not path.exists():
        return []

    if recursive:
        return [str(d) for d in path.rglob("*") if d.is_dir()]
    else:
        return [str(d) for d in path.iterdir() if d.is_dir()]


def exists(path: str) -> bool:
    """检查路径是否存在"""
    return Path(path).exists()


def is_file(path: str) -> bool:
    """检查是否为文件"""
    return Path(path).is_file()


def is_dir(path: str) -> bool:
    """检查是否为目录"""
    return Path(path).is_dir()


# ===== 文件信息获取 =====

def get_file_info(path: str) -> dict:
    """
    获取单个文件详细信息

    Returns:
        {
            "path": str,           # 文件完整路径
            "name": str,           # 文件名
            "extension": str,      # 扩展名（不含点）
            "size": int,           # 文件大小（字节）
            "size_mb": float,      # 文件大小（MB）
            "created": datetime,  # 创建时间
            "modified": datetime,  # 修改时间
            "is_file": bool,      # 是否为文件
            "is_dir": bool,        # 是否为目录
        }
    """
    path = Path(path)
    if not path.exists():
        return {}

    stat = path.stat()
    return {
        "path": str(path.absolute()),
        "name": path.name,
        "stem": path.stem,
        "extension": path.suffix.lstrip(".") if path.suffix else "",
        "size": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "created": datetime.fromtimestamp(stat.st_ctime),
        "modified": datetime.fromtimestamp(stat.st_mtime),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
    }


def get_file_size(path: str) -> int:
    """获取文件大小（字节）"""
    return Path(path).stat().st_size if Path(path).exists() else 0


def get_file_size_mb(path: str) -> float:
    """获取文件大小（MB）"""
    return round(get_file_size(path) / (1024 * 1024), 2)


def get_created_time(path: str) -> Optional[datetime]:
    """获取文件创建时间"""
    if not Path(path).exists():
        return None
    return datetime.fromtimestamp(Path(path).stat().st_ctime)


def get_modified_time(path: str) -> Optional[datetime]:
    """获取文件修改时间"""
    if not Path(path).exists():
        return None
    return datetime.fromtimestamp(Path(path).stat().st_mtime)


def get_extension(path: str) -> str:
    """获取文件扩展名（不含点）"""
    ext = Path(path).suffix
    return ext.lstrip(".") if ext else ""


def get_file_name(path: str) -> str:
    """获取文件名（不含扩展名）"""
    return Path(path).stem


def get_file_hash(path: str, algorithm: str = "md5") -> str:
    """
    计算文件哈希值

    Args:
        path: 文件路径
        algorithm: 哈希算法 (md5/sha1/sha256)

    Returns:
        哈希值字符串
    """
    if not Path(path).is_file():
        return ""

    hash_func = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()


# ===== 目录操作 =====

def create_dir(path: str) -> bool:
    """
    创建目录

    Args:
        path: 目录路径

    Returns:
        是否创建成功
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


def delete_dir(path: str, recursive: bool = False) -> bool:
    """
    删除目录

    Args:
        path: 目录路径
        recursive: 是否递归删除（否则只删除空目录）

    Returns:
        是否删除成功
    """
    try:
        path = Path(path)
        if not path.exists():
            return True

        if recursive:
            shutil.rmtree(path)
        else:
            path.rmdir()
        return True
    except Exception:
        return False


def is_empty_dir(path: str) -> bool:
    """检查目录是否为空"""
    path = Path(path)
    if not path.exists() or not path.is_dir():
        return False
    return not any(path.iterdir())


def get_dir_size(path: str) -> int:
    """
    获取目录总大小（字节）

    Args:
        path: 目录路径

    Returns:
        目录大小（字节）
    """
    total = 0
    for entry in Path(path).rglob("*"):
        if entry.is_file():
            total += entry.stat().st_size
    return total


def get_dir_size_mb(path: str) -> float:
    """获取目录总大小（MB）"""
    return round(get_dir_size(path) / (1024 * 1024), 2)


def get_dir_file_count(path: str, recursive: bool = True) -> int:
    """获取目录下的文件数量"""
    path = Path(path)
    if not path.exists():
        return 0

    if recursive:
        return sum(1 for f in path.rglob("*") if f.is_file())
    else:
        return sum(1 for f in path.iterdir() if f.is_file())


def get_dir_dir_count(path: str, recursive: bool = False) -> int:
    """获取目录下的子目录数量"""
    path = Path(path)
    if not path.exists():
        return 0

    if recursive:
        return sum(1 for d in path.rglob("*") if d.is_dir() and d != path)
    else:
        return sum(1 for d in path.iterdir() if d.is_dir())


def copy_dir(src: str, dst: str) -> bool:
    """
    复制整个目录

    Args:
        src: 源目录
        dst: 目标目录

    Returns:
        是否复制成功
    """
    try:
        shutil.copytree(src, dst, dirs_exist_ok=True)
        return True
    except Exception:
        return False


def move_dir(src: str, dst: str) -> bool:
    """
    移动整个目录

    Args:
        src: 源目录
        dst: 目标目录

    Returns:
        是否移动成功
    """
    try:
        shutil.move(src, dst)
        return True
    except Exception:
        return False


# ===== 单文件操作 =====

def move_file(src: str, dst: str) -> bool:
    """
    移动单个文件

    Args:
        src: 源文件路径
        dst: 目标路径（可以是文件或目录）

    Returns:
        是否移动成功
    """
    try:
        src_path = Path(src)
        dst_path = Path(dst)

        # 如果目标是目录，保持原文件名
        if dst_path.is_dir():
            dst_path = dst_path / src_path.name

        # 确保目标目录存在
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(src_path), str(dst_path))
        return True
    except Exception:
        return False


def copy_file(src: str, dst: str) -> bool:
    """
    复制单个文件

    Args:
        src: 源文件路径
        dst: 目标路径（可以是文件或目录）

    Returns:
        是否复制成功
    """
    try:
        src_path = Path(src)
        dst_path = Path(dst)

        # 如果目标是目录，保持原文件名
        if dst_path.is_dir():
            dst_path = dst_path / src_path.name

        # 确保目标目录存在
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(str(src_path), str(dst_path))
        return True
    except Exception:
        return False


def delete_file(path: str, to_trash: bool = True) -> bool:
    """
    删除单个文件

    Args:
        path: 文件路径
        to_trash: 是否移至回收站（True）或直接删除（False）

    Returns:
        是否删除成功
    """
    try:
        path = Path(path)
        if not path.exists():
            return True

        if to_trash:
            # 移至回收站
            trash_path = Path.home() / ".trash"
            trash_path.mkdir(exist_ok=True)

            # 如果文件名冲突，加上时间戳
            dst = trash_path / path.name
            if dst.exists():
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dst = trash_path / f"{path.stem}_{timestamp}{path.suffix}"

            shutil.move(str(path), str(dst))
        else:
            path.unlink()

        return True
    except Exception:
        return False


def rename_file(path: str, new_name: str) -> bool:
    """
    重命名文件

    Args:
        path: 原文件路径
        new_name: 新文件名（不包括路径）

    Returns:
        是否重命名成功
    """
    try:
        path = Path(path)
        if not path.exists():
            return False

        new_path = path.parent / new_name
        path.rename(new_path)
        return True
    except Exception:
        return False


def create_file(path: str, content: str = "") -> bool:
    """
    创建文件

    Args:
        path: 文件路径
        content: 文件初始内容

    Returns:
        是否创建成功
    """
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True
    except Exception:
        return False


def read_file(path: str, encoding: str = "utf-8") -> str:
    """
    读取文件内容

    Args:
        path: 文件路径
        encoding: 文件编码

    Returns:
        文件内容，读取失败返回空字符串
    """
    try:
        return Path(path).read_text(encoding=encoding)
    except Exception:
        return ""


def write_file(path: str, content: str, encoding: str = "utf-8") -> bool:
    """
    写入文件内容

    Args:
        path: 文件路径
        content: 文件内容
        encoding: 编码

    Returns:
        是否写入成功
    """
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
        return True
    except Exception:
        return False


def touch_file(path: str) -> bool:
    """
    更新文件访问/修改时间为当前时间（类似 Linux touch）

    Args:
        path: 文件路径

    Returns:
        是否成功
    """
    try:
        Path(path).touch()
        return True
    except Exception:
        return False


# ===== 批量操作辅助 =====

def ensure_dir(path: str) -> bool:
    """确保目录存在，不存在则创建"""
    return create_dir(path)


def safe_move(src: str, dst: str, overwrite: bool = False) -> bool:
    """
    安全移动文件（可控制是否覆盖）

    Args:
        src: 源文件
        dst: 目标路径
        overwrite: 是否覆盖已存在的文件

    Returns:
        是否移动成功
    """
    dst_path = Path(dst)
    if dst_path.exists() and not overwrite:
        return False
    return move_file(src, dst)


def safe_copy(src: str, dst: str, overwrite: bool = False) -> bool:
    """
    安全复制文件（可控制是否覆盖）

    Args:
        src: 源文件
        dst: 目标路径
        overwrite: 是否覆盖已存在的文件

    Returns:
        是否复制成功
    """
    dst_path = Path(dst)
    if dst_path.exists() and not overwrite:
        return False
    return copy_file(src, dst)


# ===== 路径操作辅助 =====

def join_path(*parts) -> str:
    """拼接路径"""
    return str(Path(*parts))


def get_parent_dir(path: str) -> str:
    """获取父目录"""
    return str(Path(path).parent)


def normalize_path(path: str) -> str:
    """规范化路径"""
    return str(Path(path).resolve())


def get_relative_path(path: str, base: str) -> str:
    """获取相对路径"""
    try:
        return str(Path(path).relative_to(base))
    except ValueError:
        return str(Path(path))


def expand_path(path: str) -> str:
    """展开路径（处理 ~ 和环境变量）"""
    return str(Path(path).expanduser().resolve())


def list_root_dirs() -> list:
    """列出系统根目录"""
    return [str(p) for p in Path("/").iterdir()] if os.name != "nt" else [f"{d}:" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if Path(f"{d}:").exists()]


def get_home_dir() -> str:
    """获取用户主目录"""
    return str(Path.home())


def get_desktop() -> str:
    """获取桌面路径"""
    home = Path.home()
    desktop = home / "Desktop"
    if desktop.exists():
        return str(desktop)
    # Windows 可能使用 "桌面"
    desktop_cn = home / "桌面"
    if desktop_cn.exists():
        return str(desktop_cn)
    return str(home)


def get_downloads() -> str:
    """获取下载目录"""
    home = Path.home()
    downloads = home / "Downloads"
    if downloads.exists():
        return str(downloads)
    return str(home)


def get_documents() -> str:
    """获取文档目录"""
    home = Path.home()
    docs = home / "Documents"
    if docs.exists():
        return str(docs)
    # Windows 可能使用 "文档"
    docs_cn = home / "Documents"
    if docs_cn.exists():
        return str(docs_cn)
    return str(home)
