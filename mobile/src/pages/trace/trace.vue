<template>
  <view class="page">
    <!-- 搜索区 -->
    <view class="search-card">
      <view class="search-title">追溯码查询</view>
      <view class="search-input-wrap">
        <input
          v-model="traceCode"
          class="search-input"
          placeholder="请输入追溯码"
          placeholder-class="placeholder"
          confirm-type="search"
          @confirm="handleSearch"
        />
      </view>
      <button class="btn-primary" :loading="loading" @tap="handleSearch">查询</button>

      <!-- 扫码（仅 App/小程序） -->
      <!-- #ifdef APP-PLUS || MP-WEIXIN -->
      <button class="btn-default" @tap="handleScan">扫码查询</button>
      <!-- #endif -->
    </view>

    <!-- 查询结果 -->
    <view v-if="result" class="result-card">
      <view class="result-header">
        <text class="result-title">追溯信息</text>
        <text class="result-code">{{ result.trace_code }}</text>
      </view>

      <view class="info-list">
        <view class="info-item">
          <text class="info-label">食材名称</text>
          <text class="info-value">{{ result.ingredient_name || '-' }}</text>
        </view>
        <view class="info-item">
          <text class="info-label">供应商</text>
          <text class="info-value">{{ result.supplier_name || '-' }}</text>
        </view>
        <view class="info-item">
          <text class="info-label">批次号</text>
          <text class="info-value">{{ result.batch_no || '-' }}</text>
        </view>
        <view class="info-item">
          <text class="info-label">生产日期</text>
          <text class="info-value">{{ formatDate(result.production_date) }}</text>
        </view>
        <view class="info-item">
          <text class="info-label">过期日期</text>
          <text class="info-value">{{ formatDate(result.expiry_date) }}</text>
        </view>
        <view class="info-item">
          <text class="info-label">检验报告</text>
          <text class="info-value">{{ result.test_report || '已检验' }}</text>
        </view>
        <view class="info-item">
          <text class="info-label">检疫证明</text>
          <text class="info-value">{{ result.quarantine_cert || '已检疫' }}</text>
        </view>
        <view class="info-item">
          <text class="info-label">创建时间</text>
          <text class="info-value">{{ formatDateTime(result.created_at) }}</text>
        </view>
      </view>
    </view>

    <view v-else-if="searched && !result" class="empty">
      <view class="empty-icon">🔍</view>
      <view>未找到追溯记录</view>
    </view>

    <view v-if="!searched" class="empty">
      <view class="empty-icon">🔗</view>
      <view>请输入追溯码查询</view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { traceApi } from '@/api'
import type { TraceRecord } from '@/types'

const traceCode = ref('')
const result = ref<TraceRecord | null>(null)
const loading = ref(false)
const searched = ref(false)

const formatDate = (val: string | null): string => {
  if (!val) return '-'
  return new Date(val).toISOString().slice(0, 10)
}

const formatDateTime = (val: string): string => {
  if (!val) return '-'
  const d = new Date(val)
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

const handleSearch = async () => {
  const code = traceCode.value.trim()
  if (!code) {
    uni.showToast({ title: '请输入追溯码', icon: 'none' })
    return
  }

  loading.value = true
  searched.value = true
  try {
    result.value = await traceApi.get(code)
  } catch (e: unknown) {
    const err = e as Error
    uni.showToast({ title: err.message || '查询失败', icon: 'none' })
    result.value = null
  } finally {
    loading.value = false
  }
}

const handleScan = () => {
  uni.scanCode({
    success: (res) => {
      traceCode.value = res.result
      handleSearch()
    },
    fail: () => {
      uni.showToast({ title: '扫码取消', icon: 'none' })
    },
  })
}
</script>

<style scoped lang="scss">
.page {
  min-height: 100vh;
}

.search-card {
  margin: 16rpx;
  padding: 32rpx 24rpx;
  background: #fff;
  border-radius: 16rpx;
}

.search-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 16rpx;
}

.search-input-wrap {
  margin-bottom: 16rpx;
}

.search-input {
  width: 100%;
  height: 80rpx;
  padding: 0 24rpx;
  background: #f5f5f7;
  border-radius: 12rpx;
  font-size: 28rpx;
}

.placeholder {
  color: #86868b;
}

.btn-primary {
  width: 100%;
  height: 80rpx;
  background: #18a058;
  color: #fff;
  border-radius: 12rpx;
  font-size: 28rpx;
  font-weight: 600;
  border: none;
  margin-top: 8rpx;

  &:active {
    background: #0c7a43;
  }
}

.btn-default {
  width: 100%;
  height: 80rpx;
  background: #fff;
  color: #18a058;
  border: 1rpx solid #18a058;
  border-radius: 12rpx;
  font-size: 28rpx;
  margin-top: 12rpx;
}

.result-card {
  margin: 16rpx;
  padding: 24rpx;
  background: #fff;
  border-radius: 16rpx;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 16rpx;
  border-bottom: 1rpx solid #e5e5ea;
  margin-bottom: 16rpx;
}

.result-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #1d1d1f;
}

.result-code {
  font-size: 24rpx;
  color: #18a058;
  font-family: monospace;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-label {
  font-size: 26rpx;
  color: #86868b;
}

.info-value {
  font-size: 26rpx;
  color: #1d1d1f;
  font-weight: 500;
  text-align: right;
}
</style>
