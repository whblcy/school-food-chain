<template>
  <div class="finance-page">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">本月采购总额</div>
          <div class="stat-value">¥{{ formatNumber(monthTotal) }}</div>
          <div class="stat-trend" :class="monthTrend >= 0 ? 'up' : 'down'">
            <el-icon><ArrowUp v-if="monthTrend >= 0" /><ArrowDown v-else /></el-icon>
            {{ Math.abs(monthTrend).toFixed(1) }}% 环比
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">本月入库笔数</div>
          <div class="stat-value">{{ monthCount }}</div>
          <div class="stat-trend" :class="countTrend >= 0 ? 'up' : 'down'">
            <el-icon><ArrowUp v-if="countTrend >= 0" /><ArrowDown v-else /></el-icon>
            {{ Math.abs(countTrend).toFixed(1) }}% 环比
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">平均单价</div>
          <div class="stat-value">¥{{ formatNumber(avgPrice) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">供应商数量</div>
          <div class="stat-value">{{ supplierCount }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>月度采购趋势</span>
              <el-radio-group v-model="trendYear" size="small" @change="loadYearlyTrend">
                <el-radio-button :label="2024">2024</el-radio-button>
                <el-radio-button :label="2025">2025</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="trendChart" style="height: 320px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>品类支出占比</span>
            </div>
          </template>
          <div ref="pieChart" style="height: 320px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 明细表格 -->
    <el-card class="detail-card">
      <template #header>
        <div class="card-header">
          <span>采购明细</span>
          <div class="header-actions">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              size="small"
              @change="loadMonthlySummary"
            />
            <el-button type="primary" size="small" @click="exportData">
              <el-icon><Download /></el-icon>导出
            </el-button>
          </div>
        </div>
      </template>
      <el-table :data="detailList" v-loading="loading" stripe>
        <el-table-column prop="ingredient_name" label="食材名称" />
        <el-table-column prop="category" label="品类" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="supplier_name" label="供应商" />
        <el-table-column prop="quantity" label="数量" width="100" align="right" />
        <el-table-column prop="unit_price" label="单价" width="120" align="right">
          <template #default="{ row }">
            ¥{{ row.unit_price.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="total_amount" label="金额" width="120" align="right">
          <template #default="{ row }">
            <span class="amount">¥{{ row.total_amount.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="stock_in_date" label="入库日期" width="120" />
      </el-table>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        class="pagination"
        @current-change="loadMonthlySummary"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowUp, ArrowDown, Download } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getMonthlySummary, getYearlyTrend } from '../api'

const loading = ref(false)
const monthTotal = ref(0)
const monthCount = ref(0)
const avgPrice = ref(0)
const supplierCount = ref(0)
const monthTrend = ref(0)
const countTrend = ref(0)
const trendYear = ref(2025)
const dateRange = ref([])
const detailList = ref([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const trendChart = ref(null)
const pieChart = ref(null)
let trendChartInst = null
let pieChartInst = null

const formatNumber = (n) => {
  if (n >= 10000) return (n / 10000).toFixed(2) + '万'
  return n.toFixed(2)
}

const loadMonthlySummary = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (dateRange.value?.length === 2) {
      params.start_date = dateRange.value[0].toISOString().split('T')[0]
      params.end_date = dateRange.value[1].toISOString().split('T')[0]
    }
    const res = await getMonthlySummary(params)
    const data = res.data
    monthTotal.value = data.total_amount || 0
    monthCount.value = data.total_count || 0
    avgPrice.value = data.avg_price || 0
    supplierCount.value = data.supplier_count || 0
    monthTrend.value = data.month_trend || 0
    countTrend.value = data.count_trend || 0
    detailList.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    ElMessage.error('加载财务数据失败')
  } finally {
    loading.value = false
  }
}

const loadYearlyTrend = async () => {
  try {
    const res = await getYearlyTrend({ year: trendYear.value })
    const data = res.data
    initTrendChart(data.months || [], data.amounts || [])
    initPieChart(data.categories || [])
  } catch (e) {
    // 使用模拟数据
    initTrendChart(
      ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'],
      [12000, 15000, 18000, 14000, 22000, 25000, 20000, 18000, 26000, 28000, 30000, 32000]
    )
    initPieChart([
      { name: '蔬菜', value: 35000 },
      { name: '肉类', value: 52000 },
      { name: '粮油', value: 28000 },
      { name: '调味品', value: 12000 },
      { name: '豆制品', value: 15000 }
    ])
  }
}

const initTrendChart = (months, amounts) => {
  if (!trendChart.value) return
  trendChartInst = echarts.init(trendChart.value)
  trendChartInst.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: months, boundaryGap: false },
    yAxis: { type: 'value', axisLabel: { formatter: v => v >= 10000 ? (v/10000)+'万' : v } },
    series: [{
      data: amounts,
      type: 'line',
      smooth: true,
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64,158,255,0.3)' },
          { offset: 1, color: 'rgba(64,158,255,0.05)' }
        ])
      },
      lineStyle: { color: '#409EFF', width: 2 },
      itemStyle: { color: '#409EFF' }
    }]
  })
}

const initPieChart = (categories) => {
  if (!pieChart.value) return
  pieChartInst = echarts.init(pieChart.value)
  pieChartInst.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    legend: { orient: 'vertical', right: 10, top: 'center' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['35%', '50%'],
      avoidLabelOverlap: false,
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
      data: categories,
      color: ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399']
    }]
  })
}

const exportData = () => {
  ElMessage.success('导出功能开发中')
}

onMounted(() => {
  loadMonthlySummary()
  nextTick(() => loadYearlyTrend())
})

onUnmounted(() => {
  trendChartInst?.dispose()
  pieChartInst?.dispose()
})
</script>

<style scoped>
.finance-page {
  padding-bottom: 20px;
}
.stat-cards {
  margin-bottom: 20px;
}
.stat-card {
  text-align: center;
  padding: 10px 0;
}
.stat-label {
  color: #909399;
  font-size: 14px;
  margin-bottom: 8px;
}
.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 8px;
}
.stat-trend {
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.stat-trend.up { color: #67C23A; }
.stat-trend.down { color: #F56C6C; }
.chart-row {
  margin-bottom: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
.detail-card {
  margin-top: 0;
}
.amount {
  color: #F56C6C;
  font-weight: 600;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
