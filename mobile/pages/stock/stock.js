const app = getApp()

Page({
  data: {
    activeTab: 'in',
    submitting: false,
    ingredientOptions: [],
    userOptions: [],
    selectedIngredient: null,
    inForm: {
      quantity: '',
      unit_price: '',
      production_date: '',
      expiry_date: '',
      inspector1_id: null,
      inspector1_name: '',
      inspector2_id: null,
      inspector2_name: '',
      remark: ''
    },
    outForm: {
      ingredient_id: null,
      ingredient_name: '',
      current_stock: 0,
      unit: '',
      quantity: '',
      purpose: '',
      department: '',
      remark: ''
    },
    records: []
  },

  onLoad() {
    this.setDefaultDates()
    this.loadIngredients()
    this.loadUsers()
    this.loadRecords()
  },

  setDefaultDates() {
    const today = new Date().toISOString().split('T')[0]
    const sixMonthsLater = new Date()
    sixMonthsLater.setMonth(sixMonthsLater.getMonth() + 6)
    this.setData({
      'inForm.production_date': today,
      'inForm.expiry_date': sixMonthsLater.toISOString().split('T')[0]
    })
  },

  async loadIngredients() {
    try {
      const result = await app.request({ url: '/ingredients' })
      const items = Array.isArray(result) ? result : (result.items || [])
      const options = items.map(i => ({ ...i, name: `${i.name} (库存: ${i.current_stock}${i.unit})` }))
      this.setData({ ingredientOptions: options })
    } catch (e) {
      this.setData({
        ingredientOptions: [
          { id: 1, name: '东北大米 (库存: 500kg)', current_stock: 500, unit: 'kg' },
          { id: 2, name: '五花肉 (库存: 80kg)', current_stock: 80, unit: 'kg' },
          { id: 3, name: '西红柿 (库存: 30kg)', current_stock: 30, unit: 'kg' },
        ]
      })
    }
  },

  async loadUsers() {
    try {
      const result = await app.request({ url: '/users' })
      const items = Array.isArray(result) ? result : (result.items || [])
      const options = items.map(u => ({ id: u.id, name: u.real_name || u.username }))
      this.setData({ userOptions: options })
    } catch (e) {
      this.setData({ userOptions: [{ id: 1, name: '管理员' }, { id: 2, name: '张三' }] })
    }
  },

  async loadRecords() {
    try {
      const url = this.data.activeTab === 'in' ? '/stock/in' : '/stock/out'
      const result = await app.request({ url })
      const items = Array.isArray(result) ? result : (result.items || [])
      this.setData({ records: items.slice(0, 5) })
    } catch (e) {
      this.setData({
        records: [
          { id: 1, ingredient_name: '东北大米', quantity: 500, created_at: '2025-06-20' },
          { id: 2, ingredient_name: '五花肉', quantity: 100, created_at: '2025-06-20' },
          { id: 3, ingredient_name: '西红柿', quantity: 200, created_at: '2025-06-19' },
        ]
      })
    }
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })
    this.loadRecords()
  },

  onIngredientChange(e) {
    const idx = e.detail.value
    const item = this.data.ingredientOptions[idx]
    this.setData({ selectedIngredient: item })
  },

  onInQuantity(e) { this.setData({ 'inForm.quantity': e.detail.value }) },
  onInPrice(e) { this.setData({ 'inForm.unit_price': e.detail.value }) },
  onInRemark(e) { this.setData({ 'inForm.remark': e.detail.value }) },

  onProductionDate(e) { this.setData({ 'inForm.production_date': e.detail.value }) },
  onExpiryDate(e) { this.setData({ 'inForm.expiry_date': e.detail.value }) },

  onInspector1Change(e) {
    const idx = e.detail.value
    const user = this.data.userOptions[idx]
    this.setData({ 'inForm.inspector1_id': user.id, 'inForm.inspector1_name': user.name })
  },

  onInspector2Change(e) {
    const idx = e.detail.value
    const user = this.data.userOptions[idx]
    this.setData({ 'inForm.inspector2_id': user.id, 'inForm.inspector2_name': user.name })
  },

  onOutIngredientChange(e) {
    const idx = e.detail.value
    const item = this.data.ingredientOptions[idx]
    this.setData({
      'outForm.ingredient_id': item.id,
      'outForm.ingredient_name': item.name.split(' (')[0],
      'outForm.current_stock': item.current_stock,
      'outForm.unit': item.unit
    })
  },

  onOutQuantity(e) { this.setData({ 'outForm.quantity': e.detail.value }) },
  onOutPurpose(e) { this.setData({ 'outForm.purpose': e.detail.value }) },
  onOutDepartment(e) { this.setData({ 'outForm.department': e.detail.value }) },
  onOutRemark(e) { this.setData({ 'outForm.remark': e.detail.value }) },

  async submitStockIn() {
    const { selectedIngredient, inForm } = this.data
    if (!selectedIngredient) {
      wx.showToast({ title: '请选择食材', icon: 'none' })
      return
    }
    if (!inForm.quantity || inForm.quantity <= 0) {
      wx.showToast({ title: '请输入数量', icon: 'none' })
      return
    }
    if (!inForm.unit_price) {
      wx.showToast({ title: '请输入单价', icon: 'none' })
      return
    }
    if (!inForm.inspector1_id || !inForm.inspector2_id) {
      wx.showToast({ title: '请选择两位验收人', icon: 'none' })
      return
    }

    this.setData({ submitting: true })
    try {
      await app.request({
        url: '/stock/in',
        method: 'POST',
        data: {
          ingredient_id: selectedIngredient.id,
          quantity: parseFloat(inForm.quantity),
          unit_price: parseFloat(inForm.unit_price),
          production_date: inForm.production_date,
          expiry_date: inForm.expiry_date,
          inspector1_id: inForm.inspector1_id,
          inspector2_id: inForm.inspector2_id,
          remark: inForm.remark
        }
      })
      wx.showToast({ title: '入库成功', icon: 'success' })
      this.setData({
        selectedIngredient: null,
        'inForm.quantity': '',
        'inForm.unit_price': '',
        'inForm.remark': ''
      })
      this.loadRecords()
    } catch (e) {
      wx.showToast({ title: '入库失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  },

  async submitStockOut() {
    const { outForm } = this.data
    if (!outForm.ingredient_id) {
      wx.showToast({ title: '请选择食材', icon: 'none' })
      return
    }
    if (!outForm.quantity || outForm.quantity <= 0) {
      wx.showToast({ title: '请输入数量', icon: 'none' })
      return
    }
    if (parseFloat(outForm.quantity) > outForm.current_stock) {
      wx.showToast({ title: '库存不足', icon: 'none' })
      return
    }

    this.setData({ submitting: true })
    try {
      await app.request({
        url: '/stock/out',
        method: 'POST',
        data: {
          ingredient_id: outForm.ingredient_id,
          quantity: parseFloat(outForm.quantity),
          purpose: outForm.purpose,
          department: outForm.department,
          remark: outForm.remark
        }
      })
      wx.showToast({ title: '出库成功', icon: 'success' })
      this.setData({
        'outForm.ingredient_id': null,
        'outForm.ingredient_name': '',
        'outForm.current_stock': 0,
        'outForm.quantity': '',
        'outForm.purpose': '',
        'outForm.department': '',
        'outForm.remark': ''
      })
      this.loadRecords()
    } catch (e) {
      wx.showToast({ title: '出库失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  }
})
