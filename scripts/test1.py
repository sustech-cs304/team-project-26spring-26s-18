import os
from pathlib import Path
import sys

# 动态调整 Python 搜索路径，以便能找到 scripts 目录下的模块
sys.path.append(str(Path(__file__).parent))

from workflows import process_single_homework

def ensure_test_environment(base_dir: Path):
    """确保测试目录存在"""
    print("--- 正在检查 User Story 1 的测试环境 ---")
    base_dir.mkdir(parents=True, exist_ok=True)
    print(f"确保测试目录存在: {base_dir}")

if __name__ == "__main__":
    # 测试工作区位于 scripts 文件夹内
    test_workspace = Path(__file__).parent / "test_workspace"
    
    # 1. 准备测试目录
    ensure_test_environment(test_workspace)
    
    # 定义需要处理的文件路径
    homework_to_process = test_workspace / "111.docx"

    # 检查 User Story 1 的文件是否存在
    if not homework_to_process.exists():
        print(f"\n错误: 未找到 User Story 1 的测试文件。")
        print(f"请在以下路径手动创建一个名为 111.docx 的Word文档，并写入内容（如 'CS303 Lab1'）: \n{homework_to_process}")
        sys.exit(1) # 退出脚本
    
    print("测试文件已找到，准备开始测试...")
    print("-" * 20 + "\n")

    # 2. 测试 User Story 1: 处理单个作业
    print(">>> 开始测试 User Story 1: 自动重命名并转换 PDF...")
    process_single_homework(str(homework_to_process))
    print(">>> User Story 1 测试完成!\n")