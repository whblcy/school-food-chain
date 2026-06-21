<template>
  <div>
    <n-card :bordered="false">
      <template #header>
        <div class="card-header">
          <span>供应商管理</span>
          <n-button type="primary" @click="showDialog">添加供应商</n-button>
        </div>
      </template>

      <n-data-table
        :columns="columns"
        :data="pagedSuppliers"
        :loading="loading"
        :bordered="false"
        :single-line="false"
        size="small"
        remote
        :pagination="pagination"
        @update:page="handlePageChange"
      />
    </n-card>

    <!-- 添加/编辑对话框 -->
    <n-modal
      v-model:show="dialogVisible"
      :title="isEdit ? '编辑供应商' : '添加供应商'"
      preset="card"
      style="width: 500px; max-width: calc(100vw - 32px);"
      :mask-closable="false"
    >
      <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" label-width="100">
        <n-form-item label="名称" path="name">
          <n-input v-model:value="form.name" />
        </n-form-item>
        <n-form-item label="编码" path="code">
          <n-input v-model:value="form.code" />
        </n-form-item>
        <n-form-item label="联系人">
          <n-input v-model:value="form.contact_person" />
        </n-form-item>
        <n-form-item label="电话">
          <n-input v-model:value="form.phone" />
        </n-form-item>
        <n-form-item label="邮箱">
          <n-input v-model:value="form.email" />
        </n-form-item>
        <n-form-item label="地址">
          <n-input v-model:value="form.address" />
        </n-form-item>
        <n-form-item label="状态">
          <n-select v-model:value="form.status" :options="statusOptions" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <n-button @click="dialogVisible = false">取消</n-button>
          <n-button type="primary" :loading="submitting" @click="submit">确定</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 拉黑对话框 -->
    <n-modal
      v-model:show="blacklistVisible"
      title="拉黑供应商"
      preset="card"
      style="width: 450px; max-width: calc(100vw - 32px);"
      :mask-closable="false"
    >
      <n-form ref="blacklistFormRef" :model="blacklistForm" :rules="blacklistRules" label-placement="left" label-width="80">
        <n-form-item label="供应商">
          <span>{{ currentSupplier?.name }}</span>
        </n-form-item>
        <n-form-item label="原因" path="reason">
          <n-input v-model:value="blacklistForm.reason" type="textarea" :rows="3" placeholder="请输入拉黑原因" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <n-button @click="blacklistVisible = false">取消</n-button>
          <n-button type="primary" :loading="blacklistLoading" @click="confirmBlacklist">确认拉黑</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { NTag, NButton, NSpace, NRate, useMessage, type DataTableColumns, type FormInst, type FormRules, type PaginationProps } from 'naive-ui'
import { supplierApi } from '@/api'
import type { Supplier } from '@/types'

