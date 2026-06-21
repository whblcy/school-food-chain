"""
审计日志模块测试 — 覆盖审计日志查询和权限控制。

测试路径:
  GET /api/v1/audit/   - 审计日志列表查询
"""
import pytest
from fastapi import status

from app.models import AuditLog


class TestAuditList:
    """审计日志查询测试集合。"""

    def test_list_audit_requires_auth(self, client):
        """未认证访问审计日志应返回 401/403。"""
        response = client.get("/api/v1/audit/")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_list_audit_requires_admin(self, client, operator_auth_headers):
        """非管理员访问审计日志应返回 403。"""
        response = client.get("/api/v1/audit/", headers=operator_auth_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_audit_empty(self, client, admin_auth_headers):
        """管理员查询空审计日志应返回空列表。"""
        response = client.get("/api/v1/audit/", headers=admin_auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_list_audit_with_data(self, client, db_session, test_org, test_user, admin_auth_headers):
        """查询有数据的审计日志应返回记录列表。"""
        log = AuditLog(
            user_id=test_user.id,
            action="create",
            target_type="ingredient",
            target_id=1,
            org_id=test_org.id,
            old_value=None,
            new_value={"name": "白菜"},
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )
        db_session.add(log)
        db_session.commit()

        response = client.get("/api/v1/audit/", headers=admin_auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        item = data[0]
        assert item["action"] == "create"
        assert item["target_type"] == "ingredient"
        assert item["ip_address"] == "127.0.0.1"

    def test_list_audit_filter_by_action(self, client, db_session, test_org, test_user, admin_auth_headers):
        """按 action 过滤审计日志。"""
        for action in ("create", "update", "delete"):
            db_session.add(AuditLog(
                user_id=test_user.id, action=action, target_type="test",
                target_id=1, org_id=test_org.id, ip_address="127.0.0.1",
            ))
        db_session.commit()

        response = client.get(
            "/api/v1/audit/?action=update",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["action"] == "update"

    def test_list_audit_pagination(self, client, db_session, test_org, test_user, admin_auth_headers):
        """审计日志分页查询。"""
        for i in range(5):
            db_session.add(AuditLog(
                user_id=test_user.id, action="create", target_type="test",
                target_id=i, org_id=test_org.id, ip_address="127.0.0.1",
            ))
        db_session.commit()

        response = client.get(
            "/api/v1/audit/?skip=2&limit=2",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
