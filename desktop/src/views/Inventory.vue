<template>
  <div>
    <n-card :bordered="false">
      <template #header>
        <div class="card-header">
          <span>库存盘点</span>
          <n-button type="primary" @click="showDialog">新增盘点</n-button>
        </div>
      </template>

      <n-data-table
        :columns="columns"
        :data="records"
        :loading="loading"
        :bordered="false"
        :single-line="false"
        size="small"
        remote
        :pagination="pagination"
        @update:page="handlePageChange"
      />
    </n-card>

    <n-modal
      v-model:show="dialogVisible"
      title="库存盘点"
      preset="card"
      style="width: 500px; max-width: calc(100vw - 32px);"
      :mask-closable="false"
    >
      <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" label-width="120">
        <n-form-item label="食材" path="ingredient_id">
          <n-select
            v-model:value="form.ingredient_id"
            :options="ingredientOptions"
            filterable
            placeholder="选择食材"
            @update:value="onIngredientChange"
          />
        </n-form-item>
        <n-form-item label="系统库存">
          <n-input :value="String(form.system_stock)" disabled />
        </n-form-item>
        <n-form-item label="实际库存" path="actual_stock">
          <n-input-number v-model:value="form.actual_stock" :min="0" :precision="2" style="width: 100%;" />
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
import { ref, computed, onMounted, h } from 'vue'
import { NTag, useMessage, type DataTableColumns, type FormInst, type FormRules, type PaginationProps } from 'naive-ui'
import { stockApi, ingredientApi } from '@/api'
import type { InventoryCheck, Ingredient } from '@/types'

const records = ref<InventoryCheck[]>([])
const ingredientList = ref<Ingredient[]>([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const formRef = ref<FormInst | null>(null)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

interface CheckForm {
  ingredient_id: number | null
  system_stock: number
  actual_stock: number
  remark: string
}

const form = ref<CheckForm>({
  ingredient_id: null,
  system_stock: 0,
  actual_stock: 0,
  remark: '',
})

const rules: FormRules = {
  ingredient_id: [{ required: true, message: '请选择食材', trigger: 'change', type: 'number' }],
  actual_stock: [{ required: true, message: '请输入实际库存', trigger: ['blur', 'change'], type: 'number' }],
}

const ingredientOptions = computed(() =>
  ingredientList.value.map((i) => ({
    value: i.id,
    label: `${i.name} (系统库存: ${i.current_stock})`,
  })),
)

const pagination = computed<PaginationProps>(() => ({
  page: page.value,
  pageSize: pageSize.value,
  itemCount: total.value,
  prefix: ({ itemCount }) => `共 ${itemCount} 条`,
}))

const handlePageChange = (p: number) => {
  page.value = p
  loadRecords()
}

const formatDate = (val: string | null) => {
  if (!val) return ''
  return new Date(val).toLocaleString('zh-CN')
}

const columns: DataTableColumns<InventoryCheck> = [
  { title: '食材', key: 'ingredient_name' },
  {
    title: '系统库存',
    key: 'system_stock',
    render: (row) => Number(row.system_stock),
  },
  {
    title: '实际库存',
    key: 'actual_stock',
    render: (row) => Number(row.actual_stock),
  },
  {
    title: '差异',
    key: 'difference',
    render: (row) => {
      const diff = Number(row.difference)
      return h(
        NTag,
        { type: diff === 0 ? 'success' : 'warning', size: 'small' },
        { default: () => `${diff > 0 ? '+' : ''}${diff}` },
      )
    },
  },
  {
    title: '盘点时间',
    key: 'created_at',
    width: 170,
    render: (row) => formatDate(row.created_at),
  },
]

const message = useMessage()

const loadRecords = async () => {
  loading.value = true
  try {
    const data = await stockApi.check.list({
      skip: (page.value - 1) * pageSize.value,
      limit: pageSize.value,
    })
    records.value = data
    // 后端返回数组无 total，用数组长度推断
    if (data.length < pageSize.value) {
      total.value = (page.value - 1) * pageSize.value + data.length
    } else {
      total.value = page.value * pageSize.value + 1
    }
  } catch {
    message.error('加载盘点记录失败')
    records.value = []
  } finally {
    loading.value = false
  }
}

const loadData = async () => {
  loading.value = true
  try {
    ingredientList.value = await ingredientApi.list()
    await loadRecords()
  } catch {
    message.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const onIngredientChange = (id: number | null) => {
  const item = ingredientList.value.find((i) => i.id === id)
  if (item) {
    form.value.system_stock = item.current_stock
  }
}

const showDialog = () => {
  form.value = {
    ingredient_id: null,
    system_stock: 0,
    actual_stock: 0,
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
    await stockApi.check.create(form.value)
    message.success('盘点成功')
    dialogVisible.value = false
    loadRecords()
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } } }
    message.error(err.response?.data?.detail || '盘点失败')
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
