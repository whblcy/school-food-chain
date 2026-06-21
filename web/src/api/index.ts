import axios, { type AxiosInstance } from 'axios'
import type {
  User, UserWithOrg, TokenResponse, Ingredient, Supplier, StockIn, StockOut,
  InventoryCheck, TraceRecord, AuditLog, MonthlySummary, YearlyTrendItem, GovDashboard,
  StockSummaryItem, LowStockItem, CategoryBreakdownItem, Org,
  GovSchoolListItem, GovSchoolDetail, GovAlert,
} from '@/types'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const api: AxiosInstance = axios.create({
  baseURL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// ---- 请求拦截器：注入 Bearer Token ----
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ---- 响应拦截器：401 自动刷新 ----
let _refreshing: Promise<string> | null = null

async function _doRefresh(): Promise<string> {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) throw new Error('no refresh token')

  const res = await axios.post(
    `${baseURL}/auth/refresh`,
    null,
    { headers: { Authorization: `Bearer ${refreshToken}` } },
  )
  const { access_token, refresh_token: newRefresh } = res.data
  localStorage.setItem('token', access_token)
  localStorage.setItem('refresh_token', newRefresh)
  return access_token
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status !== 401 || original._retried) return Promise.reject(error)
    if (original.url.includes('/auth/login') || original.url.includes('/auth/refresh')) {
      return Promise.reject(error)
    }
    original._retried = true
    try {
      _refreshing = _refreshing || _doRefresh()
      const newToken = await _refreshing
      _refreshing = null
      original.headers.Authorization = `Bearer ${newToken}`
      return api(original)
    } catch (refreshErr) {
      _refreshing = null
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
      return Promise.reject(refreshErr)
    }
  },
)

// ---- Auth API ----
export const authApi = {
  login: (username: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { username, password }).then((r) => r.data),
  refresh: () => api.post<TokenResponse>('/auth/refresh').then((r) => r.data),
  logout: (refreshToken?: string) =>
    api.post('/auth/logout', { refresh_token: refreshToken }),
  me: () => api.get<User>('/auth/me').then((r) => r.data),
}

// ---- Ingredients API ----
export const ingredientApi = {
  list: (params?: { skip?: number; limit?: number; category_id?: number }) =>
    api.get<Ingredient[]>('/ingredients', { params }).then((r) => r.data),
  get: (id: number) => api.get<Ingredient>(`/ingredients/${id}`).then((r) => r.data),
  create: (data: Partial<Ingredient>) => api.post<Ingredient>('/ingredients', data).then((r) => r.data),
  update: (id: number, data: Partial<Ingredient>) => api.put<Ingredient>(`/ingredients/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/ingredients/${id}`),
}

// ---- Suppliers API ----
export const supplierApi = {
  list: (params?: { skip?: number; limit?: number; status?: string }) =>
    api.get<Supplier[]>('/suppliers', { params }).then((r) => r.data),
  create: (data: Partial<Supplier>) => api.post<Supplier>('/suppliers', data).then((r) => r.data),
  update: (id: number, data: Partial<Supplier>) => api.put<Supplier>(`/suppliers/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/suppliers/${id}`),
  blacklist: (id: number, reason: string) =>
    api.post<Supplier>(`/suppliers/${id}/blacklist`, { reason }).then((r) => r.data),
  unblacklist: (id: number) =>
    api.post<Supplier>(`/suppliers/${id}/unblacklist`).then((r) => r.data),
}

// ---- Stock API ----
export const stockApi = {
  in: {
    list: (params?: { skip?: number; limit?: number; ingredient_id?: number; supplier_id?: number }) =>
      api.get<StockIn[]>('/stock/in', { params }).then((r) => r.data),
    create: (data: Record<string, unknown>) => api.post<StockIn>('/stock/in', data).then((r) => r.data),
  },
  out: {
    list: (params?: { skip?: number; limit?: number; ingredient_id?: number }) =>
      api.get<StockOut[]>('/stock/out', { params }).then((r) => r.data),
    create: (data: Record<string, unknown>) => api.post<StockOut>('/stock/out', data).then((r) => r.data),
  },
  check: {
    list: (params?: { skip?: number; limit?: number; ingredient_id?: number }) =>
      api.get<InventoryCheck[]>('/stock/check', { params }).then((r) => r.data),
    create: (data: Record<string, unknown>) => api.post<InventoryCheck>('/stock/check', data).then((r) => r.data),
  },
}

