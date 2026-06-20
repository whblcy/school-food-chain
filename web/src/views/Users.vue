<template>
  <div class="users-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" @click="showAdd = true">
            <el-icon><Plus /></el-icon>新增用户
          </el-button>
        </div>
      </template>

      <el-table :data="userList" v-loading="loading" stripe>
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="real_name" label="姓名" width="100" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="roleType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="org_name" label="所属组织" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-switch
              v-model="row.status"
              :active-value="'active'"
              :inactive-value="'inactive'"
              @change="(val) => toggleStatus(row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="last_login" label="最后登录" width="160" />
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="primary" size="small" @click="handleResetPwd(row)">重置密码</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        class="pagination"
        @current-change="loadUsers"
      />
    </el-card>

    <!-- 新增/编辑用户 -->
    <el-dialog v-model="showAdd" :title="isEdit ? '编辑用户' : '新增用户'" width="500px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="用户名" prop="username" required>
          <el-input v-model="form.username" :disabled="isEdit" placeholder="3-20位字母数字" />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="form.real_name" placeholder="真实姓名" />
        </el-form-item>
        <el-form-item label="密码" prop="password" :required="!isEdit">
          <el-input v-model="form.password" type="password" show-password placeholder="不少于6位" />
        </el-form-item>
        <el-form-item label="角色" prop="role" required>
          <el-select v-model="form.role" placeholder="选择角色" style="width: 100%">
            <el-option label="系统管理员" value="admin" />
            <el-option label="学校管理员" value="school_admin" />
            <el-option label="食堂管理员" value="canteen_admin" />
            <el-option label="仓库管理员" value="warehouse_admin" />
            <el-option label="采购员" value="purchaser" />
            <el-option label="质检员" value="inspector" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属组织" prop="org_id">
          <el-select v-model="form.org_id" placeholder="选择组织" style="width: 100%" clearable>
            <el-option
              v-for="org in orgList"
              :key="org.id"
              :label="org.name"
              :value="org.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="手机号" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="邮箱地址" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码 -->
    <el-dialog v-model="showReset" title="重置密码" width="400px">
      <el-form :model="resetForm" label-width="80px">
        <el-form-item label="新密码" required>
          <el-input v-model="resetForm.password" type="password" show-password placeholder="新密码" />
        </el-form-item>
        <el-form-item label="确认密码" required>
          <el-input v-model="resetForm.confirmPassword" type="password" show-password placeholder="确认密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showReset = false">取消</el-button>
        <el-button type="primary" @click="confirmReset" :loading="resetting">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getUsers, createUser, updateUser, deleteUser } from '../api'

const loading = ref(false)
const userList = ref([])
const orgList = ref([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const showAdd = ref(false)
const showReset = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const resetting = ref(false)
const formRef = ref(null)
const currentUser = ref(null)

const form = ref({
  username: '',
  real_name: '',
  password: '',
  role: '',
  org_id: null,
  phone: '',
  email: ''
})

const resetForm = ref({
  password: '',
  confirmPassword: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '长度3-20位', trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码不少于6位', trigger: 'blur' }
  ]
}

const roleLabel = (role) => {
  const map = {
    admin: '系统管理员',
    school_admin: '学校管理员',
    canteen_admin: '食堂管理员',
    warehouse_admin: '仓库管理员',
    purchaser: '采购员',
    inspector: '质检员',
    user: '普通用户'
  }
  return map[role] || role
}

const roleType = (role) => {
  const map = {
    admin: 'danger',
    school_admin: 'warning',
    canteen_admin: 'success',
    warehouse_admin: 'info',
    purchaser: '',
    inspector: 'primary',
    user: 'info'
  }
  return map[role] || ''
}

const loadUsers = async () => {
  loading.value = true
  try {
    const res = await getUsers()
    userList.value = res.data || []
    total.value = res.data?.length || 0
  } catch (e) {
    ElMessage.error('加载用户失败')
    // 模拟数据
    userList.value = [
      { id: 1, username: 'admin', real_name: '系统管理员', role: 'admin', org_name: '总部', phone: '13800138000', email: 'admin@school.com', status: 'active', last_login: '2025-06-20 09:30:00' },
      { id: 2, username: 'zhangsan', real_name: '张三', role: 'canteen_admin', org_name: '第一食堂', phone: '13900139000', email: 'zs@school.com', status: 'active', last_login: '2025-06-19 17:20:00' },
      { id: 3, username: 'lisi', real_name: '李四', role: 'purchaser', org_name: '采购部', phone: '13700137000', email: 'ls@school.com', status: 'active', last_login: '2025-06-18 11:00:00' },
      { id: 4, username: 'wangwu', real_name: '王五', role: 'inspector', org_name: '质检部', phone: '13600136000', email: 'ww@school.com', status: 'inactive', last_login: '2025-06-10 14:30:00' },
    ]
    total.value = userList.value.length
  } finally {
    loading.value = false
  }
}

const handleEdit = (row) => {
  isEdit.value = true
  currentUser.value = row
  form.value = {
    username: row.username,
    real_name: row.real_name,
    password: '',
    role: row.role,
    org_id: row.org_id,
    phone: row.phone,
    email: row.email
  }
  showAdd.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEdit.value) {
      await updateUser(currentUser.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createUser(form.value)
      ElMessage.success('创建成功')
    }
    showAdd.value = false
    loadUsers()
  } catch (e) {
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除用户 "${row.username}" 吗？`, '确认删除', { type: 'warning' })
    await deleteUser(row.id)
    ElMessage.success('删除成功')
    loadUsers()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const handleResetPwd = (row) => {
  currentUser.value = row
  resetForm.value = { password: '', confirmPassword: '' }
  showReset.value = true
}

const confirmReset = async () => {
  if (!resetForm.value.password || resetForm.value.password.length < 6) {
    ElMessage.warning('密码不少于6位')
    return
  }
  if (resetForm.value.password !== resetForm.value.confirmPassword) {
    ElMessage.warning('两次密码不一致')
    return
  }
  resetting.value = true
  try {
    await updateUser(currentUser.value.id, { password: resetForm.value.password })
    ElMessage.success('密码重置成功')
    showReset.value = false
  } catch (e) {
    ElMessage.error('重置失败')
  } finally {
    resetting.value = false
  }
}

const toggleStatus = async (row, val) => {
  try {
    await updateUser(row.id, { status: val })
    ElMessage.success(val === 'active' ? '已启用' : '已停用')
  } catch (e) {
    row.status = val === 'active' ? 'inactive' : 'active'
    ElMessage.error('状态更新失败')
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.users-page {
  padding-bottom: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
