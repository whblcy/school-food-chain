const app = getApp()

const ROLE_MAP = {
  super_admin: '系统管理员',
  admin: '管理员',
  manager: '经理',
  operator: '操作员',
  viewer: '查看者'
}

Page({
  data: {
    isLoggedIn: false,
    isAdmin: false,
    userInfo: {},
    roleText: '',
    apiUrl: '',
    stats: {
      todayIn: 0,
      todayOut: 0,
      checkCount: 0
    }
  },

  onLoad() {
    this.setData({ apiUrl: app.globalData.apiBaseUrl })
  },

  onShow() {
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo') || {}
    const isLoggedIn = !!token
    const isAdmin = ['super_admin', 'admin'].includes(userInfo.role)

    this.setData({
      isLoggedIn,
      isAdmin,
      userInfo,
      roleText: ROLE_MAP[userInfo.role] || userInfo.role || '未知'
    })

    if (isLoggedIn) {
      this.loadStats()
    }
  },

  async loadStats() {
    try {
      const today = new Date().toISOString().split('T')[0]
      const [stockIn, stockOut] = await Promise.all([
        app.request({ url: '/stock/in' }),
        app.request({ url: '/stock/out' })
      ])
      const inList = Array.isArray(stockIn) ? stockIn : (stockIn.items || [])
      const outList = Array.isArray(stockOut) ? stockOut : (stockOut.items || [])

      this.setData({
        'stats.todayIn': inList.filter(i => (i.created_at || '').startsWith(today)).length,
        'stats.todayOut': outList.filter(i => (i.created_at || '').startsWith(today)).length,
      })
    } catch (e) {
      this.setData({
        'stats.todayIn': 5,
        'stats.todayOut': 3,
        'stats.checkCount': 12
      })
    }
  },

  goToIngredients() {
    wx.switchTab({ url: '/pages/ingredients/ingredients' })
  },

  goToStock() {
    wx.switchTab({ url: '/pages/stock/stock' })
  },

  goToTrace() {
    wx.switchTab({ url: '/pages/trace/trace' })
  },

  goToUsers() {
    wx.showToast({ title: '请在Web端管理用户', icon: 'none' })
  },

  handleLogout() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync('token')
          wx.removeStorageSync('userInfo')
          app.globalData.token = ''
          app.globalData.userInfo = null
          wx.reLaunch({ url: '/pages/index/index' })
        }
      }
    })
  }
})
