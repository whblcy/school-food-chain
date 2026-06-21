<template>
  <view class="page">
    <!-- Tab 切换 -->
    <view class="tabs">
      <view
        :class="['tab-item', { active: activeTab === 'in' }]"
        @tap="activeTab = 'in'"
      >入库记录</view>
      <view
        :class="['tab-item', { active: activeTab === 'out' }]"
        @tap="activeTab = 'out'"
      >出库记录</view>
    </view>

    <!-- 入库列表 -->
    <view v-if="activeTab === 'in'">
      <view v-if="stockInList.length > 0" class="list">
        <view v-for="item in stockInList" :key="item.id" class="stock-card">
          <view class="stock-header">
            <text class="stock-name">{{ item.ingredient_name || `食材#${item.ingredient_id}` }}</text>
            <text class="tag tag-info">入库</text>
          </view>
          <view class="stock-meta">
            <text class="meta-item">批次: {{ item.batch_no }}</text>
            <text class="meta-item">{{ formatDate(item.created_at) }}</text>
          </view>
          <view class="stock-footer">
            <view class="stock-stat">
              <text class="stat-label">数量</text>
              <text class="stat-value">+{{ item.quantity }}</text>
            </view>
            <view class="stock-stat">
              <text class="stat-label">单价</text>
              <text class="stat-value">¥{{ Number(item.unit_price).toFixed(2) }}</text>
            </view>
            <view class="stock-stat">
              <text class="stat-label">总价</text>
              <text class="stat-value">¥{{ Number(item.total_price).toFixed(2) }}</text>
            </view>
          </view>
          <view v-if="item.supplier_name" class="stock-supplier">
            供应商: {{ item.supplier_name }}
          </view>
        </view>
      </view>
      <view v-else-if="!loading" class="empty">
        <view class="empty-icon">📥</view>
        <view>暂无入库记录</view>
      </view>
    </view>

    <!-- 出库列表 -->
    <view v-else>
      <view v-if="stockOutList.length > 0" class="list">
        <view v-for="item in stockOutList" :key="item.id" class="stock-card">
          <view class="stock-header">
            <text class="stock-name">{{ item.ingredient_name || `食材#${item.ingredient_id}` }}</text>
            <text class="tag tag-warning">出库</text>
          </view>
          <view class="stock-meta">
            <text class="meta-item">{{ formatDate(item.created_at) }}</text>
            <text v-if="item.department" class="meta-item">{{ item.department }}</text>
          </view>
          <view class="stock-footer">
            <view class="stock-stat">
              <text class="stat-label">数量</text>
              <text class="stat-value">-{{ item.quantity }}</text>
            </view>
            <view class="stock-stat">
              <text class="stat-label">单价</text>
              <text class="stat-value">¥{{ Number(item.unit_price).toFixed(2) }}</text>
            </view>
            <view class="stock-stat">
              <text class="stat-label">总价</text>
              <text class="stat-value">¥{{ Number(item.total_price).toFixed(2) }}</text>
            </view>
          </view>
          <view v-if="item.purpose" class="stock-supplier">
            用途: {{ item.purpose }}
          </view>
        </view>
      </view>
      <view v-else-if="!loading" class="empty">
        <view class="empty-icon">📤</view>
        <view>暂无出库记录</view>
      </view>
    </view>

    <view v-if="loading" class="loading">加载中...</view>
  </view>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { onShow, onPullDownRefresh } from '@dcloudio/uni-app'
import { stockApi } from '@/api'
import type { StockIn, StockOut } from '@/types'

const activeTab = ref<'in' | 'out'>('in')
const stockInList = ref<StockIn[]>([])
const stockOutList = ref<StockOut[]>([])
const loading = ref(false)

const formatDate = (val: string): string => {
  if (!val) return ''
  const d = new Date(val)
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

const loadStockIn = async () => {
  loading.value = true
  try {
    const data = await stockApi.in.list({ limit: 50 })
    stockInList.value = Array.isArray(data) ? data : []
  } catch (e) {
    uni.showToast({ title: '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

const loadStockOut = async () => {
  loading.value = true
  try {
    const data = await stockApi.out.list({ limit: 50 })
    stockOutList.value = Array.isArray(data) ? data : []
  } catch (e) {
    uni.showToast({ title: '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

watch(activeTab, (tab) => {
  if (tab === 'in' && stockInList.value.length === 0) loadStockIn()
  if (tab === 'out' && stockOutList.value.length === 0) loadStockOut()
})

onShow(() => {
  if (activeTab.value === 'in') loadStockIn()
  else loadStockOut()
})

onPullDownRefresh(() => {
  const promise = activeTab.value === 'in' ? loadStockIn() : loadStockOut()
  promise.finally(() => uni.stopPullDownRefresh())
})
</script>

<style scoped lang="scss">
.page {
  min-height: 100vh;
}

.tabs {
  display: flex;
  background: #fff;
  position: sticky;
  top: 0;
  z-index: 10;
  border-bottom: 1rpx solid #e5e5ea;
}

.tab-item {
  flex: 1;
  text-align: center;
  padding: 24rpx 0;
  font-size: 28rpx;
  color: #86868b;
  position: relative;

  &.active {
    color: #18a058;
    font-weight: 600;

    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 50%;
      transform: translateX(-50%);
      width: 48rpx;
      height: 4rpx;
      background: #18a058;
      border-radius: 2rpx;
    }
  }
}

.stock-card {
  margin: 16rpx;
  padding: 24rpx;
  background: #fff;
  border-radius: 16rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);
}

.stock-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.stock-name {
  font-size: 32rpx;
  font-weight: 600;
  color: #1d1d1f;
}

.stock-meta {
  display: flex;
  gap: 24rpx;
  margin-bottom: 16rpx;
}

.meta-item {
  font-size: 24rpx;
  color: #86868b;
}

.stock-footer {
  display: flex;
  gap: 32rpx;
  padding-top: 16rpx;
  border-top: 1rpx solid #e5e5ea;
}

.stock-stat {
  flex: 1;
}

.stat-label {
  display: block;
  font-size: 22rpx;
  color: #86868b;
  margin-bottom: 4rpx;
}

.stat-value {
  font-size: 30rpx;
  font-weight: 600;
  color: #1d1d1f;
}

.stock-supplier {
  margin-top: 12rpx;
  font-size: 24rpx;
  color: #636366;
}
</style>
