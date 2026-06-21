<template>
  <div class="trace-page">
    <!-- 搜索区域 -->
    <n-card :bordered="false" class="search-card">
      <div class="search-bar">
        <n-input
          v-model:value="searchCode"
          placeholder="输入追溯码或扫描查询"
          size="large"
          clearable
          style="max-width: 400px;"
          @keyup.enter="handleSearch"
        />
        <n-button type="primary" size="large" @click="handleSearch">查询</n-button>
        <n-button size="large" @click="showGenerate = true">生成追溯码</n-button>
      </div>
    </n-card>

    <!-- 追溯结果 -->
    <n-card v-if="traceResult" :bordered="false" class="result-card">
      <template #header>
        <div class="result-header">
          <span class="trace-code">追溯码: {{ traceResult.trace_code }}</span>
          <n-button size="small" @click="printTrace">打印</n-button>
        </div>
      </template>
      <n-descriptions :column="2" label-placement="left" bordered>
        <n-descriptions-item label="食材名称">{{ traceResult.ingredient_name || '-' }}</n-descriptions-item>
        <n-descriptions-item label="供应商">{{ traceResult.supplier_name || '-' }}</n-descriptions-item>
        <n-descriptions-item label="批次号">{{ traceResult.batch_no || '-' }}</n-descriptions-item>
        <n-descriptions-item label="生产日期">{{ formatDate(traceResult.production_date) }}</n-descriptions-item>
        <n-descriptions-item label="保质期至">{{ formatDate(traceResult.expiry_date) }}</n-descriptions-item>
        <n-descriptions-item label="创建时间">{{ formatDate(traceResult.created_at) }}</n-descriptions-item>
      </n-descriptions>
    </n-card>

    <!-- 追溯记录列表 -->
    <n-card :bordered="false">
      <template #header>
        <span>最近追溯记录</span>
      </template>
      <n-data-table
        :columns="columns"
        :data="traceList"
        :loading="listLoading"
        :bordered="false"
        :single-line="false"
        size="small"
      />
    </n-card>

    <!-- 生成追溯码弹窗 -->
    <n-modal
      v-model:show="showGenerate"
      title="生成追溯码"
      preset="card"
      style="width: 500px; max-width: calc(100vw - 32px);"
      :mask-closable="false"
    >
      <n-form :model="generateForm" label-placement="left" label-width="100">
        <n-form-item label="食材" required>
          <n-select
            v-model:value="generateForm.ingredient_id"
            :options="ingredientOptions"
            placeholder="选择食材"
            filterable
          />
        </n-form-item>
        <n-form-item label="入库记录" required>
          <n-select
            v-model:value="generateForm.stock_in_id"
            :options="stockInOptions"
            placeholder="选择入库记录"
            filterable
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <n-button @click="showGenerate = false">取消</n-button>
          <n-button type="primary" :loading="generating" @click="handleGenerate">生成</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { NButton, useMessage, type DataTableColumns } from 'naive-ui'
import { traceApi, ingredientApi, stockApi } from '@/api'
import type { TraceRecord, Ingredient, StockIn } from '@/types'

const searchCode = ref('')
const traceResult = ref<TraceRecord | null>(null)
const traceList = ref<TraceRecord[]>([])
const loading = ref(false)
const listLoading = ref(false)
const showGenerate = ref(false)
const generating = ref(false)
const ingredients = ref<Ingredient[]>([])
const stockInList = ref<StockIn[]>([])

const generateForm = ref<{ ingredient_id: number | null; stock_in_id: number | null }>({
  ingredient_id: null,
  stock_in_id: null,
})

const ingredientOptions = computed(() =>
  ingredients.value.map((i) => ({ value: i.id, label: i.name })),
)

const stockInOptions = computed(() =>
  stockInList.value.map((s) => ({
    value: s.id,
    label: `${s.ingredient_name} - ${s.batch_no}`,
  })),
)

const formatDate = (val: string | null) => {
  if (!val) return '-'
  const d = new Date(val)
  if (isNaN(d.getTime())) return '-'
  return d.toLocaleString('zh-CN')
}

const columns: DataTableColumns<TraceRecord> = [
  {
    title: '追溯码',
    key: 'trace_code',
    width: 220,
    render: (row) =>
      h(
        NButton,
        {
          text: true,
          type: 'primary',
          onClick: () => {
            searchCode.value = row.trace_code
            handleSearch()
          },
        },
        { default: () => row.trace_code },
      ),
  },
  { title: '食材', key: 'ingredient_name' },
  { title: '供应商', key: 'supplier_name' },
  {
    title: '创建时间',
    key: 'created_at',
    width: 180,
    render: (row) => formatDate(row.created_at),
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    align: 'center',
    render: (row) =>
      h(
        NButton,
        {
          text: true,
          type: 'primary',
          size: 'small',
          onClick: () => {
            searchCode.value = row.trace_code
            handleSearch()
          },
        },
        { default: () => '查看' },
      ),
  },
]

const message = useMessage()

const handleSearch = async () => {
  if (!searchCode.value.trim()) {
    message.warning('请输入追溯码')
    return
  }
  loading.value = true
  try {
    traceResult.value = await traceApi.get(searchCode.value.trim())
  } catch {
    message.error('追溯码无效或查询失败')
    traceResult.value = null
  } finally {
    loading.value = false
  }
}

const handleGenerate = async () => {
  if (!generateForm.value.ingredient_id || !generateForm.value.stock_in_id) {
    message.warning('请选择食材和入库记录')
    return
  }
  generating.value = true
  try {
    const result = await traceApi.generate(generateForm.value.ingredient_id, generateForm.value.stock_in_id)
    message.success(`追溯码生成成功: ${result.trace_code}`)
    showGenerate.value = false
    generateForm.value = { ingredient_id: null, stock_in_id: null }
    loadTraceList()
  } catch {
    message.error('生成失败')
  } finally {
    generating.value = false
  }
}

const printTrace = () => {
  window.print()
}

const loadIngredients = async () => {
  try {
    ingredients.value = await ingredientApi.list()
  } catch {
    message.error('加载食材列表失败')
  }
}

const loadStockIn = async () => {
  try {
    stockInList.value = await stockApi.in.list()
  } catch {
    message.error('加载入库记录失败')
  }
}

const loadTraceList = async () => {
  listLoading.value = true
  try {
    traceList.value = await traceApi.list({ skip: 0, limit: 20 })
  } catch {
    message.error('加载追溯记录失败')
    traceList.value = []
  } finally {
    listLoading.value = false
  }
}

onMounted(() => {
  loadIngredients()
  loadStockIn()
  loadTraceList()
})
</script>

<style scoped>
.trace-page {
  padding-bottom: 20px;
}

.search-card {
  margin-bottom: 16px;
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.result-card {
  margin-bottom: 16px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.trace-code {
  font-size: 18px;
  font-weight: 600;
}
</style>
