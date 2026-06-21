import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { UserRole } from '@/types'

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    title?: string
    roles?: UserRole[]
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '概览' } },
      { path: 'ingredients', name: 'Ingredients', component: () => import('@/views/Ingredients.vue'), meta: { title: '食材管理', roles: ['admin', 'super_admin', 'manager', 'operator'] } },
      { path: 'stock-in', name: 'StockIn', component: () => import('@/views/StockIn.vue'), meta: { title: '入库管理', roles: ['admin', 'super_admin', 'manager', 'operator'] } },
      { path: 'stock-out', name: 'StockOut', component: () => import('@/views/StockOut.vue'), meta: { title: '出库管理', roles: ['admin', 'super_admin', 'manager', 'operator'] } },
      { path: 'inventory', name: 'Inventory', component: () => import('@/views/Inventory.vue'), meta: { title: '库存盘点', roles: ['admin', 'super_admin', 'manager'] } },
      { path: 'suppliers', name: 'Suppliers', component: () => import('@/views/Suppliers.vue'), meta: { title: '供应商', roles: ['admin', 'super_admin', 'manager', 'operator'] } },
      { path: 'finance', name: 'Finance', component: () => import('@/views/Finance.vue'), meta: { title: '财务统计', roles: ['admin', 'super_admin', 'manager'] } },
      { path: 'trace', name: 'Trace', component: () => import('@/views/Trace.vue'), meta: { title: '追溯管理' } },
      { path: 'users', name: 'Users', component: () => import('@/views/Users.vue'), meta: { title: '用户管理', roles: ['admin', 'super_admin'] } },
      { path: 'audit', name: 'Audit', component: () => import('@/views/Audit.vue'), meta: { title: '审计日志', roles: ['admin', 'super_admin'] } },
      { path: 'gov', name: 'GovDashboard', component: () => import('@/views/GovDashboard.vue'), meta: { title: '教育局监管', roles: ['super_admin'] } },
    ],
  },
  // 兜底：任何其它路径交给 SPA，避免 Nginx 刷新丢失
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to, _from, next) => {
  // 初始化 Pinia（若在页面刷新时还未恢复）
  const auth = useAuthStore()
  auth.initAuth()

  const token = auth.token
  const needLogin = !to.meta.public

  if (needLogin && !token) return next('/login')

  // 角色校验
  const required = to.meta.roles
  if (required && required.length > 0 && !auth.hasRole(required)) {
    return next('/dashboard')
  }

  // 页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} · 学校食材供应链管理平台`
  }

  next()
})

export default router
