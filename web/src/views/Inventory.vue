<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>库存盘点</span>
          <el-button type="primary" @click="showDialog">新增盘点</el-button>
        </div>
      </template>
      
      <el-table :data="records" v-loading="loading">
        <el-table-column prop="ingredient_name" label="食材" />
        <el-table-column prop="system_stock" label="系统库存" />
        <el-table-column prop="actual_stock" label="实际库存" />
        <el-table-column prop="difference" label="差异">
          <template #default="{ row }">
            <el-tag :type="row.difference === 0 ? 'success' : 'warning'">
              {{ row.difference > 0 ? '+' : '' }}{{ row.difference }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="盘点时间" />
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="库存盘点" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="食材" prop="ingredient_id">
          <el-select v-model="form.ingredient_id" style="width: 100%" @change="onIngredientChange">
            <el-option 
              v-for="item in ingredientList" 
              :key="item.id" 
              :label="`${item.name} (系统库存: ${item.current_stock})`" 
              :value="item.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="系统库存">
          <el-input v-model="form.system_stock" disabled />
        </el-form-item>
        <el-form-item label="实际库存" prop="actual_stock">
          <el-input-number v-model="form.actual_stock" :min="0" :precision="2" style="width: 100%" />
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
import { inventoryCheck, getIngredients } from '../api'

const records = ref([])
const ingredientList = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const formRef = ref()
const form = ref({
  ingredient_id: null,
  system_stock: 0,
  actual_stock: 0,
  remark: ''
})

const rules = {
  ingredient_id: [{ required: true, message: '请选择食材', trigger: 'change' }],
  actual_stock: [{ required: true, message: '请输入实际库存', trigger: 'blur' }]
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getIngredients()
    ingredientList.value = res.data
    // 这里应该从API获取盘点记录
    records.value = []
  } finally {
    loading.value = false
  }
}

const onIngredientChange = (id) => {
  const item = ingredientList.value.find(i => i.id === id)
  if (item) {
    form.value.system_stock = item.current_stock
  }
}

const showDialog = () => {
  form.value = {
    ingredient_id: null,
    system_stock: 0,
    actual_stock: 0,
    remark: ''
  }
  dialogVisible.value = true
}

const submit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  try {
    await inventoryCheck(form.value)
    ElMessage.success('盘点成功')
    dialogVisible.value = false
    loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '盘点失败')
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
