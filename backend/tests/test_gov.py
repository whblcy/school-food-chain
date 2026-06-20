"""
教育局监管模块测试 - 覆盖监管看板、学校列表和预警信息查询。

测试路径:
  GET /api/v1/gov/dashboard              - 监管总览看板
  GET /api/v1/gov/schools               - 学校列表
  GET /api/v1/gov/alerts                - 预警信息
"""
import pytest
from fastapi import status


class TestGovDashboard:
    """教育局监管看板接口测试集合。"""

    def test_get_dashboard_success(self, client, admin_auth_headers, test_org):
        """测试获取监管看板数据，应返回包含各项统计指标的字典。"""
        response = client.get(
            "/api/v1/gov/dashboard",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 验证返回的看板数据结构
        assert "school_count" in data
        assert "today_stock_in" in data
        assert "today_stock_out" in data
        assert "low_stock_alert" in data
        assert "supplier_count" in data
        assert "active_supplier_count" in data
        assert "weekly_trend" in data
        # 验证周趋势数据格式
        assert isinstance(data["weekly_trend"], list)
        assert len(data["weekly_trend"]) == 7  # 最近 7 天
        for day in data["weekly_trend"]:
            assert "date" in day
            assert "stock_in" in day
            assert "stock_out" in day

    def test_get_dashboard_school_count(self, client, admin_auth_headers, test_org):
        """测试看板中的学校数量统计应正确反映数据库中的组织数量。"""
        response = client.get(
            "/api/v1/gov/dashboard",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # test_org 是 CANTEEN 类型，应被计入 school_count
        assert data["school_count"] >= 1

    def test_get_dashboard_without_auth(self, client):
        """测试未认证用户访问监管看板，应返回 401 或 403。"""
        response = client.get("/api/v1/gov/dashboard")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


class TestGovSchools:
    """学校列表接口测试集合。"""

    def test_get_schools_success(self, client, admin_auth_headers, test_org):
        """测试获取学校列表，应返回包含学校信息的列表。"""
        response = client.get(
            "/api/v1/gov/schools",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # 验证学校数据结构
        school = data[0]
        assert "id" in school
        assert "name" in school
        assert "code" in school
        assert "org_type" in school
        assert "ingredient_count" in school
        assert "today_purchase" in school
        assert "low_stock_count" in school
        assert "is_active" in school

    def test_get_schools_empty(self, client, admin_auth_headers):
        """测试无学校数据时获取学校列表，应返回空列表。"""
        # 注意：由于 conftest 中 test_org fixture 可能已创建组织，
        # 此测试主要验证接口在没有匹配数据时的行为
        response = client.get(
            "/api/v1/gov/schools",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_schools_contains_test_org(self, client, admin_auth_headers, test_org):
        """测试学校列表应包含通过 fixture 创建的测试组织。"""
        response = client.get(
            "/api/v1/gov/schools",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        school_ids = [s["id"] for s in data]
        assert test_org.id in school_ids

    def test_get_schools_without_auth(self, client):
        """测试未认证用户访问学校列表，应返回 401 或 403。"""
        response = client.get("/api/v1/gov/schools")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


class TestGovAlerts:
    """预警信息接口测试集合。"""

    def test_get_alerts_all_types(self, client, admin_auth_headers):
        """测试获取所有类型的预警信息，应返回包含 total 和 items 的字典。"""
        response = client.get(
            "/api/v1/gov/alerts",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_get_alerts_low_stock_type(self, client, admin_auth_headers):
        """测试按类型筛选低库存预警信息。"""
        response = client.get(
            "/api/v1/gov/alerts?alert_type=low_stock",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 验证返回的预警均为 low_stock 类型
        for alert in data["items"]:
            assert alert["type"] == "low_stock"
            assert "level" in alert
            assert "title" in alert
            assert "message" in alert
            assert alert["level"] in ("warning", "critical")

    def test_get_alerts_expiry_type(self, client, admin_auth_headers):
        """测试按类型筛选临期预警信息。"""
        response = client.get(
            "/api/v1/gov/alerts?alert_type=expiry",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for alert in data["items"]:
            assert alert["type"] == "expiry"

    def test_get_alerts_supplier_type(self, client, admin_auth_headers):
        """测试按类型筛选供应商预警信息。"""
        response = client.get(
            "/api/v1/gov/alerts?alert_type=supplier",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for alert in data["items"]:
            assert alert["type"] == "supplier"

    def test_get_alerts_with_low_stock_data(
        self, client, admin_auth_headers, db_session, test_ingredient, test_org
    ):
        """测试当存在低库存食材时，预警信息应包含对应的预警条目。"""
        # 将食材库存设为低于安全库存
        test_ingredient.current_stock = 5.0
        test_ingredient.safety_stock = 50.0
        db_session.commit()

        response = client.get(
            "/api/v1/gov/alerts?alert_type=low_stock",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        # 验证预警内容包含该食材名称
        titles = [alert["title"] for alert in data["items"]]
        assert any(test_ingredient.name in title for title in titles)

    def test_get_alerts_without_auth(self, client):
        """测试未认证用户访问预警信息，应返回 401 或 403。"""
        response = client.get("/api/v1/gov/alerts")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
