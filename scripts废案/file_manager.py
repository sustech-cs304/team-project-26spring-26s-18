import shutil
from pathlib import Path

def rename_and_move_file(current_path: Path | str, new_name: str, target_directory: Path | str = None) -> Path:
    """
    重命名并移动文件。
    如果指定了 target_directory，则移动到目标目录；
    否则仅在当前目录重命名。
    返回新的文件路径。
    """
    current_path = Path(current_path)
    
    if not current_path.exists():
        raise FileNotFoundError(f"文件未找到: {current_path}")

    if target_directory:
        target_directory = Path(target_directory)
        target_directory.mkdir(parents=True, exist_ok=True)
        new_path = target_directory / new_name
    else:
        new_path = current_path.parent / new_name

    shutil.move(str(current_path), str(new_path))
    return new_path