<template>
  <div class="users-page">
    <n-card :bordered="false">
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <n-button type="primary" @click="showAdd = true">新增用户</n-button>
        </div>
      </template>

      <n-data-table
        :columns="columns"
        :data="pagedUsers"
        :loading="loading"
        :bordered="false"
        :single-line="false"
        size="small"
        remote
        :pagination="pagination"
        @update:page="handlePageChange"
      />
    </n-card>

    <!-- 新增/编辑用户 -->
    <n-modal
      v-model:show="showAdd"
      :title="isEdit ? '编辑用户' : '新增用户'"
      preset="card"
      style="width: 500px; max-width: calc(100vw - 32px);"
      :mask-closable="false"
    >
      <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" label-width="80">
        <n-form-item label="用户名" path="username">
          <n-input v-model:value="form.username" :disabled="isEdit" placeholder="3-20位字母数字" />
        </n-form-item>
        <n-form-item label="姓名" path="real_name">
          <n-input v-model:value="form.real_name" placeholder="真实姓名" />
        </n-form-item>
        <n-form-item v-if="!isEdit" label="密码" path="password">
          <n-input v-model:value="form.password" type="password" show-password-on="click" placeholder="不少于6位" />
        </n-form-item>
        <n-form-item label="角色" path="role">
          <n-select v-model:value="form.role" :options="roleOptions" placeholder="选择角色" />
        </n-form-item>
        <n-form-item label="所属组织" path="org_id">
          <n-select v-model:value="form.org_id" :options="orgOptions" placeholder="选择组织" clearable />
        </n-form-item>
        <n-form-item label="手机号" path="phone">
          <n-input v-model:value="form.phone" placeholder="手机号" />
        </n-form-item>
        <n-form-item label="邮箱" path="email">
          <n-input v-model:value="form.email" placeholder="邮箱地址" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <n-button @click="showAdd = false">取消</n-button>
          <n-button type="primary" :loading="submitting" @click="handleSubmit">保存</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { NTag, NButton, NSpace, NSwitch, useMessage, type DataTableColumns, type FormInst, type FormRules, type PaginationProps } from 'naive-ui'
import { userApi, orgApi } from '@/api'
import type { UserWithOrg, Org, UserRole } from '@/types'

const loading = ref(false)
const userList = ref<UserWithOrg[]>([])
const orgList = ref<Org[]>([])
const page = ref(1)
const pageSize = ref(10)
const showAdd = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref<FormInst | null>(null)
const currentUser = ref<UserWithOrg | null>(null)

interface UserForm {
  username: string
  real_name: string
  password: string
  role: UserRole | ''
  org_id: number | null
  phone: string
  email: string
}

const form = ref<UserForm>({
  username: '',
  real_name: '',
  password: '',
  role: '',
  org_id: null,
  phone: '',
  email: '',
})

const rules = computed<FormRules>(() => ({
  username: [
    { required: true, message: '请输入用户名', trigger: ['blur', 'input'] },
    { min: 3, max: 20, message: '长度3-20位', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: isEdit.value
    ? []
    : [
        { required: true, message: '请输入密码', trigger: ['blur', 'input'] },
        { min: 6, message: '密码不少于6位', trigger: 'blur' },
      ],
}))

const roleOptions = [
  { label: '超级管理员', value: 'super_admin' },
  { label: '系统管理员', value: 'admin' },
  { label: '经理', value: 'manager' },
  { label: '操作员', value: 'operator' },
  { label: '查看者', value: 'viewer' },
]

const orgOptions = computed(() =>
  orgList.value.map((o) => ({ value: o.id, label: o.name })),
)

const roleLabel = (role: string): string => {
  const map: Record<string, string> = {
    super_admin: '超级管理员',
    admin: '系统管理员',
    manager: '经理',
    operator: '操作员',
    viewer: '查看者',
  }
  return map[role] || role
}

const roleTagType = (role: string): 'error' | 'warning' | 'success' | 'info' | 'default' => {
  const map: Record<string, 'error' | 'warning' | 'success' | 'info' | 'default'> = {
    super_admin: 'error',
    admin: 'warning',
    manager: 'success',
    operator: 'info',
    viewer: 'default',
  }
  return map[role] || 'default'
}

const total = computed(() => userList.value.length)
const pagedUsers = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return userList.value.slice(start, start + pageSize.value)
})

const pagination = computed<PaginationProps>(() => ({
  page: page.value,
  pageSize: pageSize.value,
  itemCount: total.value,
  prefix: ({ itemCount }) => `共 ${itemCount} 条`,
}))

const handlePageChange = (p: number) => {
  page.value = p
}

const columns: DataTableColumns<UserWithOrg> = [
  { title: '用户名', key: 'username', width: 120 },
  { title: '姓名', key: 'real_name', width: 100 },
  {
    title: '角色',
    key: 'role',
    width: 120,
    render: (row) => h(NTag, { type: roleTagType(row.role), size: 'small' }, { default: () => roleLabel(row.role) }),
  },
  { title: '所属组织', key: 'org_name' },
  { title: '手机号', key: 'phone', width: 130 },
  { title: '邮箱', key: 'email' },
  {
    title: '状态',
    key: 'is_active',
    width: 90,
    render: (row) =>
      h(NSwitch, {
        value: !!row.is_active,
        onUpdateValue: (val: boolean) => toggleStatus(row, val),
      }),
  },
  { title: '最后登录', key: 'last_login', width: 160 },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    align: 'center',
    fixed: 'right',
    render: (row) =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(
            NButton,
            { text: true, type: 'primary', size: 'small', onClick: () => handleEdit(row) },
            { default: () => '编辑' },
          ),
          h(
            NButton,
            { text: true, type: 'error', size: 'small', onClick: () => handleDelete(row) },
            { default: () => '删除' },
          ),
        ],
      }),
  },
]

const message = useMessage()

const loadUsers = async () => {
  loading.value = true
  try {
    userList.value = await userApi.list()
  } catch {
    message.error('加载用户失败')
    userList.value = []
  } finally {
    loading.value = false
  }
}

const loadOrgs = async () => {
  try {
    orgList.value = await orgApi.list()
  } catch {
    orgList.value = []
  }
}

const handleEdit = (row: UserWithOrg) => {
  isEdit.value = true
  currentUser.value = row
  form.value = {
    username: row.username,
    real_name: row.real_name || '',
    password: '',
    role: row.role,
    org_id: row.org_id,
    phone: row.phone || '',
    email: row.email || '',
  }
  showAdd.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    if (isEdit.value && currentUser.value) {
      // 编辑时只发送 UserUpdate schema 支持的字段（不含 username/password）
      const { username, password, ...updateData } = form.value
      void username
      void password
      await userApi.update(currentUser.value.id, updateData)
      message.success('更新成功')
    } else {
      await userApi.create(form.value)
      message.success('创建成功')
    }
    showAdd.value = false
    loadUsers()
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } } }
    message.error(err.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row: UserWithOrg) => {
  if (!confirm(`确定删除用户 "${row.username}" 吗？`)) return
  try {
    await userApi.delete(row.id)
    message.success('删除成功')
    loadUsers()
  } catch {
    message.error('删除失败')
  }
}

const toggleStatus = async (row: UserWithOrg, val: boolean) => {
  try {
    await userApi.update(row.id, { is_active: val })
    row.is_active = val
    message.success(val ? '已启用' : '已停用')
  } catch {
    message.error('状态更新失败')
  }
}

onMounted(() => {
  loadUsers()
  loadOrgs()
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
</style>
