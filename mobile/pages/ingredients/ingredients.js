const app = getApp()

Page({
  data: {
    keyword: '',
    activeCategory: '',
    ingredients: [],
    allIngredients: [],
    showModal: false,
    selectedItem: {}
  },

  onLoad() {
    this.loadData()
  },

  onShow() {
    this.loadData()
  },

  async loadData() {
    try {
      const result = await app.request({ url: '/ingredients' })
      const items = Array.isArray(result) ? result : (result.items || [])
      const processed = items.map(item => {
        const stock = item.current_stock || 0
        const safety = item.safety_stock || 1
        const progress = Math.min(Math.round((stock / Math.max(safety * 2, 1)) * 100), 100)
        let status = '正常'
        if (stock <= 0) status = '缺货'
        else if (stock <= safety * 0.5) status = '紧急'
        else if (stock <= safety) status = '偏低'
        return { ...item, progress, status }
      })
      this.setData({
        allIngredients: processed,
        ingredients: processed
      })
    } catch (e) {
      this.loadMockData()
    }
  },

  loadMockData() {
    const mock = [
      { id: 1, name: '东北大米', code: 'DC001', category: '粮油', unit: 'kg', current_stock: 500, safety_stock: 200, specification: '25kg/袋' },
      { id: 2, name: '五花肉', code: 'RH001', category: '肉类', unit: 'kg', current_stock: 80, safety_stock: 50, specification: '冷鲜肉' },
      { id: 3, name: '西红柿', code: 'SC001', category: '蔬菜', unit: 'kg', current_stock: 30, safety_stock: 100, specification: '新鲜' },
      { id: 4, name: '食用油', code: 'LY001', category: '粮油', unit: '桶', current_stock: 5, safety_stock: 20, specification: '5L/桶' },
      { id: 5, name: '鸡蛋', code: 'JD001', category: '蛋奶', unit: '盘', current_stock: 200, safety_stock: 50, specification: '30枚/盘' },
      { id: 6, name: '酱油', code: 'TW001', category: '调味品', unit: '瓶', current_stock: 3, safety_stock: 15, specification: '500ml/瓶' },
      { id: 7, name: '土豆', code: 'SC002', category: '蔬菜', unit: 'kg', current_stock: 50, safety_stock: 100, specification: '新鲜' },
      { id: 8, name: '草鱼', code: 'SC001', category: '水产', unit: 'kg', current_stock: 20, safety_stock: 30, specification: '活鱼' },
    ]
    const processed = mock.map(item => {
      const stock = item.current_stock || 0
      const safety = item.safety_stock || 1
      const progress = Math.min(Math.round((stock / Math.max(safety * 2, 1)) * 100), 100)
      let status = '正常'
      if (stock <= 0) status = '缺货'
      else if (stock <= safety * 0.5) status = '紧急'
      else if (stock <= safety) status = '偏低'
      return { ...item, progress, status }
    })
    this.setData({ allIngredients: processed, ingredients: processed })
  },

  onSearch(e) {
    const keyword = e.detail.value.toLowerCase()
    this.setData({ keyword })
    this.filterData(keyword, this.data.activeCategory)
  },

  filterCategory(e) {
    const category = e.currentTarget.dataset.category
    this.setData({ activeCategory: category })
    this.filterData(this.data.keyword, category)
  },

  filterData(keyword, category) {
    let filtered = this.data.allIngredients
    if (keyword) {
      filtered = filtered.filter(i => i.name.toLowerCase().includes(keyword))
    }
    if (category) {
      filtered = filtered.filter(i => i.category === category)
    }
    this.setData({ ingredients: filtered })
  },

  showDetail(e) {
    this.setData({
      showModal: true,
      selectedItem: e.currentTarget.dataset.item
    })
  },

  closeModal() {
    this.setData({ showModal: false })
  },

  preventClose() {
    // 阻止冒泡
  }
})
