<template>
  <div>
    <n-card :bordered="false">
      <template #header>
        <div class="card-header">
          <span>食材管理</span>
          <n-button type="primary" @click="showAddDialog">
            <template #icon><span>➕</span></template>
            添加食材
          </n-button>
        </div>
      </template>

      <n-data-table
        :columns="columns"
        :data="pagedIngredients"
        :loading="loading"
        :bordered="false"
        :single-line="false"
        remote
        :pagination="pagination"
        @update:page="handlePageChange"
      />
    </n-card>

    <!-- 添加/编辑对话框 -->
    <n-modal
      v-model:show="dialogVisible"
      :title="isEdit ? '编辑食材' : '添加食材'"
      preset="card"
      style="width: 500px; max-width: calc(100vw - 32px);"
      :mask-closable="false"
    >
      <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" label-width="100">
        <n-form-item label="食材名称" path="name">
          <n-input v-model:value="form.name" placeholder="请输入食材名称" />
        </n-form-item>
        <n-form-item label="编码" path="code">
          <n-input v-model:value="form.code" placeholder="请输入编码" />
        </n-form-item>
        <n-form-item label="分类" path="category_id">
          <n-select
            v-model:value="form.category_id"
            placeholder="选择分类"
            :options="categoryOptions"
            clearable
          />
        </n-form-item>
        <n-form-item label="供应商" path="supplier_id">
          <n-select
            v-model:value="form.supplier_id"
            placeholder="选择供应商"
            :options="supplierOptions"
            clearable
            filterable
          />
        </n-form-item>
        <n-form-item label="单位" path="unit">
          <n-input v-model:value="form.unit" placeholder="如：斤、个、袋" />
        </n-form-item>
        <n-form-item label="规格">
          <n-input v-model:value="form.specification" placeholder="规格" />
        </n-form-item>
        <n-form-item label="安全库存">
          <n-input-number v-model:value="form.safety_stock" :min="0" style="width: 100%;" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <n-button @click="dialogVisible = false">取消</n-button>
          <n-button type="primary" :loading="submitting" @click="submitForm">确定</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { NTag, NButton, NSpace, useMessage, type DataTableColumns, type FormInst, type FormRules, type PaginationProps } from 'naive-ui'
import { ingredientApi, supplierApi } from '@/api'
import type { Ingredient, Supplier } from '@/types'

const ingredients = ref<Ingredient[]>([])
const supplierList = ref<Supplier[]>([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref<FormInst | null>(null)
const currentId = ref<number | null>(null)
const page = ref(1)
const pageSize = ref(10)

interface IngredientForm {
  name: string
  code: string
  category_id: number | null
  supplier_id: number | null
  unit: string
  specification: string
  safety_stock: number
}

const form = ref<IngredientForm>({
  name: '',
  code: '',
  category_id: null,
  supplier_id: null,
  unit: '',
  specification: '',
  safety_stock: 0,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入食材名称', trigger: ['blur', 'input'] }],
  code: [{ required: true, message: '请输入编码', trigger: ['blur', 'input'] }],
  unit: [{ required: true, message: '请输入单位', trigger: ['blur', 'input'] }],
}

// 从已有食材中提取去重的分类列表（后端无独立分类端点）
const categoryOptions = computed(() => {
  const map = new Map<number, string>()
  ingredients.value.forEach((item) => {
    if (item.category_id && item.category_name && !map.has(item.category_id)) {
      map.set(item.category_id, item.category_name)
    }
  })
  return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
})

const supplierOptions = computed(() =>
  supplierList.value.map((s) => ({ value: s.id, label: s.name })),
)

// 客户端分页
const total = computed(() => ingredients.value.length)
const pagedIngredients = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return ingredients.value.slice(start, start + pageSize.value)
})

const pagination = computed<PaginationProps>(() => ({
  page: page.value,
  pageSize: pageSize.value,
  itemCount: total.value,
  showSizePicker: false,
  prefix: ({ itemCount }) => `共 ${itemCount} 条`,
}))

const handlePageChange = (p: number) => {
  page.value = p
}

const columns: DataTableColumns<Ingredient> = [
  { title: '食材名称', key: 'name' },
  { title: '编码', key: 'code' },
  { title: '分类', key: 'category_name' },
  { title: '供应商', key: 'supplier_name' },
  { title: '单位', key: 'unit' },
  { title: '规格', key: 'specification' },
  {
    title: '当前库存',
    key: 'current_stock',
    render: (row) =>
      h(
        NTag,
        {
          type: Number(row.current_stock) <= Number(row.safety_stock) ? 'error' : 'success',
          size: 'small',
        },
        { default: () => Number(row.current_stock) },
      ),
  },
  { title: '安全库存', key: 'safety_stock' },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    render: (row) =>
      h(NSpace, { size: 8 }, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => editIngredient(row) }, { default: () => '编辑' }),
          h(
            NButton,
            { size: 'small', type: 'error', onClick: () => deleteIngredient(row.id) },
            { default: () => '删除' },
          ),
        ],
      }),
  },
]

const message = useMessage()

const loadData = async () => {
  loading.value = true
  try {
    ingredients.value = await ingredientApi.list()
  } catch {
    message.error('加载食材列表失败')
    ingredients.value = []
  } finally {
    loading.value = false
  }
}

const loadSuppliers = async () => {
  try {
    supplierList.value = await supplierApi.list()
  } catch {
    supplierList.value = []
  }
}

const showAddDialog = () => {
  isEdit.value = false
  currentId.value = null
  form.value = {
    name: '',
    code: '',
    category_id: null,
    supplier_id: null,
    unit: '',
    specification: '',
    safety_stock: 0,
  }
  dialogVisible.value = true
}

const editIngredient = (row: Ingredient) => {
  isEdit.value = true
  currentId.value = row.id
  form.value = {
    name: row.name || '',
    code: row.code || '',
    category_id: row.category_id,
    supplier_id: row.supplier_id,
    unit: row.unit || '',
    specification: row.specification || '',
    safety_stock: Number(row.safety_stock) || 0,
  }
  dialogVisible.value = true
}

const submitForm = async () => {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    if (isEdit.value && currentId.value !== null) {
      await ingredientApi.update(currentId.value, form.value)
      message.success('更新成功')
    } else {
      await ingredientApi.create(form.value)
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

const deleteIngredient = async (id: number) => {
  if (!confirm('确认删除该食材？')) return
  try {
    await ingredientApi.delete(id)
    message.success('删除成功')
    loadData()
  } catch {
    message.error('删除失败')
  }
}

onMounted(() => {
  loadData()
  loadSuppliers()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
