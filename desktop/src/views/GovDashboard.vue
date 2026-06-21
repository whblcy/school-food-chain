<template>
  <div class="gov-dashboard">
    <!-- 顶部统计卡片 -->
    <div class="stat-grid">
      <n-card v-for="(card, idx) in statCards" :key="idx" class="stat-card" :bordered="false">
        <div class="stat-icon" :style="{ backgroundColor: card.bg }">{{ card.icon }}</div>
        <div class="stat-number">{{ card.value }}</div>
        <div class="stat-label">{{ card.label }}</div>
      </n-card>
    </div>

    <!-- 图表区域 -->
    <n-grid :cols="24" :x-gap="20" :y-gap="20" class="chart-row" item-responsive responsive="screen">
      <n-gi span="24 m:16">
        <n-card :bordered="false">
          <template #header>
            <div class="card-header">
              <span>近7天出入库趋势</span>
            </div>
          </template>
          <div ref="trendChartRef" class="chart-canvas"></div>
        </n-card>
      </n-gi>
      <n-gi span="24 m:8">
        <n-card :bordered="false">
          <template #header>
            <div class="card-header">
              <span>预警分布</span>
            </div>
          </template>
          <div class="alert-summary">
            <div v-for="alert in alertSummary" :key="alert.type" class="alert-item">
              <div class="alert-dot" :style="{ backgroundColor: alert.color }"></div>
              <div class="alert-info">
                <div class="alert-title">{{ alert.title }}</div>
                <div class="alert-count">{{ alert.count }} 条</div>
              </div>
            </div>
          </div>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 学校列表 + 预警列表 -->
    <n-grid :cols="24" :x-gap="20" :y-gap="20" class="list-row" item-responsive responsive="screen">
      <n-gi span="24 m:14">
        <n-card :bordered="false">
          <template #header>
            <div class="card-header">
              <span>学校监管列表</span>
              <n-input v-model:value="schoolSearch" placeholder="搜索学校" size="small" clearable style="width: 200px" />
            </div>
          </template>
          <n-data-table
            :columns="schoolColumns"
            :data="filteredSchools"
            :bordered="false"
            :single-line="false"
            size="small"
            :row-key="(row: GovSchoolListItem) => row.id"
            :pagination="false"
          />
        </n-card>
      </n-gi>
      <n-gi span="24 m:10">
        <n-card :bordered="false">
          <template #header>
            <div class="card-header">
              <span>实时预警</span>
              <n-button text type="primary" @click="loadAlerts">刷新</n-button>
            </div>
          </template>
          <n-spin :show="alertLoading">
            <div class="alert-list">
              <div
                v-for="(alert, idx) in alerts"
                :key="(alert.id ?? idx) + '-' + idx"
                class="alert-card"
                :class="alert.level"
              >
                <div class="alert-header">
                  <n-tag :type="alert.level === 'critical' ? 'error' : 'warning'" size="small" :bordered="false">
                    {{ alert.level === 'critical' ? '紧急' : '警告' }}
                  </n-tag>
                  <span v-if="alert.school_name" class="alert-school">{{ alert.school_name }}</span>
                </div>
                <div class="alert-title-text">{{ alert.title }}</div>
                <div class="alert-message">{{ alert.message }}</div>
                <div class="alert-time">{{ formatTime(alert.created_at) }}</div>
              </div>
              <n-empty v-if="alerts.length === 0" description="暂无预警" />
            </div>
          </n-spin>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 学校详情弹窗 -->
    <n-modal
      v-model:show="schoolDialogVisible"
      :title="selectedSchool?.name || '学校详情'"
      preset="card"
      style="width: 720px; max-width: calc(100vw - 32px);"
      :bordered="false"
    >
      <n-descriptions v-if="selectedSchool" label-placement="left" bordered :column="2" size="small">
        <n-descriptions-item label="编码">{{ selectedSchool.code || '-' }}</n-descriptions-item>
        <n-descriptions-item label="地址">{{ selectedSchool.address || '-' }}</n-descriptions-item>
        <n-descriptions-item label="联系人">{{ selectedSchool.contact_person || '-' }}</n-descriptions-item>
        <n-descriptions-item label="电话">{{ selectedSchool.contact_phone || '-' }}</n-descriptions-item>
      </n-descriptions>

      <n-divider />

      <div class="section-title">食材库存</div>
      <n-data-table
        :columns="ingredientColumns"
        :data="schoolDetail.ingredients"
        :bordered="false"
        :single-line="false"
        size="small"
        :pagination="false"
      />

      <n-divider />

      <div class="section-title">最近入库</div>
      <n-data-table
        :columns="stockInColumns"
        :data="schoolDetail.recent_stock_in"
        :bordered="false"
        :single-line="false"
        size="small"
        :pagination="false"
      />
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import {
  NButton, NCard, NDataTable, NDescriptions, NDescriptionsItem, NDivider,
  NEmpty, NGi, NGrid, NInput, NModal, NSpin, NTag,
  type DataTableColumns,
} from 'naive-ui'
import { useMessage } from 'naive-ui'
import { govApi } from '@/api'
import type { GovAlert, GovSchoolDetail, GovSchoolListItem } from '@/types'

