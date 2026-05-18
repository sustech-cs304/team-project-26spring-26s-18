import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_user_register():
    """测试用户注册接口"""
    response = client.post(
        "/user/register",
        json={
            "email": "test@example.com",
            "password": "test123456",
            "username": "testuser"
        }
    )
    # 检查响应状态码（成功或用户已存在）
    assert response.status_code in [200, 400]


def test_user_login():
    """测试用户登录接口"""
    response = client.post(
        "/user/login",
        json={
            "email": "test@example.com",
            "password": "test123456"
        }
    )
    # 检查响应状态码（成功或认证失败）
    assert response.status_code in [200, 401]


def test_send_code():
    """测试发送验证码接口"""
    response = client.post(
        "/user/sendCode",
        json={"email": "test@example.com"}
    )
    assert response.status_code == 200


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
