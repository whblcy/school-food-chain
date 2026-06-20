const app = getApp()

Page({
  data: {
    searchCode: '',
    traceResult: null,
    traceList: []
  },

  onLoad() {
    this.loadTraceList()
  },

  onShow() {
    this.loadTraceList()
  },

  async loadTraceList() {
    try {
      const result = await app.request({ url: '/trace' })
      const items = Array.isArray(result) ? result : (result.items || [])
      this.setData({ traceList: items })
    } catch (e) {
      this.setData({
        traceList: [
          { trace_code: 'TR-20250620-A1B2C3', ingredient_name: '东北大米', supplier_name: '绿源粮油', status: 'active' },
          { trace_code: 'TR-20250619-D4E5F6', ingredient_name: '五花肉', supplier_name: '鲜肉联', status: 'active' },
          { trace_code: 'TR-20250615-G7H8I9', ingredient_name: '西红柿', supplier_name: '蔬菜基地A', status: 'consumed' },
        ]
      })
    }
  },

  onSearchInput(e) {
    this.setData({ searchCode: e.detail.value })
  },

  async doSearch() {
    const code = this.data.searchCode.trim()
    if (!code) {
      wx.showToast({ title: '请输入追溯码', icon: 'none' })
      return
    }
    wx.showLoading({ title: '查询中' })
    try {
      const result = await app.request({ url: `/trace/${code}` })
      this.setData({
        traceResult: {
          ...result,
          step: result.stock_out_date ? 4 : 3
        }
      })
    } catch (e) {
      // 模拟数据
      this.setData({
        traceResult: {
          trace_code: code,
          status: 'active',
          step: 3,
          ingredient_name: '东北大米',
          supplier_name: '绿源粮油',
          quantity: 500,
          unit: 'kg',
          stock_in_date: '2025-06-18',
          inspector: '张三/李四',
          storage_location: 'A区-01号库',
          production_date: '2025-06-15',
          expiry_date: '2025-12-15',
          stock_out_date: ''
        }
      })
    } finally {
      wx.hideLoading()
    }
  },

  quickSearch(e) {
    const code = e.currentTarget.dataset.code
    this.setData({ searchCode: code })
    this.doSearch()
  },

  scanCode() {
    wx.scanCode({
      success: (res) => {
        this.setData({ searchCode: res.result })
        this.doSearch()
      },
      fail: () => {
        wx.showToast({ title: '扫码失败', icon: 'none' })
      }
    })
  }
})
