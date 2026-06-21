import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  const login = async (username, password) => {
    const res = await api.post('/auth/login', { username, password })
    token.value = res.data.access_token
    localStorage.setItem('token', res.data.access_token)
    // 获取用户信息
    try {
      const me = await api.get('/users/me')
      user.value = me.data
      localStorage.setItem('user', JSON.stringify(me.data))
    } catch (e) {
      user.value = { username, real_name: username }
      localStorage.setItem('user', JSON.stringify(user.value))
    }
    return res.data
  }

  const logout = () => {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  const initAuth = () => {
    const savedToken = localStorage.getItem('token')
    if (savedToken) {
      token.value = savedToken
    }
    const saved = localStorage.getItem('user')
    if (saved) {
      try { user.value = JSON.parse(saved) } catch (e) {}
    }
  }

  return { token, user, login, logout, initAuth }
})