// ---- Finance API ----
export const financeApi = {
  monthlySummary: (year: number, month: number) =>
    api.get<MonthlySummary>('/finance/monthly-summary', { params: { year, month } }).then((r) => r.data),
  yearlyTrend: (year: number) =>
    api.get<YearlyTrendItem[]>('/finance/yearly-trend', { params: { year } }).then((r) => r.data),
  categoryBreakdown: (year: number, month: number) =>
    api.get('/finance/category-breakdown', { params: { year, month } }).then((r) => r.data),
}

// ---- Reports API ----
export const reportApi = {
  stockSummary: () => api.get<StockSummaryItem[]>('/reports/stock-summary').then((r) => r.data),
  lowStock: (params?: { skip?: number; limit?: number }) =>
    api.get<LowStockItem[]>('/reports/low-stock', { params }).then((r) => r.data),
  inventoryValue: () => api.get<{ total_value: number }>('/reports/inventory-value').then((r) => r.data),
}

// ---- Trace API ----
export const traceApi = {
  list: (params?: { skip?: number; limit?: number }) =>
    api.get<TraceRecord[]>('/trace', { params }).then((r) => r.data),
  get: (code: string) => api.get<TraceRecord>(`/trace/${encodeURIComponent(code)}`).then((r) => r.data),
  generate: (ingredientId: number, stockInId: number) =>
    api.post<TraceRecord>(`/trace/generate/${ingredientId}?stock_in_id=${stockInId}`).then((r) => r.data),
}

// ---- Audit API ----
export const auditApi = {
  list: (params?: { skip?: number; limit?: number; user_id?: number; action?: string; target_type?: string; username?: string }) =>
    api.get<AuditLog[]>('/audit', { params }).then((r) => r.data),
}

// ---- Gov API ----
export const govApi = {
  dashboard: () => api.get<GovDashboard>('/gov/dashboard').then((r) => r.data),
  schools: (params?: { skip?: number; limit?: number }) =>
    api.get<GovSchoolListItem[]>('/gov/schools', { params }).then((r) => r.data),
  schoolDetail: (id: number, params?: { skip?: number; limit?: number }) =>
    api.get<GovSchoolDetail>(`/gov/schools/${id}/detail`, { params }).then((r) => r.data),
  alerts: (params?: { alert_type?: string; skip?: number; limit?: number }) =>
    api.get<{ items: GovAlert[] }>('/gov/alerts', { params }).then((r) => r.data),
}

// ---- Users API ----
export const userApi = {
  list: (params?: { skip?: number; limit?: number }) =>
    api.get<UserWithOrg[]>('/users', { params }).then((r) => r.data),
  create: (data: Record<string, unknown>) => api.post<User>('/users', data).then((r) => r.data),
  update: (id: number, data: Record<string, unknown>) => api.put<User>(`/users/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/users/${id}`),
}

// ---- Orgs API ----
export const orgApi = {
  list: (params?: { skip?: number; limit?: number }) =>
    api.get<Org[]>('/orgs', { params }).then((r) => r.data),
  create: (data: Partial<Org>) => api.post<Org>('/orgs', data).then((r) => r.data),
  update: (id: number, data: Partial<Org>) => api.put<Org>(`/orgs/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/orgs/${id}`),
}

// ---- Finance API (扩展) ----
export const financeApiExt = {
  categoryBreakdown: (year: number, month: number) =>
    api.get<CategoryBreakdownItem[]>('/finance/category-breakdown', { params: { year, month } }).then((r) => r.data),
}

export default api
