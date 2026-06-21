<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <div class="stat-grid">
      <n-card v-for="card in statCards" :key="card.label" class="stat-card" :bordered="false">
        <div class="stat-card-inner">
          <div class="stat-icon" :style="{ background: card.bg, color: card.color }">
            <span>{{ card.icon }}</span>
          </div>
          <div class="stat-info">
            <div class="stat-value">
              <n-skeleton v-if="loading" text :width="80" />
              <template v-else>{{ card.value }}</template>
            </div>
            <div class="stat-label">{{ card.label }}</div>
          </div>
        </div>
      </n-card>
    </div>

    <!-- 图表区域 -->
    <n-grid :cols="2" :x-gap="16" :y-gap="16" responsive="screen" item-responsive style="margin-top: 16px;">
      <n-grid-item span="2 m:1">
        <n-card title="月度收支趋势" :bordered="false">
          <div ref="trendChartRef" class="chart-box">
            <n-skeleton v-if="loading" text :repeat="6" />
          </div>
        </n-card>
      </n-grid-item>
      <n-grid-item span="2 m:1">
        <n-card title="分类占比" :bordered="false">
          <div ref="categoryChartRef" class="chart-box">
            <n-skeleton v-if="loading" text :repeat="6" />
          </div>
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- 低库存预警 -->
    <n-card title="低库存预警" :bordered="false" style="margin-top: 16px;">
      <n-data-table
        :columns="lowStockColumns"
        :data="lowStockItems"
        :loading="loading"
        :bordered="false"
        :single-line="false"
        size="small"
      />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, h } from 'vue'
import * as echarts from 'echarts'
import { NTag, type DataTableColumns } from 'naive-ui'
import { reportApi, financeApi, supplierApi } from '@/api'
import type { LowStockItem, StockSummaryItem, YearlyTrendItem } from '@/types'

const loading = ref(true)

interface StatCard {
  label: string
  value: string | number
  icon: string
  bg: string
  color: string
}

const statCards = ref<StatCard[]>([
  { label: '食材种类', value: 0, icon: '🥬', bg: '#e3f2fd', color: '#1976d2' },
  { label: '库存总值', value: '¥0.00', icon: '💰', bg: '#e8f5e9', color: '#388e3c' },
  { label: '低库存预警', value: 0, icon: '⚠️', bg: '#fff3e0', color: '#f57c00' },
  { label: '供应商', value: 0, icon: '🏭', bg: '#fce4ec', color: '#c2185b' },
])

const lowStockItems = ref<LowStockItem[]>([])
const trendChartRef = ref<HTMLElement | null>(null)
const categoryChartRef = ref<HTMLElement | null>(null)
let trendChartInst: echarts.ECharts | null = null
let categoryChartInst: echarts.ECharts | null = null

const lowStockColumns: DataTableColumns<LowStockItem> = [
  { title: '食材名称', key: 'name' },
  { title: '当前库存', key: 'current_stock' },
  { title: '安全库存', key: 'safety_stock' },
  {
    title: '状态',
    key: 'status',
    render: () => h(NTag, { type: 'error', size: 'small' }, { default: () => '库存不足' }),
  },
]

const formatMoney = (n: number) => {
  const num = Number(n) || 0
  if (Math.abs(num) >= 10000) return `¥${(num / 10000).toFixed(2)}万`
  return `¥${num.toFixed(2)}`
}

const loadData = async () => {
  loading.value = true
  try {
    const [summary, lowStock, trend, value, suppliers] = await Promise.all([
      reportApi.stockSummary(),
      reportApi.lowStock(),
      financeApi.yearlyTrend(new Date().getFullYear()),
      reportApi.inventoryValue(),
      supplierApi.list(),
    ])

    const ingredientCount = summary.reduce((sum: number, item: StockSummaryItem) => sum + item.count, 0)
    statCards.value[0].value = ingredientCount
    statCards.value[1].value = formatMoney(value.total_value)
    statCards.value[2].value = lowStock.length
    statCards.value[3].value = suppliers.length
    lowStockItems.value = lowStock

    await nextTick()
    initTrendChart(trend)
    initCategoryChart(summary)
  } catch {
    // 错误静默处理，骨架屏会消失
  } finally {
    loading.value = false
  }
}

const initTrendChart = (data: YearlyTrendItem[]) => {
  if (!trendChartRef.value) return
  trendChartInst = echarts.init(trendChartRef.value)
  trendChartInst.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['入库', '出库'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: data.map((d) => `${d.month}月`) },
    yAxis: { type: 'value' },
    series: [
      {
        name: '入库',
        type: 'line',
        data: data.map((d) => d.in_amount),
        smooth: true,
        areaStyle: { color: 'rgba(24,160,88,0.15)' },
        lineStyle: { color: '#18a058', width: 2 },
        itemStyle: { color: '#18a058' },
      },
      {
        name: '出库',
        type: 'line',
        data: data.map((d) => d.out_amount),
        smooth: true,
        areaStyle: { color: 'rgba(208,48,80,0.15)' },
        lineStyle: { color: '#d03050', width: 2 },
        itemStyle: { color: '#d03050' },
      },
    ],
  })
}

const initCategoryChart = (data: StockSummaryItem[]) => {
  if (!categoryChartRef.value) return
  categoryChartInst = echarts.init(categoryChartRef.value)
  categoryChartInst.setOption({
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        data: data.map((d) => ({ name: d.category || '未分类', value: d.total_stock })),
        color: ['#18a058', '#2080f0', '#f0a020', '#d03050', '#909399'],
      },
    ],
  })
}

const handleResize = () => {
  trendChartInst?.resize()
  categoryChartInst?.resize()
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChartInst?.dispose()
  categoryChartInst?.dispose()
})
</script>

<style scoped>
.stat-card {
  border-radius: 12px;
}

.stat-card-inner {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  flex-shrink: 0;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: var(--n-text-color-3, #86868b);
  margin-top: 4px;
}

.chart-box {
  height: 300px;
}

@media (max-width: 768px) {
  .stat-icon {
    width: 44px;
    height: 44px;
    font-size: 22px;
  }
  .stat-value {
    font-size: 20px;
  }
  .chart-box {
    height: 240px;
  }
}
</style>
