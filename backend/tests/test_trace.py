"""
追溯模块测试 — 覆盖追溯记录查询和详情。

测试路径:
  GET /api/v1/trace/         - 追溯记录列表
  GET /api/v1/trace/{code}   - 追溯码查询详情
"""
from datetime import date

import pytest
from fastapi import status

from app.models import TraceRecord


class TestListTrace:
    """追溯记录列表测试。"""

    def test_list_trace_requires_auth(self, client):
        """未认证访问追溯列表应返回 401。"""
        response = client.get("/api/v1/trace/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_trace_empty(self, client, admin_auth_headers):
        """空追溯列表应返回空数组。"""
        response = client.get("/api/v1/trace/", headers=admin_auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_list_trace_with_data(
        self, client, db_session, test_org, test_user, test_ingredient, test_supplier, admin_auth_headers
    ):
        """查询有数据的追溯列表应返回记录。"""
        record = TraceRecord(
            trace_code="TRACE-001",
            ingredient_id=test_ingredient.id,
            supplier_id=test_supplier.id,
            batch_no="BATCH-001",
            production_date=date(2026, 1, 1),
            expiry_date=date(2026, 6, 1),
            test_report="合格",
            quarantine_cert="合格",
            org_id=test_org.id,
        )
        db_session.add(record)
        db_session.commit()

        response = client.get("/api/v1/trace/", headers=admin_auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        item = data[0]
        assert item["trace_code"] == "TRACE-001"
        assert item["ingredient_name"] == "大白菜"

    def test_list_trace_pagination(
        self, client, db_session, test_org, test_ingredient, admin_auth_headers
    ):
        """追溯记录分页。"""
        for i in range(5):
            db_session.add(TraceRecord(
                trace_code=f"TRACE-{i:03d}",
                ingredient_id=test_ingredient.id,
                org_id=test_org.id,
            ))
        db_session.commit()

        response = client.get(
            "/api/v1/trace/?skip=1&limit=2",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2


class TestGetTraceByCode:
    """追溯码查询测试。"""

    def test_get_trace_not_found(self, client, admin_auth_headers):
        """查询不存在的追溯码应返回 404。"""
        response = client.get(
            "/api/v1/trace/NOTEXIST",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_trace_success(
        self, client, db_session, test_org, test_ingredient, test_supplier, admin_auth_headers
    ):
        """查询存在的追溯码应返回详情。"""
        record = TraceRecord(
            trace_code="TRACE-OK",
            ingredient_id=test_ingredient.id,
            supplier_id=test_supplier.id,
            batch_no="BATCH-OK",
            production_date=date(2026, 1, 1),
            expiry_date=date(2026, 12, 1),
            test_report="合格",
            quarantine_cert="合格",
            org_id=test_org.id,
        )
        db_session.add(record)
        db_session.commit()

        response = client.get(
            "/api/v1/trace/TRACE-OK",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["trace_code"] == "TRACE-OK"
        assert data["batch_no"] == "BATCH-OK"
        assert data["ingredient_name"] == "大白菜"
