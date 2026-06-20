<template>
  <div class="gov-dashboard">
    <!-- 顶部统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="4" v-for="(card, idx) in statCards" :key="idx">
        <el-card class="stat-card" :body-style="{ padding: '20px' }">
          <div class="stat-icon" :style="{ backgroundColor: card.bg }">{{ card.icon }}</div>
          <div class="stat-number">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>近7天出入库趋势</span>
            </div>
          </template>
          <div ref="trendChart" style="height: 320px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>预警分布</span>
            </div>
          </template>
          <div class="alert-summary">
            <div class="alert-item" v-for="alert in alertSummary" :key="alert.type">
              <div class="alert-dot" :style="{ backgroundColor: alert.color }"></div>
              <div class="alert-info">
                <div class="alert-title">{{ alert.title }}</div>
                <div class="alert-count">{{ alert.count }} 条</div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 学校列表 + 预警列表 -->
    <el-row :gutter="20" class="list-row">
      <el-col :span="14">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>学校监管列表</span>
              <el-input v-model="schoolSearch" placeholder="搜索学校" size="small" style="width: 200px" clearable />
            </div>
          </template>
          <el-table :data="filteredSchools" stripe size="small">
            <el-table-column prop="name" label="学校名称" min-width="140" />
            <el-table-column prop="code" label="编码" width="100" />
            <el-table-column prop="ingredient_count" label="食材数" width="80" align="center" />
            <el-table-column prop="today_purchase" label="今日采购" width="110" align="right">
              <template #default="{ row }">¥{{ row.today_purchase.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="low_stock_count" label="预警" width="80" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.low_stock_count > 0" type="danger" size="small">{{ row.low_stock_count }}</el-tag>
                <span v-else style="color: #909399;">-</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="viewSchool(row)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>实时预警</span>
              <el-link type="primary" :underline="false" @click="loadAlerts">刷新</el-link>
            </div>
          </template>
          <div class="alert-list" v-loading="alertLoading">
            <div v-for="alert in alerts" :key="alert.title" class="alert-card" :class="alert.level">
              <div class="alert-header">
                <el-tag :type="alert.level === 'critical' ? 'danger' : 'warning'" size="small">
                  {{ alert.level === 'critical' ? '紧急' : '警告' }}
                </el-tag>
                <span class="alert-school" v-if="alert.school_name">{{ alert.school_name }}</span>
              </div>
              <div class="alert-title-text">{{ alert.title }}</div>
              <div class="alert-message">{{ alert.message }}</div>
              <div class="alert-time">{{ formatTime(alert.created_at) }}</div>
            </div>
            <el-empty v-if="alerts.length === 0" description="暂无预警" :image-size="60" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 学校详情弹窗 -->
    <el-dialog v-model="schoolDialogVisible" :title="selectedSchool?.name" width="700px">
      <el-descriptions :column="2" border size="small" v-if="selectedSchool">
        <el-descriptions-item label="编码">{{ selectedSchool.code }}</el-descriptions-item>
        <el-descriptions-item label="地址">{{ selectedSchool.address || '-' }}</el-descriptions-item>
        <el-descriptions-item label="联系人">{{ selectedSchool.contact_person || '-' }}</el-descriptions-item>
        <el-descriptions-item label="电话">{{ selectedSchool.contact_phone || '-' }}</el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <div class="section-title">食材库存</div>
      <el-table :data="schoolDetail.ingredients" size="small" stripe>
        <el-table-column prop="name" label="食材" />
        <el-table-column prop="current_stock" label="当前库存" align="right" />
        <el-table-column prop="safety_stock" label="安全库存" align="right" />
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === '正常' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <el-divider />

      <div class="section-title">最近入库</div>
      <el-table :data="schoolDetail.recent_stock_in" size="small" stripe>
        <el-table-column prop="batch_no" label="批次号" width="120" />
        <el-table-column prop="ingredient_name" label="食材" />
        <el-table-column prop="quantity" label="数量" align="right" />
        <el-table-column prop="total_price" label="金额" align="right">
          <template #default="{ row }">¥{{ row.total_price?.toFixed(2) }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import api from '../api'

