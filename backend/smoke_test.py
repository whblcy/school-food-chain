"""后端冒烟测试 - 调用本地 uvicorn 实例。用法: python smoke_test.py"""
from __future__ import annotations

import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8000"


def get_token(username, password):
    data = json.dumps({"username": username, "password": password}).encode()
    req = urllib.request.Request(BASE + "/api/v1/auth/login", data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def main():
    print("[1] GET /health")
    with urllib.request.urlopen(BASE + "/health") as r:
        body = json.loads(r.read())
    assert body.get("status") == "ok"
    print("    OK — status=ok")

    print("[2] 登录 (错误密码)")
    try:
        get_token("admin", "wrong")
    except urllib.error.HTTPError as e:
        assert e.code == 401
        print("    OK — 401 Unauthorized (认证机制正常)")

    print("[3] 登录 (admin/admin123)")
    body = get_token("admin", "admin123")
    token = body.get("access_token")
    assert token and len(token) > 10
    print(f"    OK — access_token 长度 = {len(token)}")

    print("[4] GET /api/v1/auth/me")
    req = urllib.request.Request(BASE + "/api/v1/auth/me", headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=5) as r:
        body = json.loads(r.read())
    assert body.get("username") == "admin"
    print(f"    OK — username={body.get('username')} role={body.get('role')} org_id={body.get('org_id')}")

    print("[5] GET /api/v1/ingredients")
    req = urllib.request.Request(BASE + "/api/v1/ingredients", headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=5) as r:
        items = json.loads(r.read())
    print(f"    OK — 共 {len(items)} 条食材")

    print("[6] POST /api/v1/stock/in (入库)")
    data = json.dumps({"ingredient_id": 1, "quantity": 5, "unit_price": 2.5, "inspector1_id": 1, "inspector2_id": 1}).encode()
    req = urllib.request.Request(BASE + "/api/v1/stock/in", data=data, headers={"Content-Type": "application/json", "Authorization": "Bearer " + token}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        body = json.loads(r.read())
    print(f"    OK — batch_no={body.get('batch_no')} quantity={body.get('quantity')} total={body.get('total_price')}")

    print("[7] POST /api/v1/auth/logout (黑名单)")
    data = b"{}"
    req = urllib.request.Request(BASE + "/api/v1/auth/logout", data=data, headers={"Content-Type": "application/json", "Authorization": "Bearer " + token}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        body = json.loads(r.read())
    print(f"    OK — {body}")

    print("\n=========================")
    print("  所有测试通过 ✅")
    print("=========================")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"\n[X] 测试失败: {exc}", file=sys.stderr)
        sys.exit(1)