const message = useMessage()

interface StatCard {
  icon: string
  label: string
  value: number | string
  bg: string
}

const statCards = ref<StatCard[]>([
  { icon: '🏫', label: '学校数量', value: 0, bg: '#e3f2fd' },
  { icon: '📥', label: '今日入库', value: 0, bg: '#e8f5e9' },
  { icon: '📤', label: '今日出库', value: 0, bg: '#fff3e0' },
  { icon: '⚠️', label: '低库存预警', value: 0, bg: '#ffebee' },
  { icon: '🏭', label: '供应商', value: 0, bg: '#f3e5f5' },
  { icon: '✅', label: '活跃供应商', value: 0, bg: '#e0f7fa' },
])

const trendChartRef = ref<HTMLElement | null>(null)
let chartInst: echarts.ECharts | null = null
const weeklyTrend = ref<Array<{ date: string; stock_in: number; stock_out: number }>>([])

const schoolSearch = ref('')
const schools = ref<GovSchoolListItem[]>([])
const filteredSchools = computed(() => {
  const kw = schoolSearch.value.trim().toLowerCase()
  if (!kw) return schools.value
  return schools.value.filter((s) => s.name.toLowerCase().includes(kw))
})

const alerts = ref<GovAlert[]>([])
const alertLoading = ref(false)
const alertSummary = ref([
  { type: 'low_stock', title: '库存预警', count: 0, color: '#ff453a' },
  { type: 'expiry', title: '临期预警', count: 0, color: '#ff9f0a' },
  { type: 'supplier', title: '供应商预警', count: 0, color: '#bf5af2' },
])

const schoolDialogVisible = ref(false)
const selectedSchool = ref<GovSchoolListItem | null>(null)
const schoolDetail = ref<GovSchoolDetail>({
  school: {} as GovSchoolListItem,
  ingredients: [],
  ingredient_total: 0,
  recent_stock_in: [],
  recent_inventory_checks: [],
})

const formatTime = (t: string): string => {
  if (!t) return ''
  const d = new Date(t)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

// 学校列表表格列
const schoolColumns: DataTableColumns<GovSchoolListItem> = [
  { title: '学校名称', key: 'name', minWidth: 140 },
  { title: '编码', key: 'code', width: 100 },
  { title: '食材数', key: 'ingredient_count', width: 80, align: 'center' },
  {
    title: '今日采购',
    key: 'today_purchase',
    width: 110,
    align: 'right',
    render: (row) => `¥${Number(row.today_purchase).toFixed(2)}`,
  },
  {
    title: '预警',
    key: 'low_stock_count',
    width: 80,
    align: 'center',
    render: (row) =>
      row.low_stock_count > 0
        ? h(NTag, { type: 'error', size: 'small', bordered: false }, { default: () => row.low_stock_count })
        : h('span', { style: 'color: #909399;' }, '-'),
  },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    align: 'center',
    render: (row) =>
      h(NButton, { text: true, type: 'primary', size: 'small', onClick: () => viewSchool(row) }, { default: () => '查看' }),
  },
]

// 食材库存表列
const ingredientColumns: DataTableColumns<GovSchoolDetail['ingredients'][number]> = [
  { title: '食材', key: 'name' },
  { title: '当前库存', key: 'current_stock', align: 'right' },
  { title: '安全库存', key: 'safety_stock', align: 'right' },
  {
    title: '状态',
    key: 'status',
    width: 80,
    align: 'center',
    render: (row) =>
      h(
        NTag,
        { type: row.status === '正常' ? 'success' : 'error', size: 'small', bordered: false },
        { default: () => row.status },
      ),
  },
]

// 最近入库表列
const stockInColumns: DataTableColumns<GovSchoolDetail['recent_stock_in'][number]> = [
  { title: '批次号', key: 'batch_no', width: 120 },
  { title: '食材', key: 'ingredient_name' },
  { title: '数量', key: 'quantity', align: 'right' },
  {
    title: '金额',
    key: 'total_price',
    align: 'right',
    render: (row) => `¥${Number(row.total_price).toFixed(2)}`,
  },
]

