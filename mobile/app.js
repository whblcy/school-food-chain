App({
  globalData: {
    apiBaseUrl: 'http://localhost:8000/api/v1',
    token: '',
    userInfo: null
  },

  onLaunch() {
    const token = wx.getStorageSync('token')
    if (token) {
      this.globalData.token = token
      const userInfo = wx.getStorageSync('userInfo')
      if (userInfo) {
        this.globalData.userInfo = userInfo
      }
    }
  },

  request(options) {
    const app = this
    const url = options.url.startsWith('http') ? options.url : app.globalData.apiBaseUrl + options.url
    return new Promise((resolve, reject) => {
      wx.request({
        url,
        method: options.method || 'GET',
        data: options.data,
        header: {
          'Content-Type': 'application/json',
          'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : ''
        },
        success: (res) => {
          if (res.statusCode === 401) {
            wx.removeStorageSync('token')
            wx.removeStorageSync('userInfo')
            app.globalData.token = ''
            app.globalData.userInfo = null
            wx.reLaunch({ url: '/pages/index/index' })
            reject(new Error('未登录'))
            return
          }
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(res.data)
          } else {
            reject(new Error(res.data?.detail || `请求失败: ${res.statusCode}`))
          }
        },
        fail: (err) => {
          reject(new Error('网络请求失败'))
        }
      })
    })
  }
})
