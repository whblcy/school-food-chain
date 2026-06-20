<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <el-icon :size="28" color="#fff"><Food /></el-icon>
        <span>食材管理平台</span>
      </div>
      
      <el-menu
        :default-active="$route.path"
        router
        background-color="#1d1d1f"
        text-color="#a1a1a6"
        active-text-color="#fff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon>
          <span>概览统计</span>
        </el-menu-item>
        
        <el-menu-item index="/ingredients">
          <el-icon><Goods /></el-icon>
          <span>食材管理</span>
        </el-menu-item>
        
        <el-menu-item index="/stock-in">
          <el-icon><Download /></el-icon>
          <span>入库管理</span>
        </el-menu-item>
        
        <el-menu-item index="/stock-out">
          <el-icon><Upload /></el-icon>
          <span>出库管理</span>
        </el-menu-item>
        
        <el-menu-item index="/inventory">
          <el-icon><Check /></el-icon>
          <span>库存盘点</span>
        </el-menu-item>
        
        <el-menu-item index="/suppliers">
          <el-icon><OfficeBuilding /></el-icon>
          <span>供应商</span>
        </el-menu-item>
        
        <el-menu-item index="/finance">
          <el-icon><Money /></el-icon>
          <span>财务统计</span>
        </el-menu-item>
        
        <el-menu-item index="/trace">
          <el-icon><Search /></el-icon>
          <span>追溯管理</span>
        </el-menu-item>
        
        <el-menu-item index="/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <el-container>
      <el-header class="header">
        <div class="header-title">{{ $route.meta.title }}</div>
        <div class="header-actions">
          <el-dropdown>
            <span class="user-info">
              <el-icon><User /></el-icon>
              {{ authStore.user?.real_name || authStore.user?.username || '管理员' }}
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { Food, DataLine, Goods, Download, Upload, Check, OfficeBuilding, Money, Search, User } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

const handleLogout = () => {
  authStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
}

.sidebar {
  background-color: #1d1d1f;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid #333;
}

.header {
  background-color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #1d1d1f;
}

.main-content {
  background-color: #f5f5f7;
  padding: 20px;
}
</style>