const suppliers = ref<Supplier[]>([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref<FormInst | null>(null)
const page = ref(1)
const pageSize = ref(10)

// 拉黑相关
const blacklistVisible = ref(false)
const blacklistLoading = ref(false)
const blacklistFormRef = ref<FormInst | null>(null)
const currentSupplier = ref<Supplier | null>(null)
const blacklistForm = ref({ reason: '' })
const blacklistRules: FormRules = {
  reason: [{ required: true, message: '请输入拉黑原因', trigger: ['blur', 'input'] }],
}

interface SupplierForm {
  name: string
  code: string
  contact_person: string
  phone: string
  email: string
  address: string
  status: 'active' | 'suspended' | 'blacklisted'
}

const form = ref<SupplierForm>({
  name: '',
  code: '',
  contact_person: '',
  phone: '',
  email: '',
  address: '',
  status: 'active',
})

const statusOptions = [
  { label: '正常', value: 'active' },
  { label: '暂停', value: 'suspended' },
]

const statusMap: Record<string, string> = {
  active: '正常',
  suspended: '暂停',
  blacklisted: '黑名单',
}

const statusType = (status: string): 'success' | 'warning' | 'error' | 'default' => {
  const map: Record<string, 'success' | 'warning' | 'error' | 'default'> = {
    active: 'success',
    suspended: 'warning',
    blacklisted: 'error',
  }
  return map[status] || 'default'
}

const rules: FormRules = {
  name: [{ required: true, message: '请输入名称', trigger: ['blur', 'input'] }],
  code: [{ required: true, message: '请输入编码', trigger: ['blur', 'input'] }],
}

const hasBlacklisted = computed(() => suppliers.value.some((s) => s.status === 'blacklisted'))

const total = computed(() => suppliers.value.length)
const pagedSuppliers = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return suppliers.value.slice(start, start + pageSize.value)
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

const columns = computed<DataTableColumns<Supplier>>(() => {
  const cols: DataTableColumns<Supplier> = [
    { title: '供应商名称', key: 'name' },
    { title: '编码', key: 'code' },
    { title: '联系人', key: 'contact_person' },
    { title: '电话', key: 'phone' },
    {
      title: '状态',
      key: 'status',
      render: (row) =>
        h(NTag, { type: statusType(row.status), size: 'small' }, { default: () => statusMap[row.status] || row.status }),
    },
  ]
  if (hasBlacklisted.value) {
    cols.push({
      title: '拉黑原因',
      key: 'blacklist_reason',
      render: (row) => row.blacklist_reason || '-',
    })
  }
  cols.push({
    title: '评分',
    key: 'rating',
    render: (row) => h(NRate, { value: Number(row.rating), disabled: true, size: 'small', allowHalf: true }),
  })
  cols.push({
    title: '操作',
    key: 'actions',
    width: 280,
    render: (row) =>
      h(NSpace, { size: 8 }, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => editSupplier(row) }, { default: () => '编辑' }),
          row.status !== 'blacklisted'
            ? h(
                NButton,
                { size: 'small', type: 'warning', onClick: () => handleBlacklist(row) },
                { default: () => '拉黑' },
              )
            : h(
                NButton,
                { size: 'small', type: 'success', onClick: () => handleUnblacklist(row) },
                { default: () => '恢复' },
              ),
          h(
            NButton,
            { size: 'small', type: 'error', onClick: () => deleteSupplier(row.id) },
            { default: () => '删除' },
          ),
        ],
      }),
  })
  return cols
})

const message = useMessage()

const loadData = async () => {
  loading.value = true
  try {
    suppliers.value = await supplierApi.list()
  } catch {
    message.error('加载供应商列表失败')
    suppliers.value = []
  } finally {
    loading.value = false
  }
}

const showDialog = () => {
  isEdit.value = false
  currentSupplier.value = null
  form.value = {
    name: '',
    code: '',
    contact_person: '',
    phone: '',
    email: '',
    address: '',
    status: 'active',
  }
  dialogVisible.value = true
}

const editSupplier = (row: Supplier) => {
  isEdit.value = true
  currentSupplier.value = row
  form.value = {
    name: row.name || '',
    code: row.code || '',
    contact_person: row.contact_person || '',
    phone: row.phone || '',
    email: row.email || '',
    address: row.address || '',
    status: (row.status as 'active' | 'suspended' | 'blacklisted') || 'active',
  }
  dialogVisible.value = true
}

const submit = async () => {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    if (isEdit.value && currentSupplier.value) {
      await supplierApi.update(currentSupplier.value.id, form.value)
      message.success('更新成功')
    } else {
      await supplierApi.create(form.value)
      message.success('添加成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } } }
    message.error(err.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

const deleteSupplier = async (id: number) => {
  if (!confirm('确认删除？')) return
  try {
    await supplierApi.delete(id)
    message.success('删除成功')
    loadData()
  } catch {
    message.error('删除失败')
  }
}

const handleBlacklist = (row: Supplier) => {
  currentSupplier.value = row
  blacklistForm.value = { reason: '' }
  blacklistVisible.value = true
}

const confirmBlacklist = async () => {
  try {
    await blacklistFormRef.value?.validate()
  } catch {
    return
  }
  if (!currentSupplier.value) return
  blacklistLoading.value = true
  try {
    await supplierApi.blacklist(currentSupplier.value.id, blacklistForm.value.reason)
    message.success('已拉黑')
    blacklistVisible.value = false
    loadData()
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } } }
    message.error(err.response?.data?.detail || '拉黑失败')
  } finally {
    blacklistLoading.value = false
  }
}

const handleUnblacklist = async (row: Supplier) => {
  if (!confirm(`确认恢复供应商 "${row.name}" 吗？`)) return
  try {
    await supplierApi.unblacklist(row.id)
    message.success('已恢复')
    loadData()
  } catch {
    message.error('恢复失败')
  }
}

onMounted(loadData)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
