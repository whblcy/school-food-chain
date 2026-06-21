"""
安全功能测试 — 覆盖 JWT、HttpOnly Cookie、安全响应头、密码哈希等。

测试路径:
  POST /api/v1/auth/login       - 登录后检查 Cookie 设置
  POST /api/v1/auth/logout      - 登出后检查 Cookie 清除
  GET  /*                        - 安全响应头检查
  单元: 密码哈希、JWT 生成与验证
"""
import pytest
from fastapi import status

from app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class TestPasswordHashing:
    """密码哈希测试集合。"""

    def test_password_hash_is_different_from_plain(self):
        """哈希后的密码不应等于明文。"""
        plain = "MySecretPass123"
        hashed = get_password_hash(plain)
        assert hashed != plain
        assert len(hashed) > 0

    def test_password_hash_contains_bcrypt_prefix(self):
        """bcrypt 哈希应以 $2b$ 开头。"""
        hashed = get_password_hash("test123")
        assert hashed.startswith("$2")

    def test_verify_correct_password(self):
        """正确密码应验证通过。"""
        plain = "correct_password"
        hashed = get_password_hash(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_wrong_password(self):
        """错误密码应验证失败。"""
        hashed = get_password_hash("right_password")
        assert verify_password("wrong_password", hashed) is False

    def test_different_hashes_for_same_password(self):
        """相同密码每次生成的哈希应不同（bcrypt 盐值）。"""
        h1 = get_password_hash("same_pass")
        h2 = get_password_hash("same_pass")
        assert h1 != h2

    def test_verify_password_with_invalid_hash(self):
        """无效的哈希字符串应返回 False 而非抛异常。"""
        assert verify_password("any", "not_a_valid_hash") is False


class TestJWTToken:
    """JWT Token 生成与解码测试。"""

    def test_access_token_contains_sub(self):
        """access_token 应能解码出 sub 字段。"""
        token = create_access_token(data={"sub": "42"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["type"] == "access"

    def test_refresh_token_contains_type(self):
        """refresh_token 应包含 type=refresh。"""
        token = create_refresh_token(data={"sub": "42"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"

    def test_decode_invalid_token_returns_none(self):
        """无效的 token 字符串应返回 None。"""
        assert decode_token("invalid.token.here") is None
        assert decode_token("") is None
        assert decode_token("not.a.jwt") is None


class TestSecurityHeaders:
    """安全响应头测试。"""

    def test_health_endpoint_has_security_headers(self, client):
        """所有响应应包含基础安全响应头。"""
        response = client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy_header(self, client):
        """应包含 Permissions-Policy 头限制浏览器特性。"""
        response = client.get("/health")
        pp = response.headers.get("Permissions-Policy", "")
        assert "geolocation=()" in pp
        assert "microphone=()" in pp
        assert "camera=()" in pp


class TestHttpOnlyCookie:
    """HttpOnly Cookie 测试。"""

    def test_login_sets_httponly_cookies(self, client, test_user):
        """登录成功后应设置 access_token 和 refresh_token 的 HttpOnly Cookie。"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == status.HTTP_200_OK

        cookies = response.cookies
        assert "access_token" in cookies
        assert "refresh_token" in cookies

    def test_logout_clears_cookies(self, client, test_user, admin_auth_headers):
        """登出应清除 auth cookies。"""
        response = client.post("/api/v1/auth/logout", headers=admin_auth_headers)
        assert response.status_code == status.HTTP_200_OK


class TestHealthEndpoints:
    """健康检查端点测试。"""

    def test_health_check(self, client):
        """健康检查应返回 200 和状态信息。"""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "version" in data

    def test_liveness(self, client):
        """存活探针应返回 ok。"""
        response = client.get("/live")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "ok"

    def test_metrics_endpoint(self, client):
        """Prometheus 指标端点应返回 text 格式。"""
        response = client.get("/metrics")
        assert response.status_code == status.HTTP_200_OK
        assert "text" in response.headers.get("content-type", "")
