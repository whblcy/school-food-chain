<template>
  <div class="audit-page">
    <n-card :bordered="false">
      <template #header>
        <div class="card-header">
          <span>审计日志</span>
          <n-button quaternary size="small" @click="loadData">
            <template #icon><n-icon :component="RefreshIcon" /></template>
            刷新
          </n-button>
        </div>
      </template>

      <!-- 筛选区 -->
      <n-form inline :model="filters" label-placement="left" class="filter-form">
        <n-form-item label="操作">
          <n-select
            v-model:value="filters.action"
            :options="actionOptions"
            clearable
            placeholder="全部操作"
            style="width: 160px"
          />
        </n-form-item>
        <n-form-item label="目标类型">
          <n-select
            v-model:value="filters.target_type"
            :options="targetTypeOptions"
            clearable
            placeholder="全部类型"
            style="width: 160px"
          />
        </n-form-item>
        <n-form-item label="用户名">
          <n-input
            v-model:value="filters.username"
            clearable
            placeholder="按用户名搜索"
            style="width: 180px"
            @keyup.enter="onSearch"
          />
        </n-form-item>
        <n-form-item :show-label="false">
          <n-space>
            <n-button type="primary" @click="onSearch">查询</n-button>
            <n-button @click="onReset">重置</n-button>
          </n-space>
        </n-form-item>
      </n-form>

      <!-- 日志表格 -->
      <n-data-table
        :columns="columns"
        :data="records"
        :loading="loading"
        :bordered="false"
        :single-line="false"
        size="small"
        :pagination="pagination"
        :row-key="(row: AuditLog) => row.id"
        @update:page="handlePageChange"
      />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { NButton, NDataTable, NIcon, NSpace, NTag, type DataTableColumns, type PaginationProps } from 'naive-ui'
import { useMessage } from 'naive-ui'
import { auditApi } from '@/api'
import type { AuditLog } from '@/types'

const message = useMessage()

