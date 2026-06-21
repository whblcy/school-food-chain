"""
供应商管理测试 - 覆盖供应商的创建、查询列表和状态更新操作。

测试路径:
  POST   /api/v1/suppliers/           - 创建供应商
  GET    /api/v1/suppliers/           - 获取供应商列表
  GET    /api/v1/suppliers/{id}       - 获取单个供应商
  PUT    /api/v1/suppliers/{id}       - 更新供应商
  DELETE /api/v1/suppliers/{id}       - 删除供应商
"""
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
        # Pydantic v2 将 Decimal 序列化为字符串，需转换为 float 比较
        assert float(data["rating"]) == 5.0  # 默认评分
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
        """测试创建重复 code 的供应商，后端查重应返回 400 错误。"""
        payload = {
            "name": "重复供应商",
            "code": test_supplier.code,  # 重复的 code
        }
        # 后端在创建前先查重，返回 400 Bad Request
        response = client.post(
            "/api/v1/suppliers/",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


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
        """测试按不存在的状态筛选供应商，应返回 422（枚举校验失败）。"""
        response = client.get(
            "/api/v1/suppliers/?status=nonexistent_status",
            headers=admin_auth_headers,
        )
        # status 参数类型为 SupplierStatus 枚举，非法值会被 FastAPI 拒绝
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


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
    """更新供应商状态测试集合。

    后端通过独立的 /blacklist 和 /unblacklist 端点管理供应商状态，
    SupplierUpdate schema 不包含 status 字段。
    """

    def test_update_supplier_to_blacklisted(self, client, admin_auth_headers, test_supplier):
        """测试将供应商加入黑名单。"""
        # 后端通过 POST /api/v1/suppliers/{id}/blacklist 设置为黑名单
        response = client.post(
            f"/api/v1/suppliers/{test_supplier.id}/blacklist",
            json={"reason": "测试黑名单"},
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "blacklisted"

    def test_update_supplier_reactivate(self, client, admin_auth_headers, db_session, test_supplier):
        """测试将已黑名单的供应商重新激活。"""
        # 先将供应商加入黑名单
        response = client.post(
            f"/api/v1/suppliers/{test_supplier.id}/blacklist",
            json={"reason": "临时黑名单"},
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        # 通过 POST /api/v1/suppliers/{id}/unblacklist 重新激活
        response = client.post(
            f"/api/v1/suppliers/{test_supplier.id}/unblacklist",
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

    def test_delete_supplier_success(self, client, admin_auth_headers, db_session, test_org):
        """测试删除已存在的供应商，应返回成功消息。"""
        from app.models import Supplier
        supplier = Supplier(
            name="待删除供应商",
            code="SUP-DEL-001",
            status="active",
            org_id=test_org.id,
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
