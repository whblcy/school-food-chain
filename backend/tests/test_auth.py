"""
认证模块测试 - 覆盖登录、token 刷新和未授权访问等场景。

测试路径:
  POST /api/v1/auth/login       - 用户登录
  POST /api/v1/auth/refresh     - 刷新 token
"""
import pytest
from fastapi import status


class TestLogin:
    """登录接口测试集合。"""

    def test_login_success(self, client, test_user):
        """测试使用正确的用户名和密码登录成功，返回 access_token 和 refresh_token。"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    def test_login_wrong_password(self, client, test_user):
        """测试使用错误的密码登录，应返回 401 Unauthorized。"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong_password"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data

    def test_login_nonexistent_user(self, client):
        """测试使用不存在的用户名登录，应返回 401 Unauthorized。"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "whatever"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_empty_fields(self, client):
        """测试提交空的用户名和密码，应返回 422 验证错误或 401（取决于框架校验顺序）。"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "", "password": ""},
        )
        # FastAPI 对空字符串仍会尝试匹配用户，可能返回 401
        assert response.status_code in (
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED,
        )


class TestTokenRefresh:
    """Token 刷新接口测试集合。"""

    def test_refresh_token_success(self, client, test_user, admin_refresh_token):
        """测试使用有效的 refresh token 获取新的 access token。"""
        # 后端 /auth/refresh 使用 HTTPBearer，需通过 Authorization 头传递 refresh_token
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {admin_refresh_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self, client):
        """测试使用无效的 refresh token，应返回 401 或 403。"""
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": "Bearer invalid-token-here"},
        )
        # HTTPBearer 解析失败可能返回 401 或 403
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_refresh_token_with_access_token(self, client, admin_token):
        """测试使用 access token（而非 refresh token）尝试刷新，应返回 401。"""
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestProtectedEndpoints:
    """受保护接口的认证校验测试集合。"""

    def test_access_protected_endpoint_without_token(self, client):
        """测试不携带 token 访问受保护的食材列表接口，应返回 401 或 403。"""
        response = client.get("/api/v1/ingredients/")
        # HTTPBearer 在无 token 时返回 403
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_access_protected_endpoint_with_invalid_token(self, client):
        """测试携带无效 token 访问受保护接口，应返回 401 或 403。"""
        response = client.get(
            "/api/v1/ingredients/",
            headers={"Authorization": "Bearer invalid-token-here"},
        )
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_access_protected_endpoint_with_valid_token(self, client, admin_auth_headers):
        """测试携带有效 token 访问受保护接口，应返回 200。"""
        response = client.get(
            "/api/v1/ingredients/",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
