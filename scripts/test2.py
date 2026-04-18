import os
from pathlib import Path
import sys

# 动态调整 Python 搜索路径，以便能找到 scripts 目录下的模块
sys.path.append(str(Path(__file__).parent))

from workflows import organize_downloads_folder

def ensure_test_environment(base_dir: Path):
    """确保测试目录和下载子目录存在"""
    print("--- 正在检查 User Story 2 的测试环境 ---")
    downloads_path = base_dir / "downloads"
    downloads_path.mkdir(parents=True, exist_ok=True)
    print(f"确保测试目录存在: {base_dir}")
    print(f"确保下载子目录存在: {downloads_path}")
    return downloads_path

if __name__ == "__main__":
    # 测试工作区位于 scripts 文件夹内
    test_workspace = Path(__file__).parent / "test_workspace"
    
    # 1. 准备测试目录
    downloads_to_organize = ensure_test_environment(test_workspace)

    # 检查 downloads 文件夹是否为空
    if not any(downloads_to_organize.iterdir()):
         print(f"\n提示: 'downloads' 文件夹是空的。")
         print(f"请在以下路径手动添加一些 .docx 或 .pdf 文件来进行测试:\n{downloads_to_organize}")
         sys.exit(0) # 文件夹为空，直接退出
    
    print("测试文件已找到，准备开始测试...")
    print("-" * 20 + "\n")

    # 2. 测试 User Story 2: 自动整理下载文件夹
    print(">>> 开始测试 User Story 2: 自动归类下载文件夹...")
    organize_downloads_folder(str(downloads_to_organize))
    print(">>> User Story 2 测试完成!")