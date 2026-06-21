<template>
  <view class="page">
    <!-- 用户信息卡片 -->
    <view v-if="auth.isLoggedIn" class="profile-card">
      <view class="avatar">{{ avatarText }}</view>
      <view class="profile-info">
        <text class="profile-name">{{ auth.user?.real_name || auth.user?.username || '管理员' }}</text>
        <text class="profile-role">{{ roleLabel }}</text>
      </view>
    </view>

    <view v-else class="profile-card">
      <view class="avatar" style="background: #c7c7cc;">?</view>
      <view class="profile-info">
        <text class="profile-name">未登录</text>
        <button class="btn-login" @tap="goLogin">去登录</button>
      </view>
    </view>

    <!-- 功能菜单 -->
    <view v-if="auth.isLoggedIn" class="menu">
      <view class="menu-item" @tap="handleMenu('ingredients')">
        <text class="menu-icon">🥬</text>
        <text class="menu-text">食材管理</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-item" @tap="handleMenu('stock')">
        <text class="menu-icon">📦</text>
        <text class="menu-text">出入库记录</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-item" @tap="handleMenu('trace')">
        <text class="menu-icon">🔗</text>
        <text class="menu-text">追溯查询</text>
        <text class="menu-arrow">›</text>
      </view>
    </view>

    <!-- 设置菜单 -->
    <view v-if="auth.isLoggedIn" class="menu">
      <view class="menu-item" @tap="handleMenu('about')">
        <text class="menu-icon">ℹ️</text>
        <text class="menu-text">关于我们</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-item" @tap="handleMenu('clearCache')">
        <text class="menu-icon">🗑️</text>
        <text class="menu-text">清除缓存</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-item danger" @tap="handleLogout">
        <text class="menu-icon">🚪</text>
        <text class="menu-text">退出登录</text>
        <text class="menu-arrow">›</text>
      </view>
    </view>

    <view class="version">版本 2.0.0</view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import type { UserRole } from '@/types'

const auth = useAuthStore()

const avatarText = computed(() => {
  const name = auth.user?.real_name || auth.user?.username || '?'
  return name.charAt(0).toUpperCase()
})

const roleLabel = computed(() => {
  const map: Record<UserRole, string> = {
    super_admin: '超级管理员',
    admin: '系统管理员',
    manager: '经理',
    operator: '操作员',
    viewer: '查看者',
  }
  return auth.user ? map[auth.user.role] || auth.user.role : ''
})

const goLogin = () => {
  uni.navigateTo({ url: '/pages/login/login' })
}

const handleMenu = (key: string) => {
  switch (key) {
    case 'ingredients':
      uni.switchTab({ url: '/pages/ingredients/ingredients' })
      break
    case 'stock':
      uni.switchTab({ url: '/pages/stock/stock' })
      break
    case 'trace':
      uni.switchTab({ url: '/pages/trace/trace' })
      break
    case 'about':
      uni.showModal({
        title: '关于我们',
        content: '学校食堂食材全链路管理平台 v2.0.0\n提供食材采购、入库、出库、库存盘点、追溯管理一体化解决方案',
        showCancel: false,
      })
      break
    case 'clearCache':
      uni.showModal({
        title: '提示',
        content: '确定清除缓存吗？',
        success: async (res) => {
          if (res.confirm) {
            uni.clearStorageSync()
            uni.showToast({ title: '已清除', icon: 'success' })
            setTimeout(() => uni.reLaunch({ url: '/pages/login/login' }), 500)
          }
        },
      })
      break
  }
}

const handleLogout = () => {
  uni.showModal({
    title: '提示',
    content: '确定退出登录吗？',
    success: async (res) => {
      if (res.confirm) {
        await auth.logout()
        uni.showToast({ title: '已退出', icon: 'success' })
        setTimeout(() => uni.reLaunch({ url: '/pages/login/login' }), 500)
      }
    },
  })
}
</script>

<style scoped lang="scss">
.page {
  min-height: 100vh;
  padding-bottom: 40rpx;
}

.profile-card {
  display: flex;
  align-items: center;
  margin: 16rpx;
  padding: 32rpx;
  background: linear-gradient(135deg, #18a058 0%, #0c7a43 100%);
  border-radius: 20rpx;
  color: #fff;
}

.avatar {
  width: 120rpx;
  height: 120rpx;
  background: rgba(255, 255, 255, 0.25);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48rpx;
  font-weight: 700;
  margin-right: 24rpx;
}

.profile-info {
  flex: 1;
}

.profile-name {
  display: block;
  font-size: 36rpx;
  font-weight: 700;
  margin-bottom: 8rpx;
}

.profile-role {
  font-size: 24rpx;
  opacity: 0.9;
}

.btn-login {
  display: inline-block;
  margin-top: 8rpx;
  padding: 8rpx 24rpx;
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  border-radius: 24rpx;
  font-size: 24rpx;
  border: none;
}

.menu {
  margin: 16rpx;
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 28rpx 24rpx;
  border-bottom: 1rpx solid #e5e5ea;

  &:last-child {
    border-bottom: none;
  }

  &:active {
    background: #f5f5f7;
  }

  &.danger .menu-text {
    color: #ff453a;
  }
}

.menu-icon {
  font-size: 36rpx;
  margin-right: 20rpx;
}

.menu-text {
  flex: 1;
  font-size: 28rpx;
  color: #1d1d1f;
}

.menu-arrow {
  font-size: 36rpx;
  color: #c7c7cc;
}

.version {
  text-align: center;
  font-size: 24rpx;
  color: #86868b;
  margin-top: 32rpx;
}
</style>
