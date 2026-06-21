<template>
  <view class="page">
    <!-- 未登录态 -->
    <view v-if="!auth.isLoggedIn" class="empty">
      <view class="empty-icon">🔒</view>
      <view>请先登录</view>
      <button class="btn-primary" style="margin-top: 32rpx;" @tap="goLogin">去登录</button>
    </view>

    <!-- 已登录态 -->
    <view v-else>
      <!-- 欢迎区 -->
      <view class="welcome-card">
        <view class="welcome-text">
          <view class="welcome-title">{{ greeting }}，{{ auth.user?.real_name || auth.user?.username || '管理员' }}</view>
          <view class="welcome-date">{{ today }}</view>
        </view>
        <view class="welcome-avatar">{{ avatarText }}</view>
      </view>

      <!-- 统计卡片 -->
      <view class="stat-grid">
        <view v-for="card in statCards" :key="card.label" class="stat-card">
          <view class="stat-card-icon" :style="{ background: card.bg }">{{ card.icon }}</view>
          <view class="stat-card-value">{{ card.value }}</view>
          <view class="stat-card-label">{{ card.label }}</view>
        </view>
      </view>

      <!-- 低库存预警 -->
      <view class="section">
        <view class="section-header">
          <text class="section-title">低库存预警</text>
          <text v-if="lowStock.length > 0" class="tag tag-danger">{{ lowStock.length }}</text>
        </view>
        <view v-if="lowStock.length === 0" class="empty">
          <view class="empty-icon">✅</view>
          <view>库存充足</view>
        </view>
        <view v-else class="list">
          <view v-for="item in lowStock" :key="item.id" class="list-item">
            <view class="list-item-content">
              <text class="list-item-title">{{ item.name }}</text>
              <text class="list-item-subtitle">当前: {{ item.current_stock }}{{ item.unit }} / 安全: {{ item.safety_stock }}{{ item.unit }}</text>
            </view>
            <text class="tag tag-danger">预警</text>
          </view>
        </view>
      </view>

      <!-- 最近入库 -->
      <view class="section">
        <view class="section-header">
          <text class="section-title">最近入库</text>
        </view>
        <view v-if="recentStockIn.length === 0" class="empty">
          <view class="empty-icon">📋</view>
          <view>暂无记录</view>
        </view>
        <view v-else class="list">
          <view v-for="item in recentStockIn" :key="item.id" class="list-item">
            <view class="list-item-content">
              <text class="list-item-title">{{ item.ingredient_name || `食材#${item.ingredient_id}` }}</text>
              <text class="list-item-subtitle">{{ formatDate(item.created_at) }} · {{ item.batch_no }}</text>
            </view>
            <text class="list-item-amount">+{{ item.quantity }}</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { onShow, onPullDownRefresh } from '@dcloudio/uni-app'
import { useAuthStore } from '@/stores/auth'
import { ingredientApi, supplierApi, stockApi } from '@/api'
import type { Ingredient, StockIn } from '@/types'

const auth = useAuthStore()

const statCards = ref([
  { icon: '🥬', label: '食材种类', value: 0, bg: '#e8f5e9' },
  { icon: '📦', label: '库存总量', value: 0, bg: '#e3f2fd' },
  { icon: '🏭', label: '供应商', value: 0, bg: '#f3e5f5' },
  { icon: '⚠️', label: '预警', value: 0, bg: '#ffebee' },
])

const lowStock = ref<Ingredient[]>([])
const recentStockIn = ref<StockIn[]>([])

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '凌晨好'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const today = computed(() => {
  const now = new Date()
  const weekDays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 ${weekDays[now.getDay()]}`
})

const avatarText = computed(() => {
  const name = auth.user?.real_name || auth.user?.username || '?'
  return name.charAt(0).toUpperCase()
})

const formatDate = (val: string): string => {
  if (!val) return ''
  const d = new Date(val)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

const loadData = async () => {
  if (!auth.isLoggedIn) return

  try {
    const [ingredients, suppliers, stockIn] = await Promise.all([
      ingredientApi.list({ limit: 200 }),
      supplierApi.list({ limit: 100 }),
      stockApi.in.list({ limit: 10 }),
    ])

    const items = Array.isArray(ingredients) ? ingredients : []
    const totalStock = items.reduce((sum, i) => sum + Number(i.current_stock || 0), 0)
    const lowItems = items.filter((i) => Number(i.current_stock || 0) <= Number(i.safety_stock || 0))

    statCards.value[0].value = items.length
    statCards.value[1].value = Math.round(totalStock)
    statCards.value[2].value = Array.isArray(suppliers) ? suppliers.length : 0
    statCards.value[3].value = lowItems.length

    lowStock.value = lowItems.slice(0, 5)
    recentStockIn.value = Array.isArray(stockIn) ? stockIn.slice(0, 5) : []
  } catch (e) {
    uni.showToast({ title: '加载失败', icon: 'none' })
  }
}

const goLogin = () => {
  uni.navigateTo({ url: '/pages/login/login' })
}

onShow(() => {
  if (auth.isLoggedIn) loadData()
})

onPullDownRefresh(() => {
  loadData().finally(() => uni.stopPullDownRefresh())
})
</script>

<style scoped lang="scss">
.page {
  min-height: 100vh;
}

.welcome-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 16rpx;
  padding: 32rpx;
  background: linear-gradient(135deg, #18a058 0%, #0c7a43 100%);
  border-radius: 20rpx;
  color: #fff;
}

.welcome-title {
  font-size: 36rpx;
  font-weight: 700;
  margin-bottom: 8rpx;
}

.welcome-date {
  font-size: 24rpx;
  opacity: 0.9;
}

.welcome-avatar {
  width: 96rpx;
  height: 96rpx;
  background: rgba(255, 255, 255, 0.25);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
  font-weight: 700;
}

.section {
  margin: 16rpx;
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx;
  border-bottom: 1rpx solid #e5e5ea;
}

.section-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #1d1d1f;
}

.list-item {
  display: flex;
  align-items: center;
  padding: 24rpx;
  border-bottom: 1rpx solid #e5e5ea;

  &:last-child {
    border-bottom: none;
  }
}

.list-item-content {
  flex: 1;
}

.list-item-title {
  display: block;
  font-size: 28rpx;
  color: #1d1d1f;
  margin-bottom: 4rpx;
}

.list-item-subtitle {
  font-size: 24rpx;
  color: #86868b;
}

.list-item-amount {
  font-size: 32rpx;
  font-weight: 600;
  color: #30d158;
}
</style>
