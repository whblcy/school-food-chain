<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>供应商管理</span>
          <el-button type="primary" @click="showDialog">添加供应商</el-button>
        </div>
      </template>
      
      <el-table :data="suppliers" v-loading="loading">
        <el-table-column prop="name" label="供应商名称" />
        <el-table-column prop="code" label="编码" />
        <el-table-column prop="contact_person" label="联系人" />
        <el-table-column prop="phone" label="电话" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : row.status === 'suspended' ? 'warning' : 'danger'">
              {{ statusMap[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="rating" label="评分">
          <template #default="{ row }">
            <el-rate v-model="row.rating" disabled />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="editSupplier(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteSupplier(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑供应商' : '添加供应商'" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="编码" prop="code">
          <el-input v-model="form.code" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="form.contact_person" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.address" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="正常" value="active" />
            <el-option label="暂停" value="suspended" />
            <el-option label="黑名单" value="blacklisted" />
          </el-select>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSuppliers, createSupplier, updateSupplier, deleteSupplier as apiDelete } from '../api'

const suppliers = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()
const form = ref({
  name: '',
  code: '',
  contact_person: '',
  phone: '',
  email: '',
  address: '',
  status: 'active'
})

const statusMap = {
  active: '正常',
  suspended: '暂停',
  blacklisted: '黑名单'
}

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入编码', trigger: 'blur' }]
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getSuppliers()
    suppliers.value = res.data
  } finally {
    loading.value = false
  }
}

const showDialog = () => {
  isEdit.value = false
  form.value = { name: '', code: '', contact_person: '', phone: '', email: '', address: '', status: 'active' }
  dialogVisible.value = true
}

const editSupplier = (row) => {
  isEdit.value = true
  form.value = { ...row }
  dialogVisible.value = true
}

const submit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  try {
    if (isEdit.value) {
      await updateSupplier(form.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createSupplier(form.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const deleteSupplier = async (id) => {
  try {
    await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
    await apiDelete(id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
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
