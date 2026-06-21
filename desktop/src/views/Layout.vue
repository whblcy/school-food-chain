<template>
  <n-layout has-sider class="layout-container">
    <!-- 侧边栏 -->
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="240"
      :collapsed="collapsed"
      show-trigger="bar"
      @collapse="collapsed = true"
      @expand="collapsed = false"
    >
      <div class="logo" :class="{ collapsed }">
        <span class="logo-icon">🍽️</span>
        <transition name="fade">
          <span v-if="!collapsed" class="logo-text">食材供应链</span>
        </transition>
      </div>
      <n-menu
        :value="activeKey"
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="20"
        :options="menuOptions"
        @update:value="handleMenuSelect"
      />
    </n-layout-sider>

    <n-layout>
      <!-- 顶部栏 -->
      <n-layout-header bordered class="header">
        <div class="header-left">
          <n-button quaternary circle @click="collapsed = !collapsed">
            <template #icon>
              <n-icon size="20"><MenuIcon /></n-icon>
            </template>
          </n-button>
          <span class="header-title">{{ route.meta.title || '概览' }}</span>
        </div>

        <div class="header-right">
          <!-- WebSocket 连接状态 -->
          <n-tooltip>
            <template #trigger>
              <n-badge dot :type="wsConnected ? 'success' : 'error'" processing>
                <n-icon size="18" :depth="2"><PulseIcon /></n-icon>
              </n-badge>
            </template>
            {{ wsConnected ? '实时连接正常' : '实时连接断开' }}
          </n-tooltip>

          <!-- 主题切换 -->
          <n-button quaternary circle @click="themeStore.toggle()">
            <template #icon>
              <n-icon size="18">
                <SunIcon v-if="themeStore.isDark" />
                <MoonIcon v-else />
              </n-icon>
            </template>
          </n-button>

          <!-- 语言切换 -->
          <n-dropdown :options="localeOptions" @select="handleLocaleChange">
            <n-button quaternary circle>
              <template #icon>
                <n-icon size="18"><GlobeIcon /></n-icon>
              </template>
            </n-button>
          </n-dropdown>

          <!-- 用户菜单 -->
          <n-dropdown :options="userMenuOptions" @select="handleUserMenu">
            <div class="user-info">
              <n-avatar round size="small" color="#18a058">
                {{ avatarText }}
              </n-avatar>
              <div class="user-meta">
                <span class="user-name">{{ authStore.user?.real_name || authStore.user?.username || '管理员' }}</span>
                <n-tag v-if="authStore.user?.role" size="tiny" :type="roleTagType(authStore.user.role)" round>
                  {{ roleLabel(authStore.user.role) }}
                </n-tag>
              </div>
            </div>
          </n-dropdown>
        </div>
      </n-layout-header>

      <!-- 内容区 -->
      <n-layout-content class="main-content" :native-scrollbar="false">
        <div class="page-container">
          <router-view />
        </div>
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NIcon, type MenuOption } from 'naive-ui'
import { useMessage } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { setLocale } from '@/i18n'
import { useWebSocket } from '@/composables/useWebSocket'
import type { UserRole } from '@/types'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const message = useMessage()
const { connect, disconnect, isConnected } = useWebSocket()

const collapsed = ref(false)
const wsConnected = isConnected

// ---- 图标（内联 SVG，避免依赖额外图标库）----
const iconRender = (svg: string) => () => h(NIcon, null, { default: () => h('span', { innerHTML: svg, style: 'display:inline-flex' }) })

const MenuIcon = iconRender('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>')
const SunIcon = iconRender('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>')
const MoonIcon = iconRender('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>')
const GlobeIcon = iconRender('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>')
const PulseIcon = iconRender('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>')

// ---- 菜单配置 ----
interface MenuItemDef {
  key: string
  label: string
  icon?: string
  roles?: UserRole[]
  superAdminOnly?: boolean
}

