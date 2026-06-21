import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'
import type { User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(uni.getStorageSync('token') || '')
  const refreshToken = ref<string>(uni.getStorageSync('refresh_token') || '')
  const user = ref<User | null>(uni.getStorageSync('user') || null)

  const isLoggedIn = computed(() => !!token.value)
  const isSuperAdmin = computed(() => user.value?.role === 'super_admin')

  function _saveTokens(accessToken: string, refreshTokenValue?: string) {
    token.value = accessToken
    uni.setStorageSync('token', accessToken)
    if (refreshTokenValue) {
      refreshToken.value = refreshTokenValue
      uni.setStorageSync('refresh_token', refreshTokenValue)
    }
  }

  async function login(username: string, password: string) {
    const data = await authApi.login(username, password)
    _saveTokens(data.access_token, data.refresh_token)
    const userInfo = await authApi.me()
    user.value = userInfo
    uni.setStorageSync('user', userInfo)
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
    uni.removeStorageSync('token')
    uni.removeStorageSync('refresh_token')
    uni.removeStorageSync('user')
  }

  function hasRole(required: string | string[] | undefined): boolean {
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

  /** 从本地缓存恢复登录态 */
  function initAuth() {
    const t = uni.getStorageSync('token')
    if (t) token.value = t
    const rt = uni.getStorageSync('refresh_token')
    if (rt) refreshToken.value = rt
    try {
      const raw = uni.getStorageSync('user')
      if (raw) user.value = typeof raw === 'string' ? JSON.parse(raw) : raw
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
