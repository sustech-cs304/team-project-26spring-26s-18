#!/usr/bin/env python3
"""
前端部署脚本 - 从 GitHub Actions 下载的 artifact 部署前端

使用方法:
1. 从 GitHub Actions 下载 frontend-dist.zip
2. 将下载的文件放到本脚本同级目录
3. 运行本脚本

目录结构示例:
  deploy/
    deploy_frontend.py    <- 本脚本
    frontend-dist.zip     <- 从 GitHub 下载的前端产物
"""

import os
import zipfile
import shutil
import subprocess
import sys
from pathlib import Path

DEPLOY_DIR = Path("./deploy/frontend")


def find_frontend_artifact():
    """查找前端 artifact"""
    for f in Path(".").glob("*frontend*.zip"):
        return f
    return None


def extract_frontend(zip_path):
    """解压前端产物"""
    if DEPLOY_DIR.exists():
        shutil.rmtree(DEPLOY_DIR)
    DEPLOY_DIR.mkdir(parents=True)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(DEPLOY_DIR)

    # 处理可能的嵌套目录
    items = list(DEPLOY_DIR.iterdir())
    if len(items) == 1 and items[0].is_dir():
        nested = items[0]
        for item in nested.iterdir():
            shutil.move(str(item), DEPLOY_DIR / item.name)
        nested.rmdir()

    print(f"  解压到: {DEPLOY_DIR}")
    return DEPLOY_DIR


def start_server():
    """启动前端静态服务器"""
    print("\n" + "="*50)
    print("启动前端服务器...")
    print(f"访问地址: http://localhost:8080")
    print("按 Ctrl+C 停止")
    print("="*50)
    subprocess.run([sys.executable, "-m", "http.server", "8080"], cwd=DEPLOY_DIR)


def main():
    print("="*50)
    print("前端部署脚本")
    print("="*50)

    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # 查找 artifact
    print("\n[1/2] 查找前端 artifact...")
    artifact = find_frontend_artifact()

    if not artifact:
        print("\n错误: 未找到 frontend-dist.zip")
        print("请从 GitHub Actions 下载:")
        print("  仓库 -> Actions -> 选择任一 run -> Artifacts -> frontend-dist")
        sys.exit(1)

    print(f"  找到: {artifact.name}")

    # 解压
    print("\n[2/2] 解压前端产物...")
    extract_frontend(artifact)

    print("\n" + "="*50)
    print("部署完成!")
    print(f"  前端目录: {DEPLOY_DIR}")
    print("="*50)

    # 询问是否启动
    print("\n选项:")
    print("  1. 启动前端服务器 (http://localhost:8080)")
    print("  2. 退出")
    choice = input("\n请选择 (1/2): ").strip()

    if choice == "1":
        start_server()


if __name__ == "__main__":
    main()