const loadDashboard = async () => {
  try {
    const data = await govApi.dashboard()
    statCards.value[0].value = Number(data.school_count) || 0
    statCards.value[1].value = Number(data.today_stock_in) || 0
    statCards.value[2].value = Number(data.today_stock_out) || 0
    statCards.value[3].value = Number(data.low_stock_alert) || 0
    statCards.value[4].value = Number(data.supplier_count) || 0
    statCards.value[5].value = Number(data.active_supplier_count) || 0
    weeklyTrend.value = data.weekly_trend || []
    await nextTick()
    initChart()
  } catch {
    message.error('加载监管看板失败')
  }
}

const loadSchools = async () => {
  try {
    const data = await govApi.schools({ skip: 0, limit: 100 })
    schools.value = data || []
  } catch {
    message.error('加载学校列表失败')
    schools.value = []
  }
}

const loadAlerts = async () => {
  alertLoading.value = true
  try {
    const res = await govApi.alerts({ skip: 0, limit: 200 })
    alerts.value = res?.items || []
    const summary: Record<string, number> = { low_stock: 0, expiry: 0, supplier: 0 }
    alerts.value.forEach((a) => {
      summary[a.type] = (summary[a.type] || 0) + 1
    })
    alertSummary.value[0].count = summary.low_stock
    alertSummary.value[1].count = summary.expiry
    alertSummary.value[2].count = summary.supplier
  } catch {
    message.error('加载预警列表失败')
    alerts.value = []
  } finally {
    alertLoading.value = false
  }
}

const viewSchool = async (row: GovSchoolListItem) => {
  selectedSchool.value = row
  schoolDialogVisible.value = true
  try {
    const data = await govApi.schoolDetail(row.id)
    if (data.school) {
      selectedSchool.value = { ...row, ...data.school }
    }
    schoolDetail.value = {
      school: data.school || ({} as GovSchoolListItem),
      ingredients: data.ingredients || [],
      ingredient_total: data.ingredient_total || 0,
      recent_stock_in: data.recent_stock_in || [],
      recent_inventory_checks: data.recent_inventory_checks || [],
    }
  } catch {
    message.error('加载学校详情失败')
    schoolDetail.value = {
      school: {} as GovSchoolListItem,
      ingredients: [],
      ingredient_total: 0,
      recent_stock_in: [],
      recent_inventory_checks: [],
    }
  }
}

const initChart = () => {
  if (!trendChartRef.value) return
  chartInst = echarts.init(trendChartRef.value)
  const dates = weeklyTrend.value.map((d) => d.date)
  const ins = weeklyTrend.value.map((d) => d.stock_in)
  const outs = weeklyTrend.value.map((d) => d.stock_out)
  chartInst.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['入库', '出库'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value' },
    series: [
      {
        name: '入库',
        type: 'line',
        smooth: true,
        data: ins,
        itemStyle: { color: '#0a84ff' },
        areaStyle: { color: 'rgba(10,132,255,0.1)' },
      },
      {
        name: '出库',
        type: 'line',
        smooth: true,
        data: outs,
        itemStyle: { color: '#30d158' },
        areaStyle: { color: 'rgba(48,209,88,0.1)' },
      },
    ],
  })
}

const handleResize = () => chartInst?.resize()

watch(trendChartRef, (el) => {
  if (el) initChart()
})

onMounted(() => {
  loadDashboard()
  loadSchools()
  loadAlerts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInst?.dispose()
  chartInst = null
})
</script>

<style scoped lang="scss">
.gov-dashboard {
  padding-bottom: 20px;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
@media (max-width: 1200px) {
  .stat-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
@media (max-width: 640px) {
  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }
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
  color: var(--n-text-color, #1d1d1f);
  margin-bottom: 4px;
}
.stat-label {
  font-size: 13px;
  color: var(--n-text-color-3, #86868b);
}
.chart-row {
  margin-bottom: 20px;
}
.chart-canvas {
  height: 320px;
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
  border-bottom: 1px solid var(--n-divider-color, #f5f5f7);
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
  color: var(--n-text-color, #1d1d1f);
  font-weight: 500;
}
.alert-count {
  font-size: 13px;
  color: var(--n-text-color-3, #86868b);
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
  background-color: var(--n-color-target, #fafafa);
  border-left: 4px solid #ff9f0a;
}
.alert-card.critical {
  background-color: var(--n-color-error, #fff5f5);
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
  color: var(--n-text-color-3, #86868b);
}
.alert-title-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--n-text-color, #1d1d1f);
  margin-bottom: 4px;
}
.alert-message {
  font-size: 13px;
  color: var(--n-text-color-2, #636366);
  margin-bottom: 6px;
}
.alert-time {
  font-size: 12px;
  color: var(--n-text-color-3, #c7c7cc);
}
.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--n-text-color, #1d1d1f);
  margin: 16px 0 12px;
}
</style>
