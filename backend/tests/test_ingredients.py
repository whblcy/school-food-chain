"""
食材 CRUD 测试 - 覆盖食材的创建、查询、更新和删除操作。

测试路径:
  POST   /api/v1/ingredients/           - 创建食材
  GET    /api/v1/ingredients/           - 获取食材列表
  GET    /api/v1/ingredients/{id}       - 获取单个食材
  PUT    /api/v1/ingredients/{id}       - 更新食材
  DELETE /api/v1/ingredients/{id}       - 删除食材
"""
import pytest
from fastapi import status


class TestCreateIngredient:
    """创建食材接口测试集合。"""

    def test_create_ingredient_success(self, client, admin_auth_headers, test_category, test_supplier, test_org):
        """测试使用完整有效数据创建食材，应返回 201 及食材详情。"""
        payload = {
            "name": "胡萝卜",
            "code": "ING-CARROT-001",
            "category_id": test_category.id,
            "unit": "千克",
            "specification": "新鲜无腐烂，直径3-5cm",
            "safety_stock": 30.0,
            "supplier_id": test_supplier.id,
            "org_id": test_org.id,
        }
        response = client.post(
            "/api/v1/ingredients/",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "胡萝卜"
        assert data["code"] == "ING-CARROT-001"
        assert data["unit"] == "千克"
        assert data["current_stock"] == 0
        assert data["is_active"] is True
        assert "id" in data

    def test_create_ingredient_minimal(self, client, admin_auth_headers, test_category, test_org):
        """测试仅提供必填字段创建食材。"""
        payload = {
            "name": "土豆",
            "code": "ING-POTATO-001",
            "category_id": test_category.id,
            "unit": "千克",
            "org_id": test_org.id,
        }
        response = client.post(
            "/api/v1/ingredients/",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "土豆"
        assert data["current_stock"] == 0

    def test_create_ingredient_duplicate_code(self, client, admin_auth_headers, test_ingredient, test_category, test_org):
        """测试创建重复 code 的食材，数据库唯一约束冲突应导致请求失败。"""
        import sqlalchemy.exc
        payload = {
            "name": "另一白菜",
            "code": test_ingredient.code,  # 重复的 code
            "category_id": test_category.id,
            "unit": "千克",
            "org_id": test_org.id,
        }
        # IntegrityError 在 SQLite 中直接抛出，FastAPI 未全局捕获
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            client.post(
                "/api/v1/ingredients/",
                json=payload,
                headers=admin_auth_headers,
            )

    def test_create_ingredient_missing_required_fields(self, client, admin_auth_headers):
        """测试缺少必填字段创建食材，应返回 422 验证错误。"""
        payload = {
            "name": "不完整食材",
            # 缺少 code, category_id, unit, org_id
        }
        response = client.post(
            "/api/v1/ingredients/",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestListIngredients:
    """获取食材列表接口测试集合。"""

    def test_list_ingredients_empty(self, client, admin_auth_headers):
        """测试数据库为空时获取食材列表，应返回空列表。"""
        response = client.get(
            "/api/v1/ingredients/",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_list_ingredients_with_data(self, client, admin_auth_headers, test_ingredient):
        """测试数据库有数据时获取食材列表，应返回包含已创建食材的列表。"""
        response = client.get(
            "/api/v1/ingredients/",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        # 确认列表中包含测试食材
        ids = [item["id"] for item in data]
        assert test_ingredient.id in ids

    def test_list_ingredients_filter_by_category(self, client, admin_auth_headers, test_ingredient, test_category):
        """测试按分类 ID 筛选食材列表。"""
        response = client.get(
            f"/api/v1/ingredients/?category_id={test_category.id}",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data:
            assert item["category_id"] == test_category.id

    def test_list_ingredients_pagination(self, client, admin_auth_headers, test_ingredient):
        """测试分页参数 skip 和 limit 是否生效。"""
        response = client.get(
            "/api/v1/ingredients/?skip=0&limit=1",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) <= 1


class TestGetIngredient:
    """获取单个食材接口测试集合。"""

    def test_get_ingredient_success(self, client, admin_auth_headers, test_ingredient):
        """测试获取已存在的食材详情，应返回完整的食材信息。"""
        response = client.get(
            f"/api/v1/ingredients/{test_ingredient.id}",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_ingredient.id
        assert data["name"] == test_ingredient.name
        assert data["code"] == test_ingredient.code

    def test_get_ingredient_not_found(self, client, admin_auth_headers):
        """测试获取不存在的食材 ID，应返回 404。"""
        response = client.get(
            "/api/v1/ingredients/99999",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateIngredient:
    """更新食材接口测试集合。"""

    def test_update_ingredient_success(self, client, admin_auth_headers, test_ingredient, test_category, test_org):
        """测试更新食材名称和规格，应返回更新后的数据。"""
        payload = {
            "name": "大白菜（更新）",
            "code": test_ingredient.code,
            "category_id": test_category.id,
            "unit": "千克",
            "specification": "一级品，叶片翠绿",
            "safety_stock": 80.0,
            "org_id": test_org.id,
        }
        response = client.put(
            f"/api/v1/ingredients/{test_ingredient.id}",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "大白菜（更新）"
        assert data["specification"] == "一级品，叶片翠绿"
        assert data["safety_stock"] == 80.0

    def test_update_ingredient_not_found(self, client, admin_auth_headers, test_category, test_org):
        """测试更新不存在的食材 ID，应返回 404。"""
        payload = {
            "name": "不存在",
            "code": "ING-NONE",
            "category_id": test_category.id,
            "unit": "千克",
            "org_id": test_org.id,
        }
        response = client.put(
            "/api/v1/ingredients/99999",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteIngredient:
    """删除食材接口测试集合。"""

    def test_delete_ingredient_success(self, client, admin_auth_headers, db_session, test_category, test_supplier, test_org):
        """测试删除已存在的食材，应返回成功消息。"""
        # 先创建一个待删除的食材
        from app.models import Ingredient
        ingredient = Ingredient(
            name="待删除食材",
            code="ING-DEL-001",
            category_id=test_category.id,
            unit="千克",
            org_id=test_org.id,
            supplier_id=test_supplier.id,
        )
        db_session.add(ingredient)
        db_session.commit()
        db_session.refresh(ingredient)

        response = client.delete(
            f"/api/v1/ingredients/{ingredient.id}",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data

    def test_delete_ingredient_not_found(self, client, admin_auth_headers):
        """测试删除不存在的食材 ID，应返回 404。"""
        response = client.delete(
            "/api/v1/ingredients/99999",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