const menuItems: MenuItemDef[] = [
  { key: '/dashboard', label: '概览统计', icon: '📊' },
  { key: '/ingredients', label: '食材管理', icon: '🥬', roles: ['admin', 'super_admin', 'manager', 'operator'] },
  { key: '/stock-in', label: '入库管理', icon: '📥', roles: ['admin', 'super_admin', 'manager', 'operator'] },
  { key: '/stock-out', label: '出库管理', icon: '📤', roles: ['admin', 'super_admin', 'manager', 'operator'] },
  { key: '/inventory', label: '库存盘点', icon: '🔍', roles: ['admin', 'super_admin', 'manager'] },
  { key: '/suppliers', label: '供应商', icon: '🏭', roles: ['admin', 'super_admin', 'manager', 'operator'] },
  { key: '/finance', label: '财务统计', icon: '💰', roles: ['admin', 'super_admin', 'manager'] },
  { key: '/trace', label: '追溯管理', icon: '🔗' },
  { key: '/users', label: '用户管理', icon: '👥', roles: ['admin', 'super_admin'] },
  { key: '/audit', label: '审计日志', icon: '📝', roles: ['admin', 'super_admin'] },
  { key: '/gov', label: '教育局监管', icon: '🏛️', superAdminOnly: true },
]

const menuOptions = computed<MenuOption[]>(() => {
  return menuItems
    .filter((item) => {
      if (item.superAdminOnly) return authStore.isSuperAdmin
      if (!item.roles) return true
      return authStore.hasRole(item.roles)
    })
    .map((item) => ({
      label: item.label,
      key: item.key,
      icon: () => h('span', { style: 'font-size:16px; display:inline-flex; width:20px; justify-content:center' }, item.icon),
    }))
})

const activeKey = computed(() => route.path)

const handleMenuSelect = (key: string) => {
  router.push(key)
}

// ---- 角色相关 ----
const roleLabel = (role: UserRole): string => {
  const map: Record<UserRole, string> = {
    super_admin: '超级管理员',
    admin: '系统管理员',
    manager: '经理',
    operator: '操作员',
    viewer: '查看者',
  }
  return map[role] || role
}

const roleTagType = (role: UserRole): 'error' | 'warning' | 'success' | 'info' | 'default' => {
  const map: Record<UserRole, 'error' | 'warning' | 'success' | 'info' | 'default'> = {
    super_admin: 'error',
    admin: 'warning',
    manager: 'success',
    operator: 'info',
    viewer: 'default',
  }
  return map[role] || 'default'
}

const avatarText = computed(() => {
  const name = authStore.user?.real_name || authStore.user?.username || '?'
  return name.charAt(0).toUpperCase()
})

// ---- 用户菜单 ----
const userMenuOptions = [
  { label: '退出登录', key: 'logout' },
]

const handleUserMenu = async (key: string) => {
  if (key === 'logout') {
    await authStore.logout()
    disconnect()
    message.success('已退出登录')
    router.push('/login')
  }
}

// ---- 语言切换 ----
const localeOptions = [
  { label: '中文', key: 'zh' },
  { label: 'English', key: 'en' },
]

const handleLocaleChange = (key: string) => {
  setLocale(key as 'zh' | 'en')
  message.success(key === 'zh' ? '已切换为中文' : 'Switched to English')
}

// ---- WebSocket 实时通知 ----
watch(
  () => authStore.token,
  (token) => {
    if (token) {
      connect(token)
    } else {
      disconnect()
    }
  },
  { immediate: true },
)

onMounted(() => {
  if (authStore.token) connect(authStore.token)
})
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--n-text-color, #fff);
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid var(--n-border-color, rgba(255, 255, 255, 0.1));
  overflow: hidden;
  white-space: nowrap;
}

.logo.collapsed {
  gap: 0;
}

.logo-icon {
  font-size: 24px;
}

.header {
  height: var(--app-header-height, 64px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background 0.2s;
}

.user-info:hover {
  background: var(--n-color-hover, rgba(0, 0, 0, 0.05));
}

.user-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-name {
  font-size: 13px;
  font-weight: 500;
  line-height: 1;
}

.main-content {
  height: calc(100vh - var(--app-header-height, 64px));
}

.page-container {
  padding: 16px;
}

@media (max-width: 768px) {
  .page-container {
    padding: 8px;
  }
  .user-meta {
    display: none;
  }
}
</style>
