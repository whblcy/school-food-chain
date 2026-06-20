<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>出库管理</span>
          <el-button type="primary" @click="showDialog">新增出库</el-button>
        </div>
      </template>
      
      <el-table :data="records" v-loading="loading">
        <el-table-column prop="ingredient_name" label="食材" />
        <el-table-column prop="quantity" label="数量" />
        <el-table-column prop="unit_price" label="单价" />
        <el-table-column prop="total_price" label="总价" />
        <el-table-column prop="purpose" label="用途" />
        <el-table-column prop="department" label="部门" />
        <el-table-column prop="created_at" label="出库时间" />
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新增出库" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="食材" prop="ingredient_id">
          <el-select v-model="form.ingredient_id" style="width: 100%">
            <el-option 
              v-for="item in ingredientList" 
              :key="item.id" 
              :label="`${item.name} (库存: ${item.current_stock})`" 
              :value="item.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="数量" prop="quantity">
          <el-input-number v-model="form.quantity" :min="0.01" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="单价">
          <el-input-number v-model="form.unit_price" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="用途">
          <el-input v-model="form.purpose" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="form.department" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getStockOut, stockOut, getIngredients } from '../api'

const records = ref([])
const ingredientList = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const formRef = ref()
const form = ref({
  ingredient_id: null,
  quantity: 1,
  unit_price: 0,
  purpose: '',
  department: '',
  remark: ''
})

const rules = {
  ingredient_id: [{ required: true, message: '请选择食材', trigger: 'change' }],
  quantity: [{ required: true, message: '请输入数量', trigger: 'blur' }]
}

const loadData = async () => {
  loading.value = true
  try {
    const [recordsRes, ingredientsRes] = await Promise.all([
      getStockOut(),
      getIngredients()
    ])
    records.value = recordsRes.data
    ingredientList.value = ingredientsRes.data
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
    remark: ''
  }
  dialogVisible.value = true
}

const submit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  try {
    await stockOut(form.value)
    ElMessage.success('出库成功')
    dialogVisible.value = false
    loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '出库失败')
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
