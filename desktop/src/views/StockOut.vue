<template>
  <div>
    <n-card :bordered="false">
      <template #header>
        <div class="card-header">
          <span>出库管理</span>
          <n-button type="primary" @click="showDialog">新增出库</n-button>
        </div>
      </template>

      <n-data-table
        :columns="columns"
        :data="records"
        :loading="loading"
        :bordered="false"
        :single-line="false"
        size="small"
      />
    </n-card>

    <n-modal
      v-model:show="dialogVisible"
      title="新增出库"
      preset="card"
      style="width: 500px; max-width: calc(100vw - 32px);"
      :mask-closable="false"
    >
      <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" label-width="100">
        <n-form-item label="食材" path="ingredient_id">
          <n-select
            v-model:value="form.ingredient_id"
            :options="ingredientOptions"
            filterable
            placeholder="选择食材"
          />
        </n-form-item>
        <n-form-item label="数量" path="quantity">
          <n-input-number v-model:value="form.quantity" :min="0.01" :precision="2" style="width: 100%;" />
        </n-form-item>
        <n-form-item label="单价">
          <n-input-number v-model:value="form.unit_price" :min="0" :precision="2" style="width: 100%;" />
        </n-form-item>
        <n-form-item label="用途">
          <n-input v-model:value="form.purpose" placeholder="用途" />
        </n-form-item>
        <n-form-item label="部门">
          <n-input v-model:value="form.department" placeholder="部门" />
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
import { stockApi, ingredientApi } from '@/api'
import type { StockOut, Ingredient } from '@/types'

const records = ref<StockOut[]>([])
const ingredientList = ref<Ingredient[]>([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const formRef = ref<FormInst | null>(null)

interface StockOutForm {
  ingredient_id: number | null
  quantity: number
  unit_price: number
  purpose: string
  department: string
  remark: string
}

const form = ref<StockOutForm>({
  ingredient_id: null,
  quantity: 1,
  unit_price: 0,
  purpose: '',
  department: '',
  remark: '',
})

const rules: FormRules = {
  ingredient_id: [{ required: true, message: '请选择食材', trigger: 'change', type: 'number' }],
  quantity: [{ required: true, message: '请输入数量', trigger: ['blur', 'change'], type: 'number' }],
}

const ingredientOptions = computed(() =>
  ingredientList.value.map((i) => ({
    value: i.id,
    label: `${i.name} (库存: ${i.current_stock})`,
  })),
)

const columns: DataTableColumns<StockOut> = [
  { title: '食材', key: 'ingredient_name' },
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
  { title: '用途', key: 'purpose' },
  { title: '部门', key: 'department' },
  {
    title: '出库时间',
    key: 'created_at',
    render: (row) => new Date(row.created_at).toLocaleString('zh-CN'),
  },
]

const message = useMessage()

const loadData = async () => {
  loading.value = true
  try {
    const [recordsData, ingredients] = await Promise.all([
      stockApi.out.list(),
      ingredientApi.list(),
    ])
    records.value = recordsData
    ingredientList.value = ingredients
  } finally {
    loading.value = false
  }
}

const showDialog = () => {
  form.value = {
    ingredient_id: null,
    quantity: 1,
    unit_price: 0,
    purpose: '',
    department: '',
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
    await stockApi.out.create(form.value)
    message.success('出库成功')
    dialogVisible.value = false
    loadData()
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } } }
    message.error(err.response?.data?.detail || '出库失败')
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
