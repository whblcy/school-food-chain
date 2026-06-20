<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background: #e3f2fd; color: #1976d2;">
            <el-icon :size="24"><Goods /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.ingredientCount }}</div>
            <div class="stat-label">食材种类</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background: #e8f5e9; color: #388e3c;">
            <el-icon :size="24"><Money /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">¥{{ stats.totalValue?.toFixed(2) }}</div>
            <div class="stat-label">库存总值</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background: #fff3e0; color: #f57c00;">
            <el-icon :size="24"><Warning /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.lowStockCount }}</div>
            <div class="stat-label">低库存预警</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background: #fce4ec; color: #c2185b;">
            <el-icon :size="24"><OfficeBuilding /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.supplierCount }}</div>
            <div class="stat-label">供应商</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>月度收支趋势</span>
          </template>
          <div ref="trendChart" style="height: 300px;"></div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>分类占比</span>
          </template>
          <div ref="categoryChart" style="height: 300px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 低库存预警 -->
    <el-card style="margin-top: 20px;">
      <template #header>
        <span>低库存预警</span>
      </template>
      <el-table :data="lowStockItems" style="width: 100%">
        <el-table-column prop="name" label="食材名称" />
        <el-table-column prop="current" label="当前库存" />
        <el-table-column prop="safety" label="安全库存" />
        <el-table-column label="状态">
          <template #default="{ row }">
            <el-tag type="danger">库存不足</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import { Goods, Money, Warning, OfficeBuilding } from '@element-plus/icons-vue'
import { getStockSummary, getLowStock, getYearlyTrend } from '../api'

const stats = ref({})
const lowStockItems = ref([])
const trendChart = ref()
const categoryChart = ref()

const loadData = async () => {
  try {
    const [summaryRes, lowStockRes, trendRes] = await Promise.all([
      getStockSummary(),
      getLowStock(),
      getYearlyTrend({ year: new Date().getFullYear() })
    ])
    
    stats.value = {
      ingredientCount: summaryRes.data.reduce((sum, item) => sum + item.count, 0),
      totalValue: summaryRes.data.reduce((sum, item) => sum + item.total_stock, 0),
      lowStockCount: lowStockRes.data.length,
      supplierCount: 0
    }
    lowStockItems.value = lowStockRes.data
    
    initTrendChart(trendRes.data)
    initCategoryChart(summaryRes.data)
  } catch (error) {
    console.error('Load dashboard data failed:', error)
  }
}

const initTrendChart = (data) => {
  const chart = echarts.init(trendChart.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['入库', '出库'] },
    xAxis: { type: 'category', data: data.map(d => `${d.month}月`) },
    yAxis: { type: 'value' },
    series: [
      { name: '入库', type: 'line', data: data.map(d => d.in_amount), smooth: true },
      { name: '出库', type: 'line', data: data.map(d => d.out_amount), smooth: true }
    ]
  })
}

const initCategoryChart = (data) => {
  const chart = echarts.init(categoryChart.value)
  chart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: data.map(d => ({ name: d.category, value: d.total_stock }))
    }]
  })
}

onMounted(loadData)
</script>

<style scoped>
.stat-card {
  display: flex;
  align-items: center;
  padding: 10px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1d1d1f;
}

.stat-label {
  font-size: 13px;
  color: #86868b;
  margin-top: 4px;
}
</style>
