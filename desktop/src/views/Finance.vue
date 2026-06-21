<template>
  <div class="finance-page">
    <!-- 统计卡片 -->
    <div class="stat-grid">
      <n-card v-for="card in statCards" :key="card.label" class="stat-card" :bordered="false">
        <div class="stat-label">{{ card.label }}</div>
        <div class="stat-value" :class="card.tone">
          <n-skeleton v-if="loading" text :width="100" />
          <template v-else>{{ card.value }}</template>
        </div>
      </n-card>
    </div>

    <!-- 月份选择 -->
    <n-card :bordered="false" class="filter-card">
      <div class="filter-bar">
        <span class="filter-label">统计月份：</span>
        <n-date-picker v-model:value="selectedMonth" type="month" style="width: 160px;" @update:value="loadAll" />
        <span class="filter-label" style="margin-left: 20px;">趋势年份：</span>
        <n-radio-group v-model:value="trendYear" size="small" @update:value="loadYearlyTrend">
          <n-radio-button v-for="y in yearOptions" :key="y" :value="y" :label="String(y)" />
        </n-radio-group>
      </div>
    </n-card>

    <!-- 图表区域 -->
    <n-grid :cols="24" :x-gap="16" :y-gap="16" responsive="screen" item-responsive style="margin-top: 16px;">
      <n-grid-item span="24 m:16">
        <n-card :bordered="false">
          <template #header>
            <span>月度收支趋势（{{ trendYear }}年）</span>
          </template>
          <div ref="trendChartRef" class="chart-box">
            <n-skeleton v-if="loading" text :repeat="8" />
          </div>
        </n-card>
      </n-grid-item>
      <n-grid-item span="24 m:8">
        <n-card :bordered="false">
          <template #header>
            <span>品类支出占比</span>
          </template>
          <div ref="pieChartRef" class="chart-box">
            <n-skeleton v-if="loading" text :repeat="8" />
          </div>
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- 入库明细 -->
    <n-card :bordered="false" style="margin-top: 16px;">
      <template #header>
        <span>本月入库明细</span>
      </template>
      <n-data-table
        :columns="columns"
        :data="detailList"
        :loading="loading"
        :bordered="false"
        :single-line="false"
        size="small"
        remote
        :pagination="pagination"
        @update:page="handlePageChange"
      />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useMessage, type DataTableColumns, type PaginationProps } from 'naive-ui'
import { financeApi, financeApiExt, supplierApi, stockApi } from '@/api'
import type { StockIn, CategoryBreakdownItem, YearlyTrendItem } from '@/types'

const loading = ref(false)
const monthTotalIn = ref(0)
const monthTotalOut = ref(0)
const monthBalance = ref(0)
const supplierCount = ref(0)

const now = new Date()
const currentYear = now.getFullYear()
const currentMonth = now.getMonth() + 1
const selectedMonth = ref(new Date(currentYear, currentMonth - 1, 1).getTime())
const trendYear = ref(currentYear)
const yearOptions = ref([currentYear - 2, currentYear - 1, currentYear])

