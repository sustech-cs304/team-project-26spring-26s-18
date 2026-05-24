#!/usr/bin/env python3
"""
本地部署脚本 - 手动下载 artifacts 后一键部署

使用方法:
1. 从 GitHub Actions 下载 artifacts:
   - frontend-dist (zip)
   - backend-runtime (tar.gz)
2. 将下载的文件放到本脚本同级目录
3. 运行本脚本

目录结构示例:
  deploy/
    deploy_local.py      <- 本脚本
    frontend-dist.zip    <- 从 GitHub 下载的前端产物
    backend-runtime.tar.gz  <- 从 GitHub 下载的后端产物
"""

import os
import zipfile
import tarfile
import shutil
import subprocess
import sys
from pathlib import Path

# 部署路径配置
DEPLOY_DIR = Path("./deploy")


def find_artifacts():
    """查找当前目录下的 artifacts"""
    artifacts = {}

    # 查找前端 zip
    for f in Path(".").glob("*frontend*.zip"):
        artifacts["frontend"] = f
        break

    # 查找后端 zip（可能直接是 zip 或包含 tar.gz 的 zip）
    for f in Path(".").glob("*backend*.zip"):
        artifacts["backend-zip"] = f
        break

    # 查找后端 tar.gz（直接下载的情况）
    for f in Path(".").glob("*backend*.tar.gz"):
        artifacts["backend"] = f
        break

    return artifacts


def extract_frontend(zip_path, extract_to):
    """解压前端产物"""
    extract_to = Path(extract_to)
    if extract_to.exists():
        shutil.rmtree(extract_to)
    extract_to.mkdir(parents=True)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

    # 处理可能的嵌套目录
    items = list(extract_to.iterdir())
    if len(items) == 1 and items[0].is_dir():
        nested = items[0]
        for item in nested.iterdir():
            shutil.move(str(item), extract_to / item.name)
        nested.rmdir()

    print(f"  前端解压到: {extract_to}")
    return extract_to


def extract_backend_artifact(artifact_path, extract_to):
    """解压后端产物（支持 zip 或 tar.gz）"""
    artifact_path = Path(artifact_path)
    extract_to = Path(extract_to)
    if extract_to.exists():
        shutil.rmtree(extract_to)
    extract_to.mkdir(parents=True)

    if artifact_path.suffix == '.zip':
        # 先解压 zip
        temp_dir = extract_to.parent / "backend_temp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir()

        with zipfile.ZipFile(artifact_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # 从解压目录中找到 tar.gz
        tar_files = list(temp_dir.glob("**/*.tar.gz"))
        if tar_files:
            tar_path = tar_files[0]
            print(f"  找到 tar.gz: {tar_path.name}")
            with tarfile.open(tar_path, 'r:gz') as tar_ref:
                tar_ref.extractall(extract_to)
        else:
            # 没有 tar.gz，直接使用解压后的内容
            for item in temp_dir.iterdir():
                shutil.move(str(item), extract_to / item.name)
        shutil.rmtree(temp_dir)
    else:
        # 直接是 tar.gz
        with tarfile.open(artifact_path, 'r:gz') as tar_ref:
            tar_ref.extractall(extract_to)

    print(f"  后端解压到: {extract_to}")
    return extract_to


def install_backend_deps(deploy_path):
    """安装后端依赖"""
    req_file = deploy_path / "requirements.txt"
    if not req_file.exists():
        # 尝试在子目录中查找
        for subdir in deploy_path.iterdir():
            if subdir.is_dir():
                req_file = subdir / "requirements.txt"
                if req_file.exists():
                    break

    if req_file.exists():
        print(f"\n安装后端依赖: {req_file}")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            check=True
        )
        return req_file.parent
    else:
        print("\n警告: 未找到 requirements.txt")
        return deploy_path


def find_actual_dir(deploy_path):
    """找到实际的代码目录（处理可能的嵌套）"""
    # 如果直接有常见入口文件，就在根目录
    for pattern in ["app.py", "main.py", "application.py", "manage.py"]:
        if (deploy_path / pattern).exists():
            return deploy_path

    # 查找子目录
    for subdir in deploy_path.iterdir():
        if subdir.is_dir() and not subdir.name.startswith('.'):
            for pattern in ["app.py", "main.py", "application.py"]:
                if (subdir / pattern).exists():
                    return subdir
            # 检查是否是 python_demo 或类似目录
            if subdir.name in ["python_demo", "backend", "app", "src"]:
                return subdir

    return deploy_path


def start_frontend(deploy_path):
    """启动前端静态服务器"""
    print("\n" + "="*50)
    print("启动前端服务器...")
    print(f"访问地址: http://localhost:8080")
    print("按 Ctrl+C 停止")
    print("="*50)
    subprocess.run([sys.executable, "-m", "http.server", "8080"], cwd=deploy_path)


def main():
    print("="*50)
    print("本地部署脚本")
    print("="*50)

    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # 1. 查找 artifacts
    print("\n[1/4] 查找 artifacts...")
    artifacts = find_artifacts()

    if not artifacts:
        print("\n错误: 未找到 artifacts 文件")
        print("请确保以下文件在当前目录:")
        print("  - frontend-dist.zip")
        print("  - backend-runtime.zip 或 backend-runtime.tar.gz")
        print("\n从 GitHub Actions 下载:")
        print("  仓库 -> Actions -> 选择任一 run -> Artifacts -> 下载")
        sys.exit(1)

    for name, path in artifacts.items():
        print(f"  找到 {name}: {path.name}")

    # 2. 创建部署目录
    print("\n[2/4] 准备部署目录...")
    if DEPLOY_DIR.exists():
        shutil.rmtree(DEPLOY_DIR)
    DEPLOY_DIR.mkdir()

    # 3. 解压
    print("\n[3/4] 解压 artifacts...")
    frontend_path = extract_frontend(artifacts["frontend"], DEPLOY_DIR / "frontend")

    # 处理后端（可能是 zip 或 tar.gz）
    backend_artifact = artifacts.get("backend") or artifacts.get("backend-zip")
    backend_path = extract_backend_artifact(backend_artifact, DEPLOY_DIR / "backend")

    # 4. 安装依赖
    print("\n[4/4] 安装后端依赖...")
    actual_backend_dir = find_actual_dir(backend_path)
    install_backend_deps(actual_backend_dir)

    # 部署完成
    print("\n" + "="*50)
    print("部署完成!")
    print(f"  前端: {frontend_path}")
    print(f"  后端: {actual_backend_dir}")
    print("="*50)

    # 询问启动选项
    print("\n启动选项:")
    print("  1. 启动前端服务器 (http://localhost:8080)")
    print("  2. 仅显示后端启动命令")
    print("  3. 退出")
    choice = input("\n请选择 (1/2/3): ").strip()

    if choice == "1":
        start_frontend(frontend_path)
    elif choice == "2":
        print("\n后端启动命令:")
        print(f"  cd {actual_backend_dir}")
        print("  # 根据实际框架选择:")
        print("  python app.py")
        print("  # 或")
        print("  python -m flask run")


if __name__ == "__main__":
    main()
