import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'
import type { User, UserRole } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const refreshToken = ref<string>(localStorage.getItem('refresh_token') || '')
  const user = ref<User | null>(null)
  try {
    const raw = localStorage.getItem('user')
    if (raw) user.value = JSON.parse(raw)
  } catch {
    user.value = null
  }

  const isLoggedIn = computed(() => !!token.value)
  const isSuperAdmin = computed(() => user.value?.role === 'super_admin')

  function _saveTokens(accessToken: string, refreshTokenValue?: string) {
    token.value = accessToken
    localStorage.setItem('token', accessToken)
    if (refreshTokenValue) {
      refreshToken.value = refreshTokenValue
      localStorage.setItem('refresh_token', refreshTokenValue)
    }
  }

  async function login(username: string, password: string) {
    const data = await authApi.login(username, password)
    _saveTokens(data.access_token, data.refresh_token)
    const userInfo = await authApi.me()
    user.value = userInfo
    localStorage.setItem('user', JSON.stringify(userInfo))
    return userInfo
  }

  async function logout() {
    try {
      await authApi.logout(refreshToken.value)
    } catch {
      // 忽略网络错误
    }
    token.value = ''
    refreshToken.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
  }

  function hasRole(required: UserRole | UserRole[] | undefined): boolean {
    if (!required) return true
    const role = user.value?.role
    if (!role) return false
    if (Array.isArray(required)) {
      if (role === 'super_admin') return true
      return required.includes(role)
    }
    if (required === 'super_admin') return role === 'super_admin'
    return role === required || role === 'super_admin'
  }

  /** 从 localStorage 恢复登录态（页面刷新时由路由守卫调用） */
  function initAuth() {
    const t = localStorage.getItem('token')
    if (t) token.value = t
    const rt = localStorage.getItem('refresh_token')
    if (rt) refreshToken.value = rt
    try {
      const raw = localStorage.getItem('user')
      if (raw) user.value = JSON.parse(raw)
    } catch {
      user.value = null
    }
  }

  return {
    token, refreshToken, user,
    isLoggedIn, isSuperAdmin,
    login, logout, hasRole, initAuth,
  }
})
