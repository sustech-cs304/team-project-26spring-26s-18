#!/usr/bin/env python3
"""
后端部署脚本 - 从 GitHub Actions 下载的 artifact 部署后端

使用方法:
1. 从 GitHub Actions 下载 backend-runtime.zip
2. 将下载的文件放到本脚本同级目录
3. 配置必要的环境变量（见下方说明）
4. 运行本脚本

必要的环境变量:
  - OSS_ACCESS_KEY_ID      阿里云 OSS Access Key ID
  - OSS_ACCESS_KEY_SECRET  阿里云 OSS Access Key Secret
  - DASHSCOPE_API_KEY      百炼大模型 API Key（或其他 AI 密钥）

可选的环境变量:
  - BOCHA_API_KEY          博查搜索 API Key
  - MYSQL_HOST             MySQL 主机地址
  - MYSQL_PORT             MySQL 端口
  - MYSQL_USER             MySQL 用户名
  - MYSQL_PASSWORD         MySQL 密码
  - MYSQL_DB               MySQL 数据库名
  - REDIS_HOST             Redis 主机地址
  - REDIS_PORT             Redis 端口

目录结构示例:
  deploy/
    deploy_backend.py      <- 本脚本
    backend-runtime.zip    <- 从 GitHub 下载的后端产物
"""

import os
import zipfile
import tarfile
import shutil
import subprocess
import sys
from pathlib import Path

DEPLOY_DIR = Path("./deploy/backend")
TEMP_DIR = Path("./deploy/backend_temp")

REQUIRED_ENV_VARS = [
    ("OSS_ACCESS_KEY_ID", "阿里云 OSS Access Key ID"),
    ("OSS_ACCESS_KEY_SECRET", "阿里云 OSS Access Key Secret"),
]

OPTIONAL_ENV_VARS = [
    ("DASHSCOPE_API_KEY", "百炼大模型 API Key"),
    ("BOCHA_API_KEY", "博查搜索 API Key"),
    ("MYSQL_HOST", "MySQL 主机"),
    ("MYSQL_PORT", "MySQL 端口"),
    ("MYSQL_USER", "MySQL 用户名"),
    ("MYSQL_PASSWORD", "MySQL 密码"),
    ("MYSQL_DB", "MySQL 数据库"),
    ("REDIS_HOST", "Redis 主机"),
    ("REDIS_PORT", "Redis 端口"),
]


def find_backend_artifact():
    """查找后端 artifact"""
    for f in Path(".").glob("*backend*.zip"):
        return f
    for f in Path(".").glob("*backend*.tar.gz"):
        return f
    return None


def extract_backend(artifact_path):
    """解压后端产物"""
    if DEPLOY_DIR.exists():
        shutil.rmtree(DEPLOY_DIR)
    DEPLOY_DIR.mkdir(parents=True)

    artifact_path = Path(artifact_path)

    if artifact_path.suffix == '.zip':
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR)
        TEMP_DIR.mkdir()

        with zipfile.ZipFile(artifact_path, 'r') as zip_ref:
            zip_ref.extractall(TEMP_DIR)

        # 查找 tar.gz
        tar_files = list(TEMP_DIR.glob("**/*.tar.gz"))
        if tar_files:
            print(f"  找到 tar.gz: {tar_files[0].name}")
            with tarfile.open(tar_files[0], 'r:gz') as tar_ref:
                tar_ref.extractall(DEPLOY_DIR)
        else:
            for item in TEMP_DIR.iterdir():
                shutil.move(str(item), DEPLOY_DIR / item.name)

        shutil.rmtree(TEMP_DIR)
    else:
        with tarfile.open(artifact_path, 'r:gz') as tar_ref:
            tar_ref.extractall(DEPLOY_DIR)

    # 找到实际代码目录（python_demo）
    actual_dir = find_code_dir()
    print(f"  解压完成，包含:")
    for item in DEPLOY_DIR.iterdir():
        if item.is_dir():
            print(f"    - {item.name}/")
    print(f"  主代码目录: {actual_dir}")
    return actual_dir


def find_code_dir():
    """找到包含 main.py 的代码目录"""
    # 直接在部署目录下查找 python_demo
    python_demo_dir = DEPLOY_DIR / "python_demo"
    if python_demo_dir.exists():
        for pattern in ["main.py", "app.py"]:
            if (python_demo_dir / pattern).exists():
                return python_demo_dir
        return python_demo_dir

    # 备用：递归查找
    for pattern in ["main.py", "app.py"]:
        if (DEPLOY_DIR / pattern).exists():
            return DEPLOY_DIR

    for subdir in DEPLOY_DIR.iterdir():
        if subdir.is_dir() and not subdir.name.startswith('.'):
            for pattern in ["main.py", "app.py"]:
                if (subdir / pattern).exists():
                    return subdir
            if subdir.name in ["python_demo", "backend", "app", "src"]:
                return subdir

    return DEPLOY_DIR


