<template>
  <div>
    <n-card :bordered="false">
      <template #header>
        <div class="card-header">
          <span>入库管理</span>
          <n-button type="primary" @click="showDialog">新增入库</n-button>
        </div>
      </template>

      <n-data-table
        :columns="columns"
        :data="records"
        :loading="loading"
        :bordered="false"
        :single-line="false"
        size="small"
        :scroll-x="1200"
      />
    </n-card>

    <n-modal
      v-model:show="dialogVisible"
      title="新增入库"
      preset="card"
      style="width: 600px; max-width: calc(100vw - 32px);"
      :mask-closable="false"
    >
      <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" label-width="120">
        <n-form-item label="食材" path="ingredient_id">
          <n-select
            v-model:value="form.ingredient_id"
            :options="ingredientOptions"
            filterable
            placeholder="选择食材"
          />
        </n-form-item>
        <n-form-item label="供应商" path="supplier_id">
          <n-select
            v-model:value="form.supplier_id"
            :options="supplierOptions"
            filterable
            clearable
            placeholder="选择供应商"
          />
        </n-form-item>
        <n-form-item label="批次号" path="batch_number">
          <n-input v-model:value="form.batch_number" placeholder="自定义批次号" />
        </n-form-item>
        <n-form-item label="数量" path="quantity">
          <n-input-number v-model:value="form.quantity" :min="0.01" :precision="2" style="width: 100%;" />
        </n-form-item>
        <n-form-item label="单价" path="unit_price">
          <n-input-number v-model:value="form.unit_price" :min="0" :precision="2" style="width: 100%;" />
        </n-form-item>
        <n-form-item label="验收人1" path="inspector1_id">
          <n-select
            v-model:value="form.inspector1_id"
            :options="userOptions"
            filterable
            clearable
            placeholder="选择验收人"
          />
        </n-form-item>
        <n-form-item label="验收人2" path="inspector2_id">
          <n-select
            v-model:value="form.inspector2_id"
            :options="userOptions"
            filterable
            clearable
            placeholder="选择验收人"
          />
        </n-form-item>
        <n-form-item label="生产日期">
          <n-date-picker v-model:value="form.production_date" type="date" style="width: 100%;" clearable />
        </n-form-item>
        <n-form-item label="保质期至">
          <n-date-picker v-model:value="form.expiry_date" type="date" style="width: 100%;" clearable />
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model:value="form.remark" type="textarea" :rows="2" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <n-button @click="dialogVisible = false">取消</n-button>
          <n-button type="primary" :loading="submitting" @click="submit">确定</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useMessage, type DataTableColumns, type FormInst, type FormRules } from 'naive-ui'
import { stockApi, ingredientApi, supplierApi, userApi } from '@/api'
import type { StockIn, Ingredient, Supplier, UserWithOrg } from '@/types'

const records = ref<StockIn[]>([])
const ingredientList = ref<Ingredient[]>([])
const supplierList = ref<Supplier[]>([])
const userList = ref<UserWithOrg[]>([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const formRef = ref<FormInst | null>(null)

interface StockInForm {
  ingredient_id: number | null
  supplier_id: number | null
  batch_number: string
  quantity: number
  unit_price: number
  inspector1_id: number | null
  inspector2_id: number | null
  production_date: number | null
  expiry_date: number | null
  remark: string
}

const form = ref<StockInForm>({
  ingredient_id: null,
  supplier_id: null,
  batch_number: '',
  quantity: 1,
  unit_price: 0,
  inspector1_id: null,
  inspector2_id: null,
  production_date: null,
  expiry_date: null,
  remark: '',
})

const rules: FormRules = {
  ingredient_id: [{ required: true, message: '请选择食材', trigger: 'change', type: 'number' }],
  quantity: [{ required: true, message: '请输入数量', trigger: ['blur', 'change'], type: 'number' }],
  unit_price: [{ required: true, message: '请输入单价', trigger: ['blur', 'change'], type: 'number' }],
  inspector1_id: [{ required: true, message: '请选择验收人1', trigger: 'change', type: 'number' }],
  inspector2_id: [{ required: true, message: '请选择验收人2', trigger: 'change', type: 'number' }],
}

const ingredientOptions = computed(() =>
  ingredientList.value.map((i) => ({ value: i.id, label: i.name })),
)
const supplierOptions = computed(() =>
  supplierList.value.map((s) => ({ value: s.id, label: s.name })),
)
const userOptions = computed(() =>
  userList.value.map((u) => ({ value: u.id, label: u.real_name || u.username })),
)

const formatDate = (val: string | null) => {
  if (!val) return ''
  return new Date(val).toLocaleString('zh-CN')
}

const getUserName = (id: number | null) => {
  if (!id) return ''
  const user = userList.value.find((u) => u.id === id)
  return user ? user.real_name || user.username : id
}

const columns: DataTableColumns<StockIn> = [
  { title: '批次号', key: 'batch_no' },
  { title: '食材', key: 'ingredient_name' },
  { title: '供应商', key: 'supplier_name' },
  { title: '批次号(自定义)', key: 'batch_number' },
  { title: '数量', key: 'quantity' },
  {
    title: '单价',
    key: 'unit_price',
    render: (row) => `¥${Number(row.unit_price).toFixed(2)}`,
  },
  {
    title: '总价',
    key: 'total_price',
    render: (row) => `¥${Number(row.total_price).toFixed(2)}`,
  },
  {
    title: '验收人1',
    key: 'inspector1_id',
    render: (row) => getUserName(row.inspector1_id),
  },
  {
    title: '验收人2',
    key: 'inspector2_id',
    render: (row) => getUserName(row.inspector2_id),
  },
  {
    title: '入库时间',
    key: 'created_at',
    width: 170,
    render: (row) => formatDate(row.created_at),
  },
]

const message = useMessage()

const loadData = async () => {
  loading.value = true
  try {
    const [recordsData, ingredients, suppliers, users] = await Promise.all([
      stockApi.in.list(),
      ingredientApi.list(),
      supplierApi.list(),
      userApi.list(),
    ])
    records.value = recordsData
    ingredientList.value = ingredients
    supplierList.value = suppliers
    userList.value = users
  } catch {
    message.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const showDialog = () => {
  form.value = {
    ingredient_id: null,
    supplier_id: null,
    batch_number: '',
    quantity: 1,
    unit_price: 0,
    inspector1_id: null,
    inspector2_id: null,
    production_date: null,
    expiry_date: null,
    remark: '',
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
    // 将时间戳转为 ISO 字符串（后端期望 date 格式）
    const payload: Record<string, unknown> = { ...form.value }
    if (form.value.production_date) {
      payload.production_date = new Date(form.value.production_date).toISOString().slice(0, 10)
    }
    if (form.value.expiry_date) {
      payload.expiry_date = new Date(form.value.expiry_date).toISOString().slice(0, 10)
    }
    await stockApi.in.create(payload)
    message.success('入库成功')
    dialogVisible.value = false
    loadData()
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } } }
    message.error(err.response?.data?.detail || '入库失败')
  } finally {
    submitting.value = false
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
