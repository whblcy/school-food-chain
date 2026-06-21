"""端到端体验测试：1) 管理员做采购 + 库存操作 2) 普通操作员操作 3) 教育局监管视角

用法: python e2e_test.py
需要: 后端在 127.0.0.1:8000 运行中
"""
from __future__ import annotations

import json
import urllib.request
from typing import Dict


BASE = "http://127.0.0.1:8000"


def login(username: str, password: str) -> str:
    data = json.dumps({"username": username, "password": password}).encode()
    req = urllib.request.Request(BASE + "/api/v1/auth/login", data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())["access_token"]


def api(token: str, method: str, path: str, body: Dict | None = None) -> Dict | list:
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    else:
        data = b"" if method != "GET" else None
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def main() -> None:
    print("=" * 60)
    print("  School Food Chain — 端到端体验测试")
    print("=" * 60)

    admin = login("admin", "admin123")
    operator = login("school_user", "school123")

    print("\n[1] 管理员：获取食材列表")
    ingredients = api(admin, "GET", "/api/v1/ingredients")
    print(f"    共 {len(ingredients)} 条食材")
    for ing in ingredients:
        print(f"      - {ing.get('name')}: {ing.get('current_stock')} / {ing.get('safety_stock')}")

    print("\n[2] 管理员：获取供应商列表")
    suppliers = api(admin, "GET", "/api/v1/suppliers")
    print(f"    共 {len(suppliers)} 个供应商")

    print("\n[3] 管理员：模拟入库（采购 5 份大米，单价 2.5）")
    rice_id = ingredients[0]["id"]
    result = api(admin, "POST", "/api/v1/stock/in", {
        "ingredient_id": rice_id,
        "quantity": 5,
        "unit_price": 2.5,
        "inspector1_id": 1,
        "inspector2_id": 1,
    })
    print(f"    ✅ 批次: {result.get('batch_no')}  总金额: {result.get('total_price')}")

    print("\n[4] 管理员：查询库存明细（入库 + 出库）")
    stock_ins = api(admin, "GET", "/api/v1/stock/in")
    stock_outs = api(admin, "GET", "/api/v1/stock/out")
    print(f"    入库记录: {len(stock_ins)} 条； 出库记录: {len(stock_outs)} 条")

    print("\n[5] 普通操作员：登录并查询食材（组织隔离验证）")
    op_ingredients = api(operator, "GET", "/api/v1/ingredients")
    print(f"    共 {len(op_ingredients)} 条食材 (应和管理员看到的一致)")

    print("\n[6] 普通操作员：做一笔出库操作")
    out = api(operator, "POST", "/api/v1/stock/out", {
        "ingredient_id": rice_id,
        "quantity": 2,
        "unit_price": 2.5,
        "purpose": "厨房消耗",
        "department": "厨房",
    })
    print(f"    ✅ 出库完成: 数量 {out.get('quantity')}, 总金额 {out.get('total_price')}")

    print("\n[7] 再次查询食材（验证库存变化）")
    updated = api(admin, "GET", "/api/v1/ingredients")
    for ing in updated:
        print(f"    - {ing.get('name')}: {ing.get('current_stock')}")

    print("\n[8] 教育局监管看板")
    dashboard = api(admin, "GET", "/api/v1/gov/dashboard")
    print(f"    学校数: {dashboard.get('school_count')}")
    print(f"    低库存预警: {dashboard.get('low_stock_alert')}")
    print(f"    今日入库: {dashboard.get('today_stock_in')}")

    print("\n[9] 教育局：月度报告")
    report = api(admin, "GET", "/api/v1/gov/reports/monthly")
    print(f"    本月采购总额: {report.get('total_purchase')}")
    print(f"    分类统计: {report.get('category_breakdown')}")

    print("\n" + "=" * 60)
    print("  ✅ 端到端体验测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