def check_environment():
    """检查环境变量配置"""
    print("\n检查环境变量...")

    missing = []
    for var, desc in REQUIRED_ENV_VARS:
        value = os.environ.get(var, "")
        if value:
            print(f"  ✓ {var}: {'*' * 8}...{value[-4:]}")
        else:
            print(f"  ✗ {var}: 未设置 ({desc})")
            missing.append(var)

    print("\n可选环境变量:")
    for var, desc in OPTIONAL_ENV_VARS:
        value = os.environ.get(var, "")
        if value:
            print(f"  ✓ {var}: 已设置")
        else:
            print(f"  - {var}: 未设置 ({desc})")

    return missing


def install_dependencies(code_dir):
    """安装依赖（优先使用 environment.yml）"""
    env_file = code_dir / "environment.yml"
    req_file = code_dir / "requirements.txt"

    # 检查是否使用 conda
    use_conda = False
    try:
        result = subprocess.run(["conda", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  检测到 conda: {result.stdout.strip()}")
            use_conda_input = input("  是否使用 conda 创建环境? (y/n): ").strip().lower()
            use_conda = use_conda_input == 'y'
    except FileNotFoundError:
        pass

    if use_conda:
        env_name = input("  输入 conda 环境名称 (默认: fastApi_env): ").strip() or "fastApi_env"

        # 检查环境是否存在
        result = subprocess.run(["conda", "env", "list"], capture_output=True, text=True)
        if env_name in result.stdout:
            print(f"  环境 {env_name} 已存在")
            if env_file.exists():
                print(f"  使用 environment.yml 更新环境...")
                subprocess.run([
                    "conda", "env", "update", "-n", env_name, "--file", str(env_file), "--prune"
                ], check=True)
            elif req_file.exists():
                print(f"  使用 requirements.txt 更新依赖...")
                subprocess.run([
                    "conda", "run", "-n", env_name, "pip", "install", "-r", str(req_file)
                ], check=True)
        else:
            if env_file.exists():
                print(f"  使用 environment.yml 创建环境: {env_name}")
                subprocess.run([
                    "conda", "env", "create", "-n", env_name, "--file", str(env_file)
                ], check=True)
            elif req_file.exists():
                print(f"  创建新环境: {env_name}")
                subprocess.run([
                    "conda", "create", "-n", env_name, "python=3.11", "-y"
                ], check=True)
                print(f"  安装依赖到 {env_name}...")
                subprocess.run([
                    "conda", "run", "-n", env_name, "pip", "install", "-r", str(req_file)
                ], check=True)
            else:
                print("  警告: 未找到 environment.yml 或 requirements.txt")
                return None

        return env_name
    else:
        if req_file.exists():
            print(f"\n安装依赖: {req_file}")
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", str(req_file)
            ], check=True)
            return None
        else:
            print("\n警告: 未找到 requirements.txt")
            return None


def start_backend(code_dir, conda_env=None):
    """启动后端服务"""
    print("\n" + "="*50)
    print("启动后端服务...")
    print(f"访问地址: http://127.0.0.1:8000")
    print("API 文档: http://127.0.0.1:8000/docs")
    print("按 Ctrl+C 停止")
    print("="*50)

    if conda_env:
        subprocess.run([
            "conda", "run", "-n", conda_env,
            "uvicorn", "main:app", "--reload", "--host", "0.0.0.0"
        ], cwd=code_dir)
    else:
        subprocess.run([
            sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0"
        ], cwd=code_dir)


def main():
    print("="*50)
    print("后端部署脚本")
    print("="*50)

    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # 检查环境变量
    missing = check_environment()
    if missing:
        print(f"\n警告: 以下必要环境变量未设置: {', '.join(missing)}")
        print("请先设置环境变量后再运行")
        print("\nWindows 设置方式:")
        for var in missing:
            print(f"  set {var}=your_value")
        print("\nLinux/Mac 设置方式:")
        for var in missing:
            print(f"  export {var}=your_value")

        cont = input("\n是否继续部署? (y/n): ").strip().lower()
        if cont != 'y':
            sys.exit(1)

    # 查找 artifact
    print("\n[1/3] 查找后端 artifact...")
    artifact = find_backend_artifact()

    if not artifact:
        print("\n错误: 未找到 backend-runtime.zip 或 backend-runtime.tar.gz")
        print("请从 GitHub Actions 下载:")
        print("  仓库 -> Actions -> 选择任一 run -> Artifacts -> backend-runtime")
        sys.exit(1)

    print(f"  找到: {artifact.name}")

    # 解压
    print("\n[2/3] 解压后端产物...")
    code_dir = extract_backend(artifact)

    # 安装依赖
    print("\n[3/3] 安装依赖...")
    conda_env = install_dependencies(code_dir)

    print("\n" + "="*50)
    print("部署完成!")
    print(f"  后端目录: {code_dir}")
    if conda_env:
        print(f"  Conda 环境: {conda_env}")
    print("="*50)

    print("\n启动方式:")
    if conda_env:
        print(f"  1. 激活环境: conda activate {conda_env}")
    print(f"  2. 进入目录: cd {code_dir}")
    print("  3. 启动服务: uvicorn main:app --reload")
    print("  4. 访问地址: http://127.0.0.1:8000")
    print("  5. API文档: http://127.0.0.1:8000/docs")


if __name__ == "__main__":
    main()
