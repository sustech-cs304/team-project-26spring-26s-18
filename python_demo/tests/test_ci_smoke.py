# 确认后端项目结构存在

from pathlib import Path


def test_backend_project_structure_exists():
    root = Path(__file__).resolve().parents[1]

    assert (root / "main.py").exists()
    assert (root / "routers").is_dir()
    assert (root / "crud").is_dir()
    assert (root / "models").is_dir()
    assert (root / "config").is_dir()


def test_scheduler_modules_exist():
    root = Path(__file__).resolve().parents[1]

    assert (root / "routers" / "scheduler.py").exists()
    assert (root / "crud" / "scheduler.py").exists()
    assert (root / "models" / "scheduler.py").exists()


def test_core_api_modules_exist():
    root = Path(__file__).resolve().parents[1]

    assert (root / "routers" / "session.py").exists()
    assert (root / "routers" / "user.py").exists()