import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.DEV ? 'http://localhost:8000/api/v1' : '/api/v1',
  timeout: 10000
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  console.log('[API Request]', config.url, 'token:', token ? token.substring(0, 20) + '...' : 'NULL')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // 避免在登录页重复跳转
      if (window.location.pathname !== '/login') {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api

// Auth
export const login = (data) => api.post('/auth/login', data)

// Ingredients
export const getIngredients = (params) => api.get('/ingredients', { params })
export const createIngredient = (data) => api.post('/ingredients', data)
export const updateIngredient = (id, data) => api.put(`/ingredients/${id}`, data)
export const deleteIngredient = (id) => api.delete(`/ingredients/${id}`)

// Stock
export const stockIn = (data) => api.post('/stock/in', data)
export const stockOut = (data) => api.post('/stock/out', data)
export const inventoryCheck = (data) => api.post('/stock/check', data)
export const getStockIn = () => api.get('/stock/in')
export const getStockOut = () => api.get('/stock/out')

// Suppliers
export const getSuppliers = () => api.get('/suppliers')
export const createSupplier = (data) => api.post('/suppliers', data)
export const updateSupplier = (id, data) => api.put(`/suppliers/${id}`, data)
export const deleteSupplier = (id) => api.delete(`/suppliers/${id}`)

// Finance
export const getMonthlySummary = (params) => api.get('/finance/monthly-summary', { params })
export const getYearlyTrend = (params) => api.get('/finance/yearly-trend', { params })

// Reports
export const getStockSummary = () => api.get('/reports/stock-summary')
export const getLowStock = () => api.get('/reports/low-stock')

// Trace
export const generateTrace = (ingredientId, stockInId) => 
  api.post(`/trace/generate/${ingredientId}?stock_in_id=${stockInId}`)
export const getTrace = (code) => api.get(`/trace/${code}`)

// Users
export const getUsers = () => api.get('/users')
export const createUser = (data) => api.post('/users', data)
export const updateUser = (id, data) => api.put(`/users/${id}`, data)
export const deleteUser = (id) => api.delete(`/users/${id}`)

// Orgs
export const getOrgs = () => api.get('/orgs')
export const createOrg = (data) => api.post('/orgs', data)
export const updateOrg = (id, data) => api.put(`/orgs/${id}`, data)
export const deleteOrg = (id) => api.delete(`/orgs/${id}`)
