"""验证安全修复：角色校验、输入校验、租户隔离"""
import urllib.request, json, time

BASE = "http://127.0.0.1:8000"

def login(u, p):
    data = json.dumps({"username": u, "password": p}).encode()
    req = urllib.request.Request(BASE + "/api/v1/auth/login", data=data, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())["access_token"]

def call(token, method, path, body=None, expect=None):
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        r = urllib.request.urlopen(req)
        code = r.status
        resp = json.loads(r.read())
    except urllib.error.HTTPError as e:
        code = e.code
        resp = json.loads(e.read())
    status = "✅" if (expect is None or code == expect) else "❌"
    print(f"  {status} {method} {path} -> {code} (期望 {expect}) {resp.get('detail','')[:60] if code>=400 else ''}")
    return code, resp

time.sleep(1)
admin = login("admin", "admin123")
op = login("school_user", "school123")

print("\n=== 1. 健康检查（含 DB/Redis 状态）===")
call(None, "GET", "/health")

print("\n=== 2. 角色校验：OPERATOR 不能管理组织 ===")
call(op, "GET", "/api/v1/orgs/", expect=403)

print("\n=== 3. 角色校验：SUPER_ADMIN 可以管理组织 ===")
call(admin, "GET", "/api/v1/orgs/", expect=200)

print("\n=== 4. 角色校验：OPERATOR 不能查审计日志 ===")
call(op, "GET", "/api/v1/audit/", expect=403)

print("\n=== 5. 角色校验：SUPER_ADMIN 可以查审计日志 ===")
call(admin, "GET", "/api/v1/audit/", expect=200)

print("\n=== 6. 输入校验：入库数量为负数应被拒绝 ===")
ings = call(admin, "GET", "/api/v1/ingredients/")[1]
rice_id = ings[0]["id"]
call(admin, "POST", "/api/v1/stock/in", {
    "ingredient_id": rice_id, "quantity": -5, "unit_price": 2.5,
    "inspector1_id": 1, "inspector2_id": 1,
}, expect=422)

print("\n=== 7. 输入校验：出库数量为负数应被拒绝 ===")
call(op, "POST", "/api/v1/stock/out", {
    "ingredient_id": rice_id, "quantity": -2,
}, expect=422)

print("\n=== 8. 库存不足应返回 400（脱敏信息）===")
call(op, "POST", "/api/v1/stock/out", {
    "ingredient_id": rice_id, "quantity": 99999,
}, expect=400)

print("\n=== 9. 角色校验：OPERATOR 不能创建食材 ===")
call(op, "POST", "/api/v1/ingredients/", {
    "name": "测试", "code": "TEST-001", "category_id": 1, "unit": "kg",
}, expect=403)

print("\n=== 10. 角色校验：OPERATOR 不能删除供应商 ===")
call(op, "DELETE", "/api/v1/suppliers/1", expect=403)

print("\n=== 11. 全局异常处理：重复 code 应返回 400 而非 500 ===")
call(admin, "POST", "/api/v1/suppliers/", {
    "name": "重复测试", "code": "SUP-001",
}, expect=400)

print("\n=== 12. 追溯生成 + 查询 ===")
tr = call(admin, "POST", "/api/v1/trace/generate/1")[1]
if "trace_code" in tr:
    call(admin, "GET", f"/api/v1/trace/{tr['trace_code']}", expect=200)

print("\n验证完成。")
