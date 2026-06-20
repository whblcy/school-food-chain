"""
库存操作测试 - 覆盖入库、出库、库存不足校验和盘点操作。

测试路径:
  POST /api/v1/stock/in     - 入库操作
  POST /api/v1/stock/out    - 出库操作
  POST /api/v1/stock/check  - 库存盘点
"""
import pytest
from fastapi import status


class TestStockIn:
    """入库操作测试集合。"""

    def test_stock_in_success(self, client, admin_auth_headers, test_ingredient, test_supplier, test_user):
        """测试正常入库操作，应创建入库记录并更新食材库存。"""
        payload = {
            "ingredient_id": test_ingredient.id,
            "quantity": 50.0,
            "unit_price": 3.5,
            "supplier_id": test_supplier.id,
            "inspector1_id": test_user.id,
            "inspector2_id": test_user.id,
            "remark": "正常采购入库",
        }
        response = client.post(
            "/api/v1/stock/in",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ingredient_id"] == test_ingredient.id
        assert data["quantity"] == 50.0
        assert data["unit_price"] == 3.5
        assert data["total_price"] == 175.0  # 50 * 3.5
        assert data["batch_no"].startswith("IN")
        assert "id" in data

    def test_stock_in_updates_current_stock(self, client, admin_auth_headers, test_ingredient, test_supplier, test_user, db_session):
        """测试入库后食材的 current_stock 应增加。"""
        original_stock = test_ingredient.current_stock
        payload = {
            "ingredient_id": test_ingredient.id,
            "quantity": 20.0,
            "unit_price": 2.0,
            "supplier_id": test_supplier.id,
            "inspector1_id": test_user.id,
            "inspector2_id": test_user.id,
        }
        response = client.post(
            "/api/v1/stock/in",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        # 刷新食材对象，验证库存变化
        db_session.refresh(test_ingredient)
        assert test_ingredient.current_stock == original_stock + 20.0

    def test_stock_in_nonexistent_ingredient(self, client, admin_auth_headers, test_supplier, test_user):
        """测试对不存在的食材进行入库，应返回 404。"""
        payload = {
            "ingredient_id": 99999,
            "quantity": 10.0,
            "unit_price": 1.0,
            "supplier_id": test_supplier.id,
            "inspector1_id": test_user.id,
            "inspector2_id": test_user.id,
        }
        response = client.post(
            "/api/v1/stock/in",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestStockOut:
    """出库操作测试集合。"""

    def test_stock_out_success(self, client, admin_auth_headers, test_ingredient):
        """测试正常出库操作，库存充足时应成功创建出库记录。"""
        payload = {
            "ingredient_id": test_ingredient.id,
            "quantity": 30.0,
            "unit_price": 3.5,
            "purpose": "午餐烹饪",
            "department": "第一食堂",
        }
        response = client.post(
            "/api/v1/stock/out",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ingredient_id"] == test_ingredient.id
        assert data["quantity"] == 30.0
        assert data["total_price"] == 105.0  # 30 * 3.5

    def test_stock_out_updates_current_stock(self, client, admin_auth_headers, test_ingredient, db_session):
        """测试出库后食材的 current_stock 应减少。"""
        original_stock = test_ingredient.current_stock
        out_quantity = 10.0
        payload = {
            "ingredient_id": test_ingredient.id,
            "quantity": out_quantity,
            "unit_price": 2.0,
            "purpose": "测试出库",
        }
        response = client.post(
            "/api/v1/stock/out",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        db_session.refresh(test_ingredient)
        assert test_ingredient.current_stock == original_stock - out_quantity

    def test_stock_out_insufficient_stock(self, client, admin_auth_headers, test_ingredient):
        """测试库存不足时出库，应返回 400 错误并提示库存不足。"""
        # 尝试出库数量大于当前库存
        payload = {
            "ingredient_id": test_ingredient.id,
            "quantity": 99999.0,
            "unit_price": 1.0,
            "purpose": "超额出库测试",
        }
        response = client.post(
            "/api/v1/stock/out",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Insufficient stock" in data["detail"]

    def test_stock_out_nonexistent_ingredient(self, client, admin_auth_headers):
        """测试对不存在的食材进行出库，应返回 404。"""
        payload = {
            "ingredient_id": 99999,
            "quantity": 10.0,
            "unit_price": 1.0,
        }
        response = client.post(
            "/api/v1/stock/out",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestInventoryCheck:
    """库存盘点操作测试集合。"""

    def test_inventory_check_success(self, client, admin_auth_headers, test_ingredient):
        """测试正常盘点操作，应记录系统库存与实际库存的差异。"""
        system_stock = 100.0
        actual_stock = 85.0
        payload = {
            "ingredient_id": test_ingredient.id,
            "system_stock": system_stock,
            "actual_stock": actual_stock,
            "remark": "月度盘点",
        }
        response = client.post(
            "/api/v1/stock/check",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ingredient_id"] == test_ingredient.id
        assert data["system_stock"] == system_stock
        assert data["actual_stock"] == actual_stock
        # difference = actual_stock - system_stock
        expected_diff = actual_stock - system_stock
        assert data["difference"] == expected_diff

    def test_inventory_check_corrects_stock(self, client, admin_auth_headers, test_ingredient, db_session):
        """测试盘点后食材库存应被校正为实际库存值。"""
        actual_stock = 60.0
        payload = {
            "ingredient_id": test_ingredient.id,
            "system_stock": test_ingredient.current_stock,
            "actual_stock": actual_stock,
            "remark": "盘点校正",
        }
        response = client.post(
            "/api/v1/stock/check",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        db_session.refresh(test_ingredient)
        assert test_ingredient.current_stock == actual_stock

    def test_inventory_check_negative_difference(self, client, admin_auth_headers, test_ingredient):
        """测试实际库存小于系统库存时，差异值应为负数。"""
        payload = {
            "ingredient_id": test_ingredient.id,
            "system_stock": 100.0,
            "actual_stock": 80.0,
            "remark": "盘亏测试",
        }
        response = client.post(
            "/api/v1/stock/check",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["difference"] == -20.0

    def test_inventory_check_nonexistent_ingredient(self, client, admin_auth_headers):
        """测试对不存在的食材进行盘点，应返回 404。"""
        payload = {
            "ingredient_id": 99999,
            "system_stock": 100.0,
            "actual_stock": 100.0,
        }
        response = client.post(
            "/api/v1/stock/check",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
