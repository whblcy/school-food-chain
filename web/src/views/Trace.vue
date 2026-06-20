<template>
  <div class="trace-page">
    <!-- 搜索区域 -->
    <el-card class="search-card">
      <el-input
        v-model="searchCode"
        placeholder="输入追溯码或扫描查询"
        size="large"
        clearable
        style="width: 400px"
        @keyup.enter="handleSearch"
      >
        <template #append>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>查询
          </el-button>
        </template>
      </el-input>
      <el-button size="large" style="margin-left: 12px" @click="showGenerate = true">
        <el-icon><Plus /></el-icon>生成追溯码
      </el-button>
    </el-card>

    <!-- 追溯结果 -->
    <el-card v-if="traceResult" class="result-card" v-loading="loading">
      <template #header>
        <div class="result-header">
          <div>
            <span class="trace-code">追溯码: {{ traceResult.trace_code }}</span>
            <el-tag :type="traceResult.status === 'active' ? 'success' : 'info'" style="margin-left: 12px">
              {{ traceResult.status === 'active' ? '有效' : '已失效' }}
            </el-tag>
          </div>
          <el-button size="small" @click="printTrace">
            <el-icon><Printer /></el-icon>打印
          </el-button>
        </div>
      </template>

      <el-steps :active="4" align-center class="trace-steps">
        <el-step title="采购入库" :description="traceResult.stock_in_date">
          <template #icon>
            <el-icon :size="24" color="#67C23A"><CircleCheck /></el-icon>
          </template>
        </el-step>
        <el-step title="质检审核" :description="traceResult.inspector">
          <template #icon>
            <el-icon :size="24" color="#67C23A"><CircleCheck /></el-icon>
          </template>
        </el-step>
        <el-step title="库存管理" :description="traceResult.storage_location">
          <template #icon>
            <el-icon :size="24" color="#67C23A"><CircleCheck /></el-icon>
          </template>
        </el-step>
        <el-step title="出库使用" :description="traceResult.stock_out_date || '待出库'">
          <template #icon>
            <el-icon :size="24" :color="traceResult.stock_out_date ? '#67C23A' : '#909399'">
              <CircleCheck v-if="traceResult.stock_out_date" />
              <Timer v-else />
            </el-icon>
          </template>
        </el-step>
      </el-steps>

      <el-divider />

      <el-descriptions :column="2" border>
        <el-descriptions-item label="食材名称">{{ traceResult.ingredient_name }}</el-descriptions-item>
        <el-descriptions-item label="品类">{{ traceResult.category }}</el-descriptions-item>
        <el-descriptions-item label="供应商">{{ traceResult.supplier_name }}</el-descriptions-item>
        <el-descriptions-item label="联系人">{{ traceResult.supplier_contact }}</el-descriptions-item>
        <el-descriptions-item label="入库数量">{{ traceResult.quantity }} {{ traceResult.unit }}</el-descriptions-item>
        <el-descriptions-item label="入库单价">¥{{ traceResult.unit_price?.toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="生产日期">{{ traceResult.production_date }}</el-descriptions-item>
        <el-descriptions-item label="保质期至">{{ traceResult.expiry_date }}</el-descriptions-item>
        <el-descriptions-item label="质检员1">{{ traceResult.inspector1_name }}</el-descriptions-item>
        <el-descriptions-item label="质检员2">{{ traceResult.inspector2_name }}</el-descriptions-item>
        <el-descriptions-item label="存放位置" :span="2">{{ traceResult.storage_location }}</el-descriptions-item>
        <el-descriptions-item label="批次备注" :span="2">{{ traceResult.batch_notes || '无' }}</el-descriptions-item>
      </el-descriptions>

      <div class="qr-section" v-if="traceResult.qr_url">
        <div class="qr-label">扫码追溯</div>
        <el-image :src="traceResult.qr_url" style="width: 160px; height: 160px" fit="contain">
          <template #error>
            <div class="qr-placeholder">
              <el-icon :size="48" color="#909399"><Picture /></el-icon>
              <div>QR Code</div>
            </div>
          </template>
        </el-image>
      </div>
    </el-card>

    <!-- 追溯记录列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>最近追溯记录</span>
        </div>
      </template>
      <el-table :data="traceList" stripe>
        <el-table-column prop="trace_code" label="追溯码" width="200">
          <template #default="{ row }">
            <el-link type="primary" @click="searchCode = row.trace_code; handleSearch()">
              {{ row.trace_code }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="ingredient_name" label="食材" />
        <el-table-column prop="supplier_name" label="供应商" />
        <el-table-column prop="stock_in_date" label="入库日期" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '有效' : '已失效' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="searchCode = row.trace_code; handleSearch()">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 生成追溯码弹窗 -->
    <el-dialog v-model="showGenerate" title="生成追溯码" width="500px">
      <el-form :model="generateForm" label-width="100px">
        <el-form-item label="食材" required>
          <el-select v-model="generateForm.ingredient_id" placeholder="选择食材" style="width: 100%">
            <el-option
              v-for="item in ingredients"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="入库记录" required>
          <el-select v-model="generateForm.stock_in_id" placeholder="选择入库记录" style="width: 100%">
            <el-option
              v-for="item in stockInList"
              :key="item.id"
              :label="`${item.ingredient_name} - ${item.stock_in_date}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGenerate = false">取消</el-button>
        <el-button type="primary" @click="handleGenerate" :loading="generating">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Plus, Printer, CircleCheck, Timer, Picture } from '@element-plus/icons-vue'
import { getTrace, generateTrace, getIngredients, getStockIn } from '../api'

const searchCode = ref('')
const traceResult = ref(null)
const traceList = ref([])
const loading = ref(false)
const showGenerate = ref(false)
const generating = ref(false)
const ingredients = ref([])
const stockInList = ref([])

const generateForm = ref({
  ingredient_id: null,
  stock_in_id: null
})

const handleSearch = async () => {
  if (!searchCode.value.trim()) {
    ElMessage.warning('请输入追溯码')
    return
  }
  loading.value = true
  try {
    const res = await getTrace(searchCode.value.trim())
    traceResult.value = res.data
  } catch (e) {
    ElMessage.error('追溯码无效或查询失败')
    traceResult.value = null
  } finally {
    loading.value = false
  }
}

const handleGenerate = async () => {
  if (!generateForm.value.ingredient_id || !generateForm.value.stock_in_id) {
    ElMessage.warning('请选择食材和入库记录')
    return
  }
  generating.value = true
  try {
    const res = await generateTrace(generateForm.value.ingredient_id, generateForm.value.stock_in_id)
    ElMessage.success(`追溯码生成成功: ${res.data.trace_code}`)
    showGenerate.value = false
    generateForm.value = { ingredient_id: null, stock_in_id: null }
    loadTraceList()
  } catch (e) {
    ElMessage.error('生成失败')
  } finally {
    generating.value = false
  }
}

const printTrace = () => {
  window.print()
}

const loadIngredients = async () => {
  try {
    const res = await getIngredients()
    ingredients.value = res.data.items || []
  } catch (e) {}
}

const loadStockIn = async () => {
  try {
    const res = await getStockIn()
    stockInList.value = res.data || []
  } catch (e) {}
}

const loadTraceList = () => {
  // 模拟数据
  traceList.value = [
    { trace_code: 'TR-20250620-A1B2C3', ingredient_name: '东北大米', supplier_name: '绿源粮油', stock_in_date: '2025-06-18', status: 'active' },
    { trace_code: 'TR-20250619-D4E5F6', ingredient_name: '五花肉', supplier_name: '鲜肉联', stock_in_date: '2025-06-17', status: 'active' },
    { trace_code: 'TR-20250615-G7H8I9', ingredient_name: '西红柿', supplier_name: '蔬菜基地A', stock_in_date: '2025-06-15', status: 'consumed' },
  ]
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
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.result-card {
  margin-bottom: 20px;
}
.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.trace-code {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
}
.trace-steps {
  margin: 24px 0;
}
.qr-section {
  margin-top: 24px;
  text-align: center;
  padding: 20px;
  background: #f5f5f7;
  border-radius: 8px;
}
.qr-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 12px;
}
.qr-placeholder {
  width: 160px;
  height: 160px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 1px dashed #dcdfe6;
  border-radius: 4px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
