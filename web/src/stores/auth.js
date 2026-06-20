import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  const login = async (username, password) => {
    const res = await axios.post('/api/v1/auth/login', { username, password })
    token.value = res.data.access_token
    localStorage.setItem('token', res.data.access_token)
    axios.defaults.headers.common['Authorization'] = `Bearer ${res.data.access_token}`
    // 尝试获取用户信息
    try {
      const me = await axios.get('/api/v1/users/me', {
        headers: { Authorization: `Bearer ${res.data.access_token}` }
      })
      user.value = me.data
      localStorage.setItem('user', JSON.stringify(me.data))
    } catch (e) {
      user.value = { username, real_name: username }
    }
    return res.data
  }

  const logout = () => {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    delete axios.defaults.headers.common['Authorization']
  }

  const initAuth = () => {
    if (token.value) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
    }
    const saved = localStorage.getItem('user')
    if (saved) {
      try { user.value = JSON.parse(saved) } catch (e) {}
    }
  }

  return { token, user, login, logout, initAuth }
})
