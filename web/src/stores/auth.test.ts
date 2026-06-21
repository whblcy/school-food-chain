import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

// Mock authApi 模块
vi.mock('@/api', () => ({
  authApi: {
    login: vi.fn(),
    logout: vi.fn(),
    me: vi.fn(),
  },
  // 保留其他导出避免破坏其他模块导入
  ingredientApi: {},
  supplierApi: {},
  stockApi: {},
  financeApi: {},
  financeApiExt: {},
  traceApi: {},
  auditApi: {},
  userApi: {},
  orgApi: {},
  reportApi: {},
  govApi: {},
}))

import { authApi } from '@/api'

describe('useAuthStore', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('初始状态应为未登录', () => {
    const store = useAuthStore()
    expect(store.isLoggedIn).toBe(false)
    expect(store.user).toBeNull()
    expect(store.token).toBe('')
  })

  it('login 成功后应保存 token 和用户信息', async () => {
    const mockUser = { id: 1, username: 'admin', email: null, real_name: '管理员', role: 'admin', org_id: 1 }
    const mockToken = { access_token: 'atk', refresh_token: 'rft', token_type: 'bearer', expires_in: 3600 }
    vi.mocked(authApi.login).mockResolvedValue(mockToken as never)
    vi.mocked(authApi.me).mockResolvedValue(mockUser as never)

    const store = useAuthStore()
    await store.login('admin', 'pass')

    expect(store.token).toBe('atk')
    expect(store.refreshToken).toBe('rft')
    expect(store.user).toEqual(mockUser)
    expect(store.isLoggedIn).toBe(true)
    expect(localStorage.getItem('token')).toBe('atk')
    expect(localStorage.getItem('refresh_token')).toBe('rft')
    expect(JSON.parse(localStorage.getItem('user') || 'null')).toEqual(mockUser)
  })

  it('logout 应清除所有认证状态', async () => {
    vi.mocked(authApi.logout).mockResolvedValue(undefined as never)

    const store = useAuthStore()
    // 先模拟登录态
    localStorage.setItem('token', 'atk')
    localStorage.setItem('refresh_token', 'rft')
    localStorage.setItem('user', JSON.stringify({ id: 1, username: 'admin' }))
    store.initAuth()

    await store.logout()

    expect(store.token).toBe('')
    expect(store.refreshToken).toBe('')
    expect(store.user).toBeNull()
    expect(store.isLoggedIn).toBe(false)
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
    expect(localStorage.getItem('user')).toBeNull()
  })

  describe('hasRole', () => {
    it('required 为 undefined 时应返回 true', () => {
      const store = useAuthStore()
      expect(store.hasRole(undefined)).toBe(true)
    })

    it('未登录用户应返回 false', () => {
      const store = useAuthStore()
      expect(store.hasRole('admin')).toBe(false)
    })

    it('super_admin 应拥有所有权限', () => {
      const store = useAuthStore()
      store.user = { id: 1, username: 'root', email: null, real_name: null, role: 'super_admin', org_id: null }
      expect(store.hasRole('admin')).toBe(true)
      expect(store.hasRole(['admin', 'operator'])).toBe(true)
      expect(store.hasRole('super_admin')).toBe(true)
    })

    it('普通角色应精确匹配', () => {
      const store = useAuthStore()
      store.user = { id: 2, username: 'op', email: null, real_name: null, role: 'operator', org_id: 1 }
      expect(store.hasRole('operator')).toBe(true)
      expect(store.hasRole('admin')).toBe(false)
      expect(store.hasRole(['admin', 'operator'])).toBe(true)
      expect(store.hasRole(['admin', 'viewer'])).toBe(false)
    })
  })

  describe('initAuth', () => {
    it('应从 localStorage 恢复登录态', () => {
      const mockUser = { id: 1, username: 'admin', email: null, real_name: null, role: 'admin', org_id: 1 }
      localStorage.setItem('token', 'restored_token')
      localStorage.setItem('refresh_token', 'restored_rt')
      localStorage.setItem('user', JSON.stringify(mockUser))

      const store = useAuthStore()
      store.initAuth()

      expect(store.token).toBe('restored_token')
      expect(store.refreshToken).toBe('restored_rt')
      expect(store.user).toEqual(mockUser)
      expect(store.isLoggedIn).toBe(true)
    })

    it('localStorage 中 user 为损坏 JSON 时应安全降级', () => {
      localStorage.setItem('token', 't')
      localStorage.setItem('user', '{invalid json')

      const store = useAuthStore()
      store.initAuth()

      expect(store.token).toBe('t')
      expect(store.user).toBeNull()
    })
  })
})
