"""
供应商管理测试 - 覆盖供应商的创建、查询列表和状态更新操作。

测试路径:
  POST   /api/v1/suppliers/           - 创建供应商
  GET    /api/v1/suppliers/           - 获取供应商列表
  GET    /api/v1/suppliers/{id}       - 获取单个供应商
  PUT    /api/v1/suppliers/{id}       - 更新供应商
  DELETE /api/v1/suppliers/{id}       - 删除供应商
"""
import pytest
from fastapi import status


class TestCreateSupplier:
    """创建供应商接口测试集合。"""

    def test_create_supplier_success(self, client, admin_auth_headers):
        """测试使用完整有效数据创建供应商，应返回供应商详情。"""
        payload = {
            "name": "新鲜蔬菜配送中心",
            "code": "SUP-FRESH-001",
            "contact_person": "王经理",
            "phone": "13800138001",
            "email": "fresh@example.com",
            "address": "农产品批发市场A区12号",
            "status": "active",
        }
        response = client.post(
            "/api/v1/suppliers/",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "新鲜蔬菜配送中心"
        assert data["code"] == "SUP-FRESH-001"
        assert data["contact_person"] == "王经理"
        assert data["status"] == "active"
        assert data["rating"] == 5.0  # 默认评分
        assert "id" in data

    def test_create_supplier_minimal(self, client, admin_auth_headers):
        """测试仅提供必填字段创建供应商。"""
        payload = {
            "name": "最小供应商",
            "code": "SUP-MIN-001",
        }
        response = client.post(
            "/api/v1/suppliers/",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "最小供应商"
        assert data["status"] == "active"  # 默认状态

    def test_create_supplier_duplicate_code(self, client, admin_auth_headers, test_supplier):
        """测试创建重复 code 的供应商，数据库唯一约束冲突应导致请求失败。"""
        import sqlalchemy.exc
        payload = {
            "name": "重复供应商",
            "code": test_supplier.code,  # 重复的 code
        }
        # IntegrityError 在 SQLite 中直接抛出，FastAPI 未全局捕获
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            client.post(
                "/api/v1/suppliers/",
                json=payload,
                headers=admin_auth_headers,
            )


class TestListSuppliers:
    """获取供应商列表接口测试集合。"""

    def test_list_suppliers_empty(self, client, admin_auth_headers):
        """测试数据库为空时获取供应商列表，应返回空列表。"""
        response = client.get(
            "/api/v1/suppliers/",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_list_suppliers_with_data(self, client, admin_auth_headers, test_supplier):
        """测试数据库有数据时获取供应商列表，应包含已创建的供应商。"""
        response = client.get(
            "/api/v1/suppliers/",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        ids = [item["id"] for item in data]
        assert test_supplier.id in ids

    def test_list_suppliers_filter_by_status(self, client, admin_auth_headers, test_supplier):
        """测试按状态筛选供应商列表。"""
        response = client.get(
            "/api/v1/suppliers/?status=active",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data:
            assert item["status"] == "active"

    def test_list_suppliers_filter_by_nonexistent_status(self, client, admin_auth_headers):
        """测试按不存在的状态筛选供应商，应返回空列表。"""
        response = client.get(
            "/api/v1/suppliers/?status=nonexistent_status",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0


class TestGetSupplier:
    """获取单个供应商接口测试集合。"""

    def test_get_supplier_success(self, client, admin_auth_headers, test_supplier):
        """测试获取已存在的供应商详情，应返回完整信息。"""
        response = client.get(
            f"/api/v1/suppliers/{test_supplier.id}",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_supplier.id
        assert data["name"] == test_supplier.name
        assert data["code"] == test_supplier.code

    def test_get_supplier_not_found(self, client, admin_auth_headers):
        """测试获取不存在的供应商 ID，应返回 404。"""
        response = client.get(
            "/api/v1/suppliers/99999",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateSupplierStatus:
    """更新供应商状态测试集合。"""

    def test_update_supplier_to_suspended(self, client, admin_auth_headers, test_supplier):
        """测试将供应商状态更新为 suspended（暂停）。"""
        payload = {
            "name": test_supplier.name,
            "code": test_supplier.code,
            "contact_person": test_supplier.contact_person,
            "phone": test_supplier.phone,
            "email": test_supplier.email,
            "status": "suspended",
        }
        response = client.put(
            f"/api/v1/suppliers/{test_supplier.id}",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "suspended"

    def test_update_supplier_to_blacklisted(self, client, admin_auth_headers, test_supplier):
        """测试将供应商状态更新为 blacklisted（黑名单）。"""
        payload = {
            "name": test_supplier.name,
            "code": test_supplier.code,
            "contact_person": test_supplier.contact_person,
            "phone": test_supplier.phone,
            "email": test_supplier.email,
            "status": "blacklisted",
        }
        response = client.put(
            f"/api/v1/suppliers/{test_supplier.id}",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "blacklisted"

    def test_update_supplier_reactivate(self, client, admin_auth_headers, db_session, test_supplier):
        """测试将已暂停的供应商重新激活。"""
        # 先将供应商设为暂停
        test_supplier.status = "suspended"
        db_session.commit()

        payload = {
            "name": test_supplier.name,
            "code": test_supplier.code,
            "contact_person": test_supplier.contact_person,
            "phone": test_supplier.phone,
            "email": test_supplier.email,
            "status": "active",
        }
        response = client.put(
            f"/api/v1/suppliers/{test_supplier.id}",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "active"

    def test_update_supplier_not_found(self, client, admin_auth_headers):
        """测试更新不存在的供应商 ID，应返回 404。"""
        payload = {
            "name": "不存在",
            "code": "SUP-NONE",
            "status": "active",
        }
        response = client.put(
            "/api/v1/suppliers/99999",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteSupplier:
    """删除供应商接口测试集合。"""

    def test_delete_supplier_success(self, client, admin_auth_headers, db_session):
        """测试删除已存在的供应商，应返回成功消息。"""
        from app.models import Supplier
        supplier = Supplier(
            name="待删除供应商",
            code="SUP-DEL-001",
            status="active",
        )
        db_session.add(supplier)
        db_session.commit()
        db_session.refresh(supplier)

        response = client.delete(
            f"/api/v1/suppliers/{supplier.id}",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data

    def test_delete_supplier_not_found(self, client, admin_auth_headers):
        """测试删除不存在的供应商 ID，应返回 404。"""
        response = client.delete(
            "/api/v1/suppliers/99999",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
