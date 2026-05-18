import sys
import os

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


def test_jwt_util():
    """测试 JWT 工具函数"""
    from utils.jwt_util import create_token, verify_token
    
    # 创建 token
    token = create_token({"user_id": 1, "email": "test@example.com"})
    assert token is not None
    assert isinstance(token, str)
    
    # 验证 token
    payload = verify_token(token)
    assert payload is not None
    assert payload.get("user_id") == 1


def test_result_util():
    """测试 Result 工具类"""
    from utils.Result import Result
    
    # 测试成功结果
    success_result = Result.success("test data")
    assert success_result.code == 1
    assert success_result.message == "success"
    assert success_result.data == "test data"
    
    # 测试失败结果
    fail_result = Result.fail("error message")
    assert fail_result.code == 0
    assert fail_result.message == "error message"
    assert fail_result.data is None


def test_mail_util_exists():
    """测试邮件工具模块存在"""
    import utils.mail_util
    assert utils.mail_util is not None


def test_oss_util_exists():
    """测试 OSS 工具模块存在"""
    import utils.oss_util
    assert utils.oss_util is not None
