<template>
  <view class="page">
    <!-- 搜索栏 -->
    <view class="search-bar">
      <input
        v-model="keyword"
        class="search-input"
        placeholder="搜索食材名称/编码"
        placeholder-class="placeholder"
        confirm-type="search"
      />
    </view>

    <!-- 食材列表 -->
    <view v-if="filteredIngredients.length > 0" class="list">
      <view v-for="item in filteredIngredients" :key="item.id" class="ingredient-card">
        <view class="ingredient-header">
          <text class="ingredient-name">{{ item.name }}</text>
          <text :class="['tag', stockTagClass(item)]">{{ stockLabel(item) }}</text>
        </view>
        <view class="ingredient-meta">
          <text class="meta-item">编码: {{ item.code || '-' }}</text>
          <text class="meta-item">单位: {{ item.unit }}</text>
        </view>
        <view class="ingredient-stock">
          <view class="stock-info">
            <text class="stock-label">当前库存</text>
            <text class="stock-value">{{ item.current_stock }}</text>
          </view>
          <view class="stock-info">
            <text class="stock-label">安全库存</text>
            <text class="stock-value">{{ item.safety_stock }}</text>
          </view>
          <view v-if="item.supplier_name" class="stock-info">
            <text class="stock-label">供应商</text>
            <text class="stock-value">{{ item.supplier_name }}</text>
          </view>
        </view>
      </view>
    </view>

    <view v-else-if="!loading" class="empty">
      <view class="empty-icon">🥬</view>
      <view>暂无食材数据</view>
    </view>

    <view v-if="loading" class="loading">加载中...</view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { onShow, onPullDownRefresh } from '@dcloudio/uni-app'
import { ingredientApi } from '@/api'
import type { Ingredient } from '@/types'

const ingredients = ref<Ingredient[]>([])
const keyword = ref('')
const loading = ref(false)

const filteredIngredients = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return ingredients.value
  return ingredients.value.filter(
    (i) => i.name.toLowerCase().includes(kw) || (i.code || '').toLowerCase().includes(kw),
  )
})

const stockTagClass = (item: Ingredient): string => {
  if (Number(item.current_stock) <= 0) return 'tag-danger'
  if (Number(item.current_stock) <= Number(item.safety_stock)) return 'tag-warning'
  return 'tag-success'
}

const stockLabel = (item: Ingredient): string => {
  if (Number(item.current_stock) <= 0) return '缺货'
  if (Number(item.current_stock) <= Number(item.safety_stock)) return '低库存'
  return '正常'
}

const loadData = async () => {
  loading.value = true
  try {
    const data = await ingredientApi.list({ limit: 200 })
    ingredients.value = Array.isArray(data) ? data : []
  } catch (e) {
    uni.showToast({ title: '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

onShow(loadData)

onPullDownRefresh(() => {
  loadData().finally(() => uni.stopPullDownRefresh())
})
</script>

<style scoped lang="scss">
.page {
  min-height: 100vh;
}

.search-bar {
  padding: 16rpx;
  background: #fff;
  position: sticky;
  top: 0;
  z-index: 10;
}

.search-input {
  width: 100%;
  height: 72rpx;
  padding: 0 24rpx;
  background: #f5f5f7;
  border-radius: 36rpx;
  font-size: 28rpx;
}

.placeholder {
  color: #86868b;
}

.ingredient-card {
  margin: 16rpx;
  padding: 24rpx;
  background: #fff;
  border-radius: 16rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);
}

.ingredient-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.ingredient-name {
  font-size: 32rpx;
  font-weight: 600;
  color: #1d1d1f;
}

.ingredient-meta {
  display: flex;
  gap: 24rpx;
  margin-bottom: 16rpx;
}

.meta-item {
  font-size: 24rpx;
  color: #86868b;
}

.ingredient-stock {
  display: flex;
  gap: 32rpx;
  padding-top: 16rpx;
  border-top: 1rpx solid #e5e5ea;
}

.stock-info {
  flex: 1;
}

.stock-label {
  display: block;
  font-size: 22rpx;
  color: #86868b;
  margin-bottom: 4rpx;
}

.stock-value {
  font-size: 32rpx;
  font-weight: 600;
  color: #1d1d1f;
}
</style>
