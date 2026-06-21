import urllib.request, json, time

for i in range(5):
    try:
        r = urllib.request.urlopen('http://localhost:8000/health')
        print('health:', r.status)
        break
    except Exception as e:
        print(f'wait... {e}')
        time.sleep(1)

data = json.dumps({'username': 'admin', 'password': 'admin123'}).encode()
req = urllib.request.Request('http://localhost:8000/api/v1/auth/login', data=data, headers={'Content-Type': 'application/json'})
token = json.loads(urllib.request.urlopen(req).read())['access_token']
print('登录 ok, token len', len(token))

endpoints = [
    '/api/v1/suppliers/', '/api/v1/ingredients/', '/api/v1/stock/in',
    '/api/v1/stock/out', '/api/v1/users/', '/api/v1/orgs/',
    '/api/v1/audit/', '/api/v1/reports/summary', '/api/v1/trace/',
    '/api/v1/finance/transactions',
]
for path in endpoints:
    try:
        r = urllib.request.urlopen(
            urllib.request.Request(f'http://localhost:8000{path}',
                                   headers={'Authorization': f'Bearer {token}'}))
        body = json.loads(r.read())
        if isinstance(body, list):
            print(f'{path}: 200 OK ({len(body)} items)')
        else:
            print(f'{path}: 200 OK (keys={list(body.keys())[:5]})')
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:200]
        print(f'{path}: {e.code} - {detail}')
    except Exception as e:
        print(f'{path}: ERR {e}')
