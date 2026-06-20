<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>食材管理</span>
          <el-button type="primary" @click="showAddDialog">添加食材</el-button>
        </div>
      </template>
      
      <el-table :data="ingredients" v-loading="loading">
        <el-table-column prop="name" label="食材名称" />
        <el-table-column prop="code" label="编码" />
        <el-table-column prop="category_id" label="分类" />
        <el-table-column prop="unit" label="单位" />
        <el-table-column prop="specification" label="规格" />
        <el-table-column prop="current_stock" label="当前库存">
          <template #default="{ row }">
            <el-tag :type="row.current_stock <= row.safety_stock ? 'danger' : 'success'">
              {{ row.current_stock }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="safety_stock" label="安全库存" />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="editIngredient(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteIngredient(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑食材' : '添加食材'" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="食材名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="编码" prop="code">
          <el-input v-model="form.code" />
        </el-form-item>
        <el-form-item label="分类" prop="category_id">
          <el-select v-model="form.category_id" style="width: 100%">
            <el-option label="蔬菜类" :value="1" />
            <el-option label="肉类" :value="2" />
            <el-option label="粮油类" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="单位" prop="unit">
          <el-input v-model="form.unit" placeholder="如：斤、个、袋" />
        </el-form-item>
        <el-form-item label="规格">
          <el-input v-model="form.specification" />
        </el-form-item>
        <el-form-item label="安全库存">
          <el-input-number v-model="form.safety_stock" :min="0" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getIngredients, createIngredient, updateIngredient, deleteIngredient as apiDelete } from '../api'

const ingredients = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()
const form = ref({
  name: '',
  code: '',
  category_id: 1,
  unit: '',
  specification: '',
  safety_stock: 0,
  org_id: 1
})

const rules = {
  name: [{ required: true, message: '请输入食材名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入编码', trigger: 'blur' }],
  category_id: [{ required: true, message: '请选择分类', trigger: 'change' }],
  unit: [{ required: true, message: '请输入单位', trigger: 'blur' }]
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getIngredients()
    ingredients.value = res.data
  } finally {
    loading.value = false
  }
}

const showAddDialog = () => {
  isEdit.value = false
  form.value = { name: '', code: '', category_id: 1, unit: '', specification: '', safety_stock: 0, org_id: 1 }
  dialogVisible.value = true
}

const editIngredient = (row) => {
  isEdit.value = true
  form.value = { ...row }
  dialogVisible.value = true
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  try {
    if (isEdit.value) {
      await updateIngredient(form.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createIngredient(form.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

const deleteIngredient = async (id) => {
  try {
    await ElMessageBox.confirm('确认删除该食材？', '提示', { type: 'warning' })
    await apiDelete(id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
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
