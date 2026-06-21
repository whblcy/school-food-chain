import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '概览' }
      },
      {
        path: 'ingredients',
        name: 'Ingredients',
        component: () => import('../views/Ingredients.vue'),
        meta: { title: '食材管理' }
      },
      {
        path: 'stock-in',
        name: 'StockIn',
        component: () => import('../views/StockIn.vue'),
        meta: { title: '入库管理' }
      },
      {
        path: 'stock-out',
        name: 'StockOut',
        component: () => import('../views/StockOut.vue'),
        meta: { title: '出库管理' }
      },
      {
        path: 'inventory',
        name: 'Inventory',
        component: () => import('../views/Inventory.vue'),
        meta: { title: '库存盘点' }
      },
      {
        path: 'suppliers',
        name: 'Suppliers',
        component: () => import('../views/Suppliers.vue'),
        meta: { title: '供应商' }
      },
      {
        path: 'finance',
        name: 'Finance',
        component: () => import('../views/Finance.vue'),
        meta: { title: '财务统计' }
      },
      {
        path: 'trace',
        name: 'Trace',
        component: () => import('../views/Trace.vue'),
        meta: { title: '追溯管理' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../views/Users.vue'),
        meta: { title: '用户管理' }
      },
      {
        path: 'gov',
        name: 'GovDashboard',
        component: () => import('../views/GovDashboard.vue'),
        meta: { title: '教育局监管', role: 'admin' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  // 优先从 localStorage 读取 token，避免 Pinia 状态未恢复
  const token = authStore.token || localStorage.getItem('token')
  if (!to.meta.public && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
