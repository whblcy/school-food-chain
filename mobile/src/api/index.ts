import type {
  User, TokenResponse, Ingredient, Supplier, StockIn, StockOut, TraceRecord,
} from '@/types'

// API 基础地址：H5 走代理，小程序/App 走配置的完整 URL
const baseURL: string = (() => {
  // #ifdef H5
  return '/api/v1'
  // #endif
  // #ifndef H5
  return 'http://localhost:8000/api/v1'
  // #endif
})()

// 并发刷新去重
let _refreshing: Promise<string> | null = null

async function _doRefresh(): Promise<string> {
  const refreshToken = uni.getStorageSync('refresh_token')
  if (!refreshToken) throw new Error('no refresh token')

  return new Promise((resolve, reject) => {
    uni.request({
      url: `${baseURL}/auth/refresh`,
      method: 'POST',
      timeout: 10000,
      header: { Authorization: `Bearer ${refreshToken}` },
      success: (res) => {
        if (res.statusCode === 200) {
          const data = res.data as TokenResponse
          uni.setStorageSync('token', data.access_token)
          uni.setStorageSync('refresh_token', data.refresh_token)
          resolve(data.access_token)
        } else {
          reject(new Error('refresh failed'))
        }
      },
      fail: () => reject(new Error('refresh network error')),
    })
  })
}

interface RequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: Record<string, unknown> | string | ArrayBuffer
  header?: Record<string, string>
}

function request<T = unknown>(options: RequestOptions): Promise<T> {
  const url = options.url.startsWith('http') ? options.url : baseURL + options.url

  return new Promise<T>((resolve, reject) => {
    const doRequest = (token: string, retried = false) => {
      uni.request({
        url,
        method: options.method || 'GET',
        data: options.data,
        timeout: 15000,
        header: {
          'Content-Type': 'application/json',
          ...(options.header || {}),
          Authorization: token ? `Bearer ${token}` : '',
        },
        success: async (res) => {
          if (res.statusCode === 401) {
            if (options.url.includes('/auth/login') || options.url.includes('/auth/refresh')) {
              reject(new Error((res.data as { detail?: string })?.detail || '未登录'))
              return
            }
            if (retried) {
              _clearAuth()
              reject(new Error('登录已过期'))
              return
            }
            try {
              _refreshing = _refreshing || _doRefresh()
              const newToken = await _refreshing
              _refreshing = null
              doRequest(newToken, true)
            } catch {
              _refreshing = null
              _clearAuth()
              reject(new Error('登录已过期'))
            }
            return
          }
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(res.data as T)
          } else {
            reject(new Error((res.data as { detail?: string })?.detail || `请求失败: ${res.statusCode}`))
          }
        },
        fail: () => reject(new Error('网络请求失败')),
      })
    }
    doRequest(uni.getStorageSync('token'))
  })
}

function _clearAuth() {
  uni.removeStorageSync('token')
  uni.removeStorageSync('refresh_token')
  uni.removeStorageSync('user')
  uni.reLaunch({ url: '/pages/login/login' })
}

// ---- Auth API ----
export const authApi = {
  login: (username: string, password: string) =>
    request<TokenResponse>({ url: '/auth/login', method: 'POST', data: { username, password } }),
  refresh: () => request<TokenResponse>({ url: '/auth/refresh', method: 'POST' }),
  logout: (refreshToken?: string) =>
    request({ url: '/auth/logout', method: 'POST', data: { refresh_token: refreshToken } }),
  me: () => request<User>({ url: '/auth/me' }),
}

// ---- Ingredients API ----
export const ingredientApi = {
  list: (params?: { skip?: number; limit?: number }) =>
    request<Ingredient[]>({ url: '/ingredients', data: params }),
}

// ---- Suppliers API ----
export const supplierApi = {
  list: (params?: { skip?: number; limit?: number }) =>
    request<Supplier[]>({ url: '/suppliers', data: params }),
}

// ---- Stock API ----
export const stockApi = {
  in: {
    list: (params?: { skip?: number; limit?: number }) =>
      request<StockIn[]>({ url: '/stock/in', data: params }),
  },
  out: {
    list: (params?: { skip?: number; limit?: number }) =>
      request<StockOut[]>({ url: '/stock/out', data: params }),
  },
}

// ---- Trace API ----
export const traceApi = {
  get: (code: string) =>
    request<TraceRecord>({ url: `/trace/${encodeURIComponent(code)}` }),
  list: (params?: { skip?: number; limit?: number }) =>
    request<TraceRecord[]>({ url: '/trace', data: params }),
}

export default request