const statCards = ref([
  { icon: '🏫', label: '学校数量', value: 0, bg: '#e3f2fd' },
  { icon: '📥', label: '今日入库', value: 0, bg: '#e8f5e9' },
  { icon: '📤', label: '今日出库', value: 0, bg: '#fff3e0' },
  { icon: '⚠️', label: '低库存预警', value: 0, bg: '#ffebee' },
  { icon: '🏭', label: '供应商', value: 0, bg: '#f3e5f5' },
  { icon: '✅', label: '活跃供应商', value: 0, bg: '#e0f7fa' },
])

const trendChart = ref(null)
let chartInst = null
const weeklyTrend = ref([])

const schoolSearch = ref('')
const schools = ref([])
const filteredSchools = computed(() => {
  const kw = schoolSearch.value.trim().toLowerCase()
  if (!kw) return schools.value
  return schools.value.filter(s => s.name.toLowerCase().includes(kw))
})

const alerts = ref([])
const alertLoading = ref(false)
const alertSummary = ref([
  { type: 'low_stock', title: '库存预警', count: 0, color: '#ff453a' },
  { type: 'expiry', title: '临期预警', count: 0, color: '#ff9f0a' },
  { type: 'supplier', title: '供应商预警', count: 0, color: '#bf5af2' },
])

const schoolDialogVisible = ref(false)
const selectedSchool = ref(null)
const schoolDetail = ref({ ingredients: [], recent_stock_in: [], recent_inventory_checks: [] })

const formatTime = (t) => {
  if (!t) return ''
  const d = new Date(t)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

const loadDashboard = async () => {
  try {
    const res = await api.get('/gov/dashboard')
    const data = res.data
    statCards.value[0].value = data.school_count
    statCards.value[1].value = data.today_stock_in
    statCards.value[2].value = data.today_stock_out
    statCards.value[3].value = data.low_stock_alert
    statCards.value[4].value = data.supplier_count
    statCards.value[5].value = data.active_supplier_count
    weeklyTrend.value = data.weekly_trend || []
    initChart()
  } catch (e) {
    // 模拟数据
    statCards.value[0].value = 12
    statCards.value[1].value = 1250
    statCards.value[2].value = 890
    statCards.value[3].value = 8
    statCards.value[4].value = 24
    statCards.value[5].value = 20
    weeklyTrend.value = [
      { date: '06-14', stock_in: 800, stock_out: 600 },
      { date: '06-15', stock_in: 950, stock_out: 700 },
      { date: '06-16', stock_in: 1100, stock_out: 850 },
      { date: '06-17', stock_in: 900, stock_out: 750 },
      { date: '06-18', stock_in: 1200, stock_out: 900 },
      { date: '06-19', stock_in: 1050, stock_out: 800 },
      { date: '06-20', stock_in: 1250, stock_out: 890 },
    ]
    initChart()
  }
}

const loadSchools = async () => {
  try {
    const res = await api.get('/gov/schools')
    schools.value = res.data || []
  } catch (e) {
    schools.value = [
      { id: 1, name: '第一中学', code: 'S001', ingredient_count: 45, today_purchase: 3200, low_stock_count: 2, address: 'xx路1号', contact_person: '张校长', contact_phone: '13800138001' },
      { id: 2, name: '第二中学', code: 'S002', ingredient_count: 38, today_purchase: 2800, low_stock_count: 0, address: 'xx路2号', contact_person: '李校长', contact_phone: '13800138002' },
      { id: 3, name: '实验小学', code: 'S003', ingredient_count: 52, today_purchase: 4100, low_stock_count: 3, address: 'xx路3号', contact_person: '王校长', contact_phone: '13800138003' },
      { id: 4, name: '外国语学校', code: 'S004', ingredient_count: 41, today_purchase: 3500, low_stock_count: 1, address: 'xx路4号', contact_person: '赵校长', contact_phone: '13800138004' },
      { id: 5, name: '职业中学', code: 'S005', ingredient_count: 35, today_purchase: 2100, low_stock_count: 0, address: 'xx路5号', contact_person: '刘校长', contact_phone: '13800138005' },
    ]
  }
}

const loadAlerts = async () => {
  alertLoading.value = true
  try {
    const res = await api.get('/gov/alerts')
    alerts.value = res.data?.items || []
    // 更新汇总
    const summary = { low_stock: 0, expiry: 0, supplier: 0 }
    alerts.value.forEach(a => { summary[a.type] = (summary[a.type] || 0) + 1 })
    alertSummary.value[0].count = summary.low_stock
    alertSummary.value[1].count = summary.expiry
    alertSummary.value[2].count = summary.supplier
  } catch (e) {
    alerts.value = [
      { type: 'low_stock', level: 'warning', title: '库存预警: 食用油', message: '当前库存 5桶，低于安全库存 20桶', school_name: '第一中学', created_at: new Date().toISOString() },
      { type: 'low_stock', level: 'critical', title: '库存预警: 酱油', message: '当前库存 3瓶，低于安全库存 15瓶', school_name: '实验小学', created_at: new Date().toISOString() },
      { type: 'expiry', level: 'warning', title: '临期预警: 东北大米', message: '批次 RK001 将于 15 天后过期', school_name: '', created_at: new Date().toISOString() },
    ]
    alertSummary.value[0].count = 2
    alertSummary.value[1].count = 1
    alertSummary.value[2].count = 0
  } finally {
    alertLoading.value = false
  }
}

const viewSchool = async (row) => {
  selectedSchool.value = row
  try {
    const res = await api.get(`/gov/schools/${row.id}/detail`)
    schoolDetail.value = res.data
  } catch (e) {
    schoolDetail.value = {
      ingredients: [
        { id: 1, name: '东北大米', current_stock: 500, safety_stock: 200, status: '正常' },
        { id: 2, name: '食用油', current_stock: 5, safety_stock: 20, status: '预警' },
      ],
      recent_stock_in: [
        { batch_no: 'RK20250620001', ingredient_name: '东北大米', quantity: 500, total_price: 1600 },
        { batch_no: 'RK20250620002', ingredient_name: '五花肉', quantity: 100, total_price: 2800 },
      ],
      recent_inventory_checks: []
    }
  }
  schoolDialogVisible.value = true
}

const initChart = () => {
  if (!trendChart.value) return
  chartInst = echarts.init(trendChart.value)
  const dates = weeklyTrend.value.map(d => d.date)
  const ins = weeklyTrend.value.map(d => d.stock_in)
  const outs = weeklyTrend.value.map(d => d.stock_out)
  chartInst.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['入库', '出库'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value' },
    series: [
      { name: '入库', type: 'line', smooth: true, data: ins, itemStyle: { color: '#0a84ff' }, areaStyle: { color: 'rgba(10,132,255,0.1)' } },
      { name: '出库', type: 'line', smooth: true, data: outs, itemStyle: { color: '#30d158' }, areaStyle: { color: 'rgba(48,209,88,0.1)' } },
    ]
  })
}

