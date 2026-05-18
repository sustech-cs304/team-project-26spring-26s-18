import sys
import os

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


def test_result_util():
    """测试 Result 工具类"""
    from utils.Result import Result
    
    # 测试成功结果
    success_result = Result.success("test data")
    assert success_result.code == 1
    assert success_result.message == "success"
    assert success_result.data == "test data"
    
    # 测试失败结果（使用正确的方法名 error）
    error_result = Result.error("error message")
    assert error_result.code == 0
    assert error_result.message == "error message"
    assert error_result.data is None


def test_jwt_util():
    """测试 JWT 工具类"""
    from utils.jwt_util import JWTUtil
    
    # 生成 token
    token = JWTUtil.generate_token(user_id=123)
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0
    
    # 解析 token
    user_id = JWTUtil.parse_token(token)
    assert user_id is not None
    assert user_id == 123
    
    # 测试无效 token
    invalid_user_id = JWTUtil.parse_token("invalid_token")
    assert invalid_user_id is None


def test_mail_util_exists():
    """测试邮件工具模块存在"""
    import utils.mail_util
    assert utils.mail_util is not None
    assert hasattr(utils.mail_util, 'MailUtil')


def test_oss_util_exists():
    """测试 OSS 工具模块存在"""
    import utils.oss_util
    assert utils.oss_util is not None


def test_ai_util_exists():
    """测试 AI 工具模块存在"""
    import utils.ai_util
    assert utils.ai_util is not None


def test_pdf_util_exists():
    """测试 PDF 工具模块存在"""
    import utils.pdf_util
    assert utils.pdf_util is not None
