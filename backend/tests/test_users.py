"""
用户管理模块测试 — 覆盖用户 CRUD、权限控制和多租户隔离。

测试路径:
  GET    /api/v1/users/me    - 获取当前用户信息
  GET    /api/v1/users/      - 用户列表
  POST   /api/v1/users/      - 创建用户
  PUT    /api/v1/users/{id}  - 更新用户
  DELETE /api/v1/users/{id}  - 删除用户
"""
import pytest
from fastapi import status


class TestGetMe:
    """当前用户信息测试。"""

    def test_get_me_requires_auth(self, client):
        """未认证访问 /me 应返回 401。"""
        response = client.get("/api/v1/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_me_success(self, client, admin_auth_headers, test_user):
        """认证用户应能获取自己的信息。"""
        response = client.get("/api/v1/users/me", headers=admin_auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"


class TestListUsers:
    """用户列表测试。"""

    def test_list_users_requires_auth(self, client):
        """未认证访问用户列表应返回 401。"""
        response = client.get("/api/v1/users/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_users_success(self, client, admin_auth_headers, test_user):
        """管理员应能查看用户列表。"""
        response = client.get("/api/v1/users/", headers=admin_auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(u["username"] == "admin" for u in data)

    def test_list_users_pagination(self, client, admin_auth_headers, test_user):
        """用户列表分页。"""
        response = client.get(
            "/api/v1/users/?skip=0&limit=1",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) <= 1


class TestCreateUser:
    """创建用户测试。"""

    def test_create_user_requires_admin(self, client, operator_auth_headers):
        """非管理员创建用户应返回 403。"""
        response = client.post(
            "/api/v1/users/",
            json={
                "username": "newuser",
                "password": "NewPass123!",
                "role": "operator",
            },
            headers=operator_auth_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_user_success(self, client, admin_auth_headers, test_org):
        """管理员创建用户应成功。"""
        response = client.post(
            "/api/v1/users/",
            json={
                "username": "newuser",
                "password": "NewPass123!",
                "email": "new@test.com",
                "real_name": "新用户",
                "role": "operator",
                "org_id": test_org.id,
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == "newuser"
        assert data["role"] == "operator"
        assert "password" not in data
        assert "hashed_password" not in data

    def test_create_user_duplicate_username(self, client, admin_auth_headers, test_user):
        """重复用户名应返回 400。"""
        response = client.post(
            "/api/v1/users/",
            json={
                "username": "admin",
                "password": "AnyPass123!",
                "role": "operator",
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_user_missing_required_fields(self, client, admin_auth_headers):
        """缺少必填字段应返回 422。"""
        response = client.post(
            "/api/v1/users/",
            json={"username": "incomplete"},
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