const detailList = ref<StockIn[]>([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const trendChartRef = ref<HTMLElement | null>(null)
const pieChartRef = ref<HTMLElement | null>(null)
let trendChartInst: echarts.ECharts | null = null
let pieChartInst: echarts.ECharts | null = null

const statCards = computed(() => [
  { label: '本月采购总额', value: formatMoney(monthTotalIn.value), tone: '' },
  { label: '本月出库总额', value: formatMoney(monthTotalOut.value), tone: '' },
  { label: '本月结余', value: formatMoney(monthBalance.value), tone: monthBalance.value >= 0 ? 'positive' : 'negative' },
  { label: '供应商数量', value: supplierCount.value, tone: '' },
])

const pagination = computed<PaginationProps>(() => ({
  page: page.value,
  pageSize: pageSize.value,
  itemCount: total.value,
  prefix: ({ itemCount }) => `共 ${itemCount} 条`,
}))

const handlePageChange = (p: number) => {
  page.value = p
  loadStockInDetails()
}

const formatMoney = (n: number) => {
  const num = Number(n) || 0
  if (Math.abs(num) >= 10000) return `¥${(num / 10000).toFixed(2)}万`
  return `¥${num.toFixed(2)}`
}

const formatDate = (val: string | null) => {
  if (!val) return '-'
  return new Date(val).toLocaleString('zh-CN')
}

const columns: DataTableColumns<StockIn> = [
  { title: '批次号', key: 'batch_no', width: 160 },
  { title: '食材名称', key: 'ingredient_name' },
  {
    title: '供应商',
    key: 'supplier_name',
    render: (row) => row.supplier_name || '-',
  },
  { title: '数量', key: 'quantity', align: 'right' },
  {
    title: '单价',
    key: 'unit_price',
    align: 'right',
    render: (row) => `¥${Number(row.unit_price).toFixed(2)}`,
  },
  {
    title: '金额',
    key: 'total_price',
    align: 'right',
    render: (row) => `¥${Number(row.total_price).toFixed(2)}`,
  },
  {
    title: '入库时间',
    key: 'created_at',
    width: 180,
    render: (row) => formatDate(row.created_at),
  },
]

const message = useMessage()

const loadAll = async () => {
  await Promise.all([loadMonthlySummary(), loadCategoryBreakdown(), loadStockInDetails()])
}

const loadMonthlySummary = async () => {
  try {
    const d = new Date(selectedMonth.value)
    const data = await financeApi.monthlySummary(d.getFullYear(), d.getMonth() + 1)
    monthTotalIn.value = Number(data.total_in) || 0
    monthTotalOut.value = Number(data.total_out) || 0
    monthBalance.value = Number(data.balance) || 0
  } catch {
    message.error('加载财务汇总失败')
  }
}

const loadYearlyTrend = async () => {
  try {
    const data: YearlyTrendItem[] = await financeApi.yearlyTrend(trendYear.value)
    const months = data.map((d) => `${d.month}月`)
    const inAmounts = data.map((d) => Number(d.in_amount) || 0)
    const outAmounts = data.map((d) => Number(d.out_amount) || 0)
    await nextTick()
    initTrendChart(months, inAmounts, outAmounts)
  } catch {
    message.error('加载趋势数据失败')
  }
}

const loadCategoryBreakdown = async () => {
  try {
    const d = new Date(selectedMonth.value)
    const data: CategoryBreakdownItem[] = await financeApiExt.categoryBreakdown(d.getFullYear(), d.getMonth() + 1)
    await nextTick()
    initPieChart(data.map((item) => ({ name: item.category || '未分类', value: Number(item.amount) || 0 })))
  } catch {
    initPieChart([])
  }
}

const loadStockInDetails = async () => {
  loading.value = true
  try {
    const skip = (page.value - 1) * pageSize.value
    const data = await stockApi.in.list({ skip, limit: pageSize.value })
    detailList.value = data
    total.value =
      data.length < pageSize.value
        ? (page.value - 1) * pageSize.value + data.length
        : (page.value + 1) * pageSize.value
  } catch {
    message.error('加载入库明细失败')
    detailList.value = []
  } finally {
    loading.value = false
  }
}

const loadSupplierCount = async () => {
  try {
    const data = await supplierApi.list({ skip: 0, limit: 1 })
    supplierCount.value = data.length
  } catch {
    supplierCount.value = 0
  }
}

const initTrendChart = (months: string[], inAmounts: number[], outAmounts: number[]) => {
  if (!trendChartRef.value) return
  trendChartInst = echarts.init(trendChartRef.value)
  trendChartInst.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['采购入库', '出库消耗'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: months, boundaryGap: false },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => (v >= 10000 ? `${v / 10000}万` : String(v)) } },
    series: [
      {
        name: '采购入库',
        data: inAmounts,
        type: 'line',
        smooth: true,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(24,160,88,0.3)' },
            { offset: 1, color: 'rgba(24,160,88,0.05)' },
          ]),
        },
        lineStyle: { color: '#18a058', width: 2 },
        itemStyle: { color: '#18a058' },
      },
      {
        name: '出库消耗',
        data: outAmounts,
        type: 'line',
        smooth: true,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(208,48,80,0.3)' },
            { offset: 1, color: 'rgba(208,48,80,0.05)' },
          ]),
        },
        lineStyle: { color: '#d03050', width: 2 },
        itemStyle: { color: '#d03050' },
      },
    ],
  })
}

const initPieChart = (categories: Array<{ name: string; value: number }>) => {
  if (!pieChartRef.value) return
  pieChartInst = echarts.init(pieChartRef.value)
  pieChartInst.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    legend: { orient: 'vertical', right: 10, top: 'center' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
        data: categories,
        color: ['#18a058', '#2080f0', '#f0a020', '#d03050', '#909399'],
      },
    ],
  })
}

const handleResize = () => {
  trendChartInst?.resize()
  pieChartInst?.resize()
}

onMounted(() => {
  loadAll()
  loadYearlyTrend()
  loadSupplierCount()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChartInst?.dispose()
  pieChartInst?.dispose()
})
</script>

<style scoped>
.finance-page {
  padding-bottom: 20px;
}

.stat-card {
  text-align: center;
  border-radius: 12px;
}

.stat-label {
  color: var(--n-text-color-3, #86868b);
  font-size: 14px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  margin-bottom: 8px;
}

.stat-value.positive {
  color: #18a058;
}

.stat-value.negative {
  color: #d03050;
}

.filter-card {
  margin-top: 16px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-label {
  font-size: 14px;
  color: var(--n-text-color-2, #606266);
}

.chart-box {
  height: 320px;
}

@media (max-width: 768px) {
  .chart-box {
    height: 240px;
  }
  .stat-value {
    font-size: 22px;
  }
}
</style>