onMounted(() => {
  loadDashboard()
  loadSchools()
  loadAlerts()
})

onUnmounted(() => {
  chartInst?.dispose()
})
</script>

<style scoped>
.gov-dashboard {
  padding-bottom: 20px;
}
.stat-row {
  margin-bottom: 20px;
}
.stat-card {
  text-align: center;
  position: relative;
  overflow: hidden;
}
.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  margin: 0 auto 12px;
}
.stat-number {
  font-size: 28px;
  font-weight: 700;
  color: #1d1d1f;
  margin-bottom: 4px;
}
.stat-label {
  font-size: 13px;
  color: #86868b;
}
.chart-row {
  margin-bottom: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.alert-summary {
  padding: 10px 0;
}
.alert-item {
  display: flex;
  align-items: center;
  padding: 14px 0;
  border-bottom: 1px solid #f5f5f7;
}
.alert-item:last-child {
  border-bottom: none;
}
.alert-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 12px;
}
.alert-info {
  flex: 1;
}
.alert-title {
  font-size: 14px;
  color: #1d1d1f;
  font-weight: 500;
}
.alert-count {
  font-size: 13px;
  color: #86868b;
  margin-top: 2px;
}
.list-row {
  margin-bottom: 20px;
}
.alert-list {
  max-height: 480px;
  overflow-y: auto;
}
.alert-card {
  padding: 14px 16px;
  border-radius: 10px;
  margin-bottom: 10px;
  background-color: #fafafa;
  border-left: 4px solid #ff9f0a;
}
.alert-card.critical {
  background-color: #fff5f5;
  border-left-color: #ff453a;
}
.alert-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.alert-school {
  font-size: 12px;
  color: #86868b;
}
.alert-title-text {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 4px;
}
.alert-message {
  font-size: 13px;
  color: #636366;
  margin-bottom: 6px;
}
.alert-time {
  font-size: 12px;
  color: #c7c7cc;
}
.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 16px 0 12px;
}
</style>
