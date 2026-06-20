const app = getApp()

Page({
  data: {
    isLoggedIn: false,
    username: 'admin',
    password: 'admin123',
    errorMsg: '',
    loading: false,
    apiUrl: '',
    userInfo: {},
    today: '',
    stats: {
      ingredients: 0,
      stock: 0,
      suppliers: 0,
      alerts: 0
    },
    recentStockIn: [],
    lowStock: []
  },

  onLoad() {
    this.setData({ apiUrl: app.globalData.apiBaseUrl })
    this.setToday()

    const token = wx.getStorageSync('token')
    if (token) {
      this.setData({ isLoggedIn: true })
      this.loadData()
    }
  },

  onShow() {
    if (this.data.isLoggedIn) {
      this.loadData()
    }
  },

  setToday() {
    const now = new Date()
    const weekDays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
    const dateStr = `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 ${weekDays[now.getDay()]}`
    this.setData({ today: dateStr })
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value })
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value })
  },

  async handleLogin() {
    const { username, password } = this.data
    if (!username || !password) {
      this.setData({ errorMsg: '请输入用户名和密码' })
      return
    }

    this.setData({ loading: true, errorMsg: '' })

    try {
      const result = await app.request({
        url: '/auth/login',
        method: 'POST',
        data: { username, password }
      })

      app.globalData.token = result.access_token
      wx.setStorageSync('token', result.access_token)

      // 获取用户信息
      try {
        const userInfo = await app.request({ url: '/users/me' })
        app.globalData.userInfo = userInfo
        wx.setStorageSync('userInfo', userInfo)
        this.setData({ userInfo, isLoggedIn: true })
      } catch (e) {
        this.setData({ userInfo: { username }, isLoggedIn: true })
      }

      this.loadData()
    } catch (e) {
      this.setData({ errorMsg: '登录失败: ' + e.message })
    } finally {
      this.setData({ loading: false })
    }
  },

  async loadData() {
    // 加载统计数据
    try {
      const ingredients = await app.request({ url: '/ingredients' })
      const items = Array.isArray(ingredients) ? ingredients : (ingredients.items || [])
      const totalStock = items.reduce((sum, i) => sum + (i.current_stock || 0), 0)
      const lowCount = items.filter(i => (i.current_stock || 0) <= (i.safety_stock || 0)).length

      const suppliers = await app.request({ url: '/suppliers' })
      const supList = Array.isArray(suppliers) ? suppliers : (suppliers.items || [])

      this.setData({
        'stats.ingredients': items.length,
        'stats.stock': Math.round(totalStock),
        'stats.suppliers': supList.length,
        'stats.alerts': lowCount,
        lowStock: items.filter(i => (i.current_stock || 0) <= (i.safety_stock || 0)).slice(0, 5)
      })
    } catch (e) {
      this.loadMockData()
    }

    // 加载最近入库
    try {
      const stockIn = await app.request({ url: '/stock/in' })
      const list = Array.isArray(stockIn) ? stockIn : (stockIn.items || [])
      this.setData({ recentStockIn: list.slice(0, 5) })
    } catch (e) {
      this.setData({
        recentStockIn: [
          { id: 1, ingredient_name: '东北大米', quantity: 500, unit: 'kg', supplier_name: '绿源粮油', created_at: '2025-06-20' },
          { id: 2, ingredient_name: '五花肉', quantity: 100, unit: 'kg', supplier_name: '鲜肉联', created_at: '2025-06-20' },
          { id: 3, ingredient_name: '西红柿', quantity: 200, unit: 'kg', supplier_name: '蔬菜基地A', created_at: '2025-06-19' },
        ]
      })
    }
  },

  loadMockData() {
    this.setData({
      'stats.ingredients': 128,
      'stats.stock': 3560,
      'stats.suppliers': 24,
      'stats.alerts': 5,
      lowStock: [
        { id: 1, name: '食用油', current_stock: 5, safety_stock: 20 },
        { id: 2, name: '酱油', current_stock: 3, safety_stock: 15 },
        { id: 3, name: '土豆', current_stock: 50, safety_stock: 100 },
      ]
    })
  },

  goToPage(e) {
    wx.switchTab({ url: e.currentTarget.dataset.url })
  }
})
