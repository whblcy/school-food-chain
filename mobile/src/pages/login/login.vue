<template>
  <view class="login-page">
    <view class="login-bg-shape shape-1" />
    <view class="login-bg-shape shape-2" />

    <view class="login-card">
      <view class="logo-circle">🍽️</view>
      <view class="title">学校食堂食材管理平台</view>
      <view class="subtitle">全链路食材供应链管理系统</view>

      <view class="form">
        <view class="form-item">
          <input
            v-model="form.username"
            class="input"
            placeholder="请输入用户名"
            placeholder-class="placeholder"
            @confirm="handleLogin"
          />
        </view>
        <view class="form-item">
          <input
            v-model="form.password"
            class="input"
            password
            placeholder="请输入密码"
            placeholder-class="placeholder"
            @confirm="handleLogin"
          />
        </view>

        <view v-if="errorMsg" class="error-msg">{{ errorMsg }}</view>

        <button class="btn-primary" :loading="loading" @tap="handleLogin">
          {{ loading ? '登录中...' : '登 录' }}
        </button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const form = ref({
  username: '',
  password: '',
})

const loading = ref(false)
const errorMsg = ref('')

const handleLogin = async () => {
  if (!form.value.username || !form.value.password) {
    errorMsg.value = '请输入用户名和密码'
    return
  }

  loading.value = true
  errorMsg.value = ''

  try {
    await auth.login(form.value.username, form.value.password)
    uni.showToast({ title: '登录成功', icon: 'success' })
    setTimeout(() => {
      uni.switchTab({ url: '/pages/index/index' })
    }, 500)
  } catch (e: unknown) {
    const err = e as Error
    errorMsg.value = '登录失败: ' + err.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.login-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #18a058 0%, #0c7a43 100%);
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40rpx;
}

.login-bg-shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(60rpx);
  opacity: 0.3;

  &.shape-1 {
    width: 400rpx;
    height: 400rpx;
    background: #ffffff;
    top: -100rpx;
    right: -100rpx;
  }

  &.shape-2 {
    width: 300rpx;
    height: 300rpx;
    background: #36ad6a;
    bottom: -50rpx;
    left: -50rpx;
  }
}

.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 640rpx;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20rpx);
  border-radius: 32rpx;
  padding: 60rpx 40rpx;
  box-shadow: 0 20rpx 60rpx rgba(0, 0, 0, 0.15);
}

.logo-circle {
  width: 120rpx;
  height: 120rpx;
  margin: 0 auto 24rpx;
  background: #18a058;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 60rpx;
}

.title {
  text-align: center;
  font-size: 36rpx;
  font-weight: 700;
  color: #1d1d1f;
  margin-bottom: 8rpx;
}

.subtitle {
  text-align: center;
  font-size: 24rpx;
  color: #86868b;
  margin-bottom: 48rpx;
}

.form-item {
  margin-bottom: 24rpx;
}

.input {
  width: 100%;
  height: 88rpx;
  padding: 0 24rpx;
  background: #f5f5f7;
  border-radius: 16rpx;
  font-size: 30rpx;
  color: #1d1d1f;
  border: 2rpx solid transparent;
  transition: border-color 0.2s;

  &:focus {
    border-color: #18a058;
  }
}

.placeholder {
  color: #86868b;
}

.error-msg {
  color: #ff453a;
  font-size: 24rpx;
  margin-bottom: 16rpx;
  text-align: center;
}

.btn-primary {
  width: 100%;
  height: 88rpx;
  background: #18a058;
  color: #fff;
  border-radius: 16rpx;
  font-size: 32rpx;
  font-weight: 600;
  border: none;
  margin-top: 16rpx;

  &:active {
    background: #0c7a43;
  }
}
</style>
