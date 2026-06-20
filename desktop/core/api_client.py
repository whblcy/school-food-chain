"""API客户端 - 封装所有后端接口调用"""
import json
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class ApiClient:
    def __init__(self, base_url: str, token: str = ''):
        self.base_url = base_url.rstrip('/')
        self.token = token

    def _headers(self) -> dict:
        h = {'Content-Type': 'application/json'}
        if self.token:
            h['Authorization'] = f'Bearer {self.token}'
        return h

    def _request(self, method: str, path: str, data: dict = None, params: dict = None) -> dict:
        url = self.base_url + path
        if params:
            url += '?' + urlencode(params)
        body = json.dumps(data).encode() if data else None
        req = Request(url, data=body, headers=self._headers(), method=method)
        try:
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            logger.error(f'API {method} {path} -> {e.code}: {e.read().decode()}')
            raise
        except URLError as e:
            logger.error(f'API connection error: {e.reason}')
            raise

    def get(self, path, params=None) -> dict:
        return self._request('GET', path, params=params)

    def post(self, path, data=None) -> dict:
        return self._request('POST', path, data=data)

    def put(self, path, data=None) -> dict:
        return self._request('PUT', path, data=data)

    def delete(self, path) -> dict:
        return self._request('DELETE', path)

    # ===== Auth =====
    def login(self, username: str, password: str) -> dict:
        return self.post('/auth/login', {'username': username, 'password': password})

    # ===== Ingredients =====
    def get_ingredients(self, page=1, page_size=50) -> dict:
        return self.get('/ingredients', {'page': page, 'page_size': page_size})

    def create_ingredient(self, data: dict) -> dict:
        return self.post('/ingredients', data)

    def update_ingredient(self, iid: int, data: dict) -> dict:
        return self.put(f'/ingredients/{iid}', data)

    def delete_ingredient(self, iid: int) -> dict:
        return self.delete(f'/ingredients/{iid}')

    # ===== Stock =====
    def stock_in(self, data: dict) -> dict:
        return self.post('/stock/in', data)

    def stock_out(self, data: dict) -> dict:
        return self.post('/stock/out', data)

    def inventory_check(self, data: dict) -> dict:
        return self.post('/stock/check', data)

    def get_stock_in_list(self) -> dict:
        return self.get('/stock/in')

    def get_stock_out_list(self) -> dict:
        return self.get('/stock/out')

    # ===== Suppliers =====
    def get_suppliers(self) -> dict:
        return self.get('/suppliers')

    def create_supplier(self, data: dict) -> dict:
        return self.post('/suppliers', data)

    def update_supplier(self, sid: int, data: dict) -> dict:
        return self.put(f'/suppliers/{sid}', data)

    def delete_supplier(self, sid: int) -> dict:
        return self.delete(f'/suppliers/{sid}')

    # ===== Finance =====
    def get_monthly_summary(self, params=None) -> dict:
        return self.get('/finance/monthly-summary', params)

    def get_yearly_trend(self, year: int) -> dict:
        return self.get('/finance/yearly-trend', {'year': year})

    # ===== Trace =====
    def generate_trace(self, ingredient_id: int, stock_in_id: int) -> dict:
        return self.post(f'/trace/generate/{ingredient_id}', params={'stock_in_id': stock_in_id})

    def get_trace(self, code: str) -> dict:
        return self.get(f'/trace/{code}')

    # ===== Users =====
    def get_users(self) -> dict:
        return self.get('/users')

    def create_user(self, data: dict) -> dict:
        return self.post('/users', data)

    def update_user(self, uid: int, data: dict) -> dict:
        return self.put(f'/users/{uid}', data)

    def delete_user(self, uid: int) -> dict:
        return self.delete(f'/users/{uid}')

    def get_me(self) -> dict:
        return self.get('/users/me')

    # ===== Reports =====
    def get_stock_summary(self) -> dict:
        return self.get('/reports/stock-summary')

    def get_low_stock(self) -> dict:
        return self.get('/reports/low-stock')

    # ===== Orgs =====
    def get_orgs(self) -> dict:
        return self.get('/orgs')