const records = ref<AuditLog[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const filters = ref({
  action: null as string | null,
  target_type: null as string | null,
  username: '',
})

// 操作类型选项
const actionOptions = [
  { label: '登录', value: 'login' },
  { label: '登出', value: 'logout' },
  { label: '创建', value: 'create' },
  { label: '更新', value: 'update' },
  { label: '删除', value: 'delete' },
  { label: '入库', value: 'stock_in' },
  { label: '出库', value: 'stock_out' },
  { label: '盘点', value: 'inventory_check' },
  { label: '生成追溯', value: 'trace_generate' },
  { label: '加入黑名单', value: 'blacklist' },
  { label: '移出黑名单', value: 'unblacklist' },
]

// 目标类型选项
const targetTypeOptions = [
  'user', 'ingredient', 'supplier', 'stock_in', 'stock_out',
  'inventory_check', 'trace', 'org',
].map((v) => ({ label: v, value: v }))

// 操作类型中文映射
const actionLabel = (action: string): string => {
  const item = actionOptions.find((o) => o.value === action)
  return item ? item.label : action
}

// 操作类型对应的标签颜色
const actionTagType = (action: string): 'default' | 'success' | 'warning' | 'error' | 'info' => {
  const map: Record<string, 'default' | 'success' | 'warning' | 'error' | 'info'> = {
    login: 'success',
    logout: 'info',
    create: 'success',
    update: 'warning',
    delete: 'error',
    stock_in: 'info',
    stock_out: 'info',
    inventory_check: 'warning',
    trace_generate: 'default',
    blacklist: 'error',
    unblacklist: 'success',
  }
  return map[action] || 'default'
}

// 格式化日期显示
const formatDate = (val: string | null): string => {
  if (!val) return ''
  return new Date(val).toLocaleString('zh-CN')
}

// JSON 美化显示
const formatJson = (val: unknown): string => {
  if (val === null || val === undefined || val === '') return '-'
  if (typeof val === 'string') {
    try {
      return JSON.stringify(JSON.parse(val), null, 2)
    } catch {
      return val
    }
  }
  try {
    return JSON.stringify(val, null, 2)
  } catch {
    return String(val)
  }
}

// 内联刷新图标
const RefreshIcon = () =>
  h('svg', { viewBox: '0 0 24 24', width: '14', height: '14' }, [
    h('path', {
      fill: 'currentColor',
      d: 'M17.65 6.35A7.958 7.958 0 0 0 12 4a8 8 0 1 0 7.74 10h-2.08A6 6 0 1 1 12 6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z',
    }),
  ])

// 表格列定义
const columns: DataTableColumns<AuditLog> = [
  {
    type: 'expand',
    expandable: () => true,
    renderExpand: (row: AuditLog) =>
      h('div', { class: 'expand-content' }, [
        h('div', { class: 'expand-item' }, [
          h('div', { class: 'expand-label' }, '旧值：'),
          h('pre', { class: 'json-box' }, formatJson(row.old_value)),
        ]),
        h('div', { class: 'expand-item' }, [
          h('div', { class: 'expand-label' }, '新值：'),
          h('pre', { class: 'json-box' }, formatJson(row.new_value)),
        ]),
        row.user_agent
          ? h('div', { class: 'expand-item' }, [
              h('div', { class: 'expand-label' }, 'User-Agent：'),
              h('span', row.user_agent),
            ])
          : null,
      ]),
  },
  {
    title: '时间',
    key: 'created_at',
    width: 170,
    render: (row) => formatDate(row.created_at),
  },
  { title: '用户名', key: 'username', width: 120 },
  {
    title: '操作',
    key: 'action',
    width: 140,
    render: (row) =>
      h(NTag, { type: actionTagType(row.action), size: 'small', bordered: false }, { default: () => actionLabel(row.action) }),
  },
  { title: '目标类型', key: 'target_type', width: 140 },
  { title: '目标ID', key: 'target_id', width: 100 },
  { title: 'IP地址', key: 'ip_address', width: 140 },
]

// 分页配置
const pagination = computed<PaginationProps>(() => ({
  page: page.value,
  pageSize: pageSize.value,
  itemCount: total.value,
  showSizePicker: false,
  prefix: ({ itemCount }: { itemCount: number | undefined }) => `共 ${itemCount ?? 0} 条`,
}))

const handlePageChange = (p: number) => {
  page.value = p
  loadData()
}

// 加载审计日志
const loadData = async () => {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      skip: (page.value - 1) * pageSize.value,
      limit: pageSize.value,
    }
    if (filters.value.action) params.action = filters.value.action
    if (filters.value.target_type) params.target_type = filters.value.target_type
    if (filters.value.username) params.username = filters.value.username

    const res = await auditApi.list(params)
    records.value = res || []
    // 后端返回数组，无 total 字段；用数组长度推断是否末页
    if (res.length < pageSize.value) {
      total.value = (page.value - 1) * pageSize.value + res.length
    } else {
      total.value = page.value * pageSize.value + 1
    }
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } } }
    message.error(err.response?.data?.detail || '加载审计日志失败')
    records.value = []
  } finally {
    loading.value = false
  }
}

// 点击查询
const onSearch = () => {
  page.value = 1
  loadData()
}

// 重置筛选
const onReset = () => {
  filters.value = { action: null, target_type: null, username: '' }
  page.value = 1
  loadData()
}

onMounted(loadData)
</script>

<style scoped lang="scss">
.audit-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .filter-form {
    margin-bottom: 16px;
  }
  :deep(.expand-content) {
    padding: 12px 24px;
    background-color: var(--n-color, #fafafa);
  }
  .expand-item {
    margin-bottom: 12px;
  }
  .expand-label {
    font-weight: 600;
    color: var(--n-text-color-3, #606266);
    margin-bottom: 4px;
  }
  .json-box {
    background-color: var(--n-color-target, #f5f5f7);
    padding: 12px;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    color: var(--n-text-color, #1d1d1f);
    margin: 0;
    max-height: 240px;
    overflow: auto;
    white-space: pre-wrap;
    word-break: break-all;
  }
}
</style>
