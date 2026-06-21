<template>
  <div class="login-container">
    <div class="login-bg-shape shape-1" />
    <div class="login-bg-shape shape-2" />
    <div class="login-bg-shape shape-3" />

    <n-card class="login-card" :bordered="false" size="large">
      <div class="login-header">
        <div class="logo-circle">🍽️</div>
        <h1>学校食堂食材管理平台</h1>
        <p>全链路食材供应链管理系统</p>
      </div>

      <n-form ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent="handleLogin">
        <n-form-item path="username" :show-label="false">
          <n-input
            v-model:value="form.username"
            placeholder="用户名"
            clearable
            @keyup.enter="handleLogin"
          >
            <template #prefix>
              <n-icon size="18"><UserIcon /></n-icon>
            </template>
          </n-input>
        </n-form-item>

        <n-form-item path="password" :show-label="false">
          <n-input
            v-model:value="form.password"
            type="password"
            show-password-on="click"
            placeholder="密码"
            @keyup.enter="handleLogin"
          >
            <template #prefix>
              <n-icon size="18"><LockIcon /></n-icon>
            </template>
          </n-input>
        </n-form-item>

        <n-button
          type="primary"
          size="large"
          block
          :loading="loading"
          @click="handleLogin"
        >
          登 录
        </n-button>
      </n-form>

      <div class="login-footer">
        <n-alert v-if="isDev" type="info" :bordered="false" size="small">
          默认账号: admin / 密码: admin123
        </n-alert>
        <p class="copyright">© 2026 学校食材供应链平台</p>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { h, ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, type FormInst, type FormRules } from 'naive-ui'
import { useMessage } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loading = ref(false)
const isDev = import.meta.env.DEV

const form = reactive({
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: ['blur', 'input'] }],
  password: [{ required: true, message: '请输入密码', trigger: ['blur', 'input'] }],
}

// 内联 SVG 图标
const UserIcon = () =>
  h(NIcon, null, {
    default: () =>
      h('span', {
        innerHTML:
          '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
        style: 'display:inline-flex',
      }),
  })
const LockIcon = () =>
  h(NIcon, null, {
    default: () =>
      h('span', {
        innerHTML:
          '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
        style: 'display:inline-flex',
      }),
  })

const handleLogin = async () => {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  loading.value = true
  try {
    await authStore.login(form.username, form.password)
    message.success('登录成功')
    router.push('/')
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } } }
    message.error(err.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
  position: relative;
  overflow: hidden;
}

.login-bg-shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
  animation: float 12s ease-in-out infinite;
}

.shape-1 {
  width: 400px;
  height: 400px;
  background: #18a058;
  top: -100px;
  left: -100px;
}

.shape-2 {
  width: 300px;
  height: 300px;
  background: #36ad6a;
  bottom: -50px;
  right: -50px;
  animation-delay: -4s;
}

.shape-3 {
  width: 200px;
  height: 200px;
  background: #2080f0;
  top: 50%;
  left: 60%;
  animation-delay: -8s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.95); }
}

.login-card {
  width: 420px;
  max-width: calc(100vw - 32px);
  padding: 12px 20px;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  position: relative;
  z-index: 1;
}

.login-header {
  text-align: center;
  margin-bottom: 28px;
}

.logo-circle {
  width: 72px;
  height: 72px;
  margin: 0 auto 16px;
  border-radius: 50%;
  background: linear-gradient(135deg, #18a058, #36ad6a);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  box-shadow: 0 8px 24px rgba(24, 160, 88, 0.3);
}

.login-header h1 {
  font-size: 22px;
  color: var(--n-text-color, #1d1d1f);
  margin: 0 0 8px;
  font-weight: 700;
}

.login-header p {
  color: var(--n-text-color-3, #86868b);
  font-size: 13px;
  margin: 0;
}

.login-footer {
  margin-top: 20px;
  text-align: center;
}

.copyright {
  margin: 12px 0 0;
  color: var(--n-text-color-3, #86868b);
  font-size: 12px;
}

@media (max-width: 480px) {
  .login-card {
    padding: 8px 12px;
  }
  .login-header h1 {
    font-size: 18px;
  }
}
</style>
