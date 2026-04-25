<template>
  <div class="dept-page crud-page">
    <a-card>
      <a-form :model="queryParams" class="crud-filter-form smart-filter-form">
        <a-row :gutter="16" class="filter-row">
          <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
            <a-form-item label="部门名称" class="filter-item">
              <a-input v-model:value="queryParams.name" placeholder="请输入部门名称" allow-clear @pressEnter="handleSearch" />
            </a-form-item>
          </a-col>
          <a-col v-if="userStore.isSuperUser" :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
            <a-form-item label="租户" class="filter-item">
              <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户" allow-clear
                :options="tenantOptions" @change="handleSearch" />
            </a-form-item>
          </a-col>
          <a-col v-bind="getActionColProps" 
            class="filter-actions-col"
            :class="filterItemCount <= 2 ? 'single-line' : 'multi-line'">
            <a-form-item class="filter-actions">
              <a-space>
                <a-button type="primary" @click="handleSearch">
                  <SearchOutlined />
                  查询
                </a-button>
                <a-button @click="handleReset">
                  <ReloadOutlined />
                  重置
                </a-button>
              </a-space>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>

      <div class="table-actions">
        <a-button v-permission="'post/api/v1/dept/create'" type="primary" @click="handleAdd">
          <PlusOutlined />
          新建部门
        </a-button>
      </div>

      <a-table
        class="crud-table"
        :columns="columns"
        :data-source="tableData"
        :loading="loading"
        :pagination="false"
        row-key="id"
        :scroll="{ x: 'max-content' }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'tenant_name'">
            {{ record.tenant_name || '-' }}
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button v-permission="'post/api/v1/dept/update'" type="link" size="small"
                @click="handleEdit(record)">编辑</a-button>
              <a-popconfirm title="确定删除该部门吗？" @confirm="handleDelete(record)">
                <a-button v-permission="'delete/api/v1/dept/delete'" type="link" danger size="small">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 新增/编辑 弹窗 -->
    <a-modal v-model:open="modalVisible" :title="modalTitle" :confirm-loading="modalLoading" @ok="handleSave"
      @cancel="modalVisible = false">
      <a-form ref="modalFormRef" :model="modalForm" :rules="modalRules" :label-col="{ span: 6 }"
        :wrapper-col="{ span: 16 }">
        <!-- 超级管理员：选择所属租户 -->
        <a-form-item v-if="userStore.isSuperUser" label="所属租户" name="tenant_id">
          <a-select v-model:value="modalForm.tenant_id" placeholder="请选择租户" allow-clear :options="tenantOptions" />
        </a-form-item>
        <a-form-item label="父级部门" name="parent_id">
          <a-tree-select v-model:value="modalForm.parent_id" :tree-data="deptOptions"
            :field-names="{ label: 'name', value: 'id', children: 'children' }" placeholder="请选择父级部门" allow-clear
            tree-default-expand-all :disabled="isDisabled" />
        </a-form-item>
        <a-form-item label="部门名称" name="name">
          <a-input v-model:value="modalForm.name" placeholder="请输入部门名称" />
        </a-form-item>
        <a-form-item label="备注" name="desc">
          <a-textarea v-model:value="modalForm.desc" :rows="3" />
        </a-form-item>
        <a-form-item label="排序" name="order">
          <a-input-number v-model:value="modalForm.order" :min="0" style="width: 100%" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '@/store'
import api from '@/api'

const userStore = useUserStore()

const queryParams = reactive<any>({
  name: '',
  tenant_id: undefined,
})

// 计算表单项数量（用于控制按钮布局）
const filterItemCount = computed(() => {
  // 基础字段：部门名称
  let count = 1
  // 超级管理员额外显示租户字段
  if (userStore.isSuperUser) count++
  return count
})

// 操作按钮列的栅格配置
// 单行时宽度自适应，多行时占据标准宽度
const getActionColProps = computed(() => {
  const isSingleLine = filterItemCount.value <= 2
  if (isSingleLine) {
    // 单行模式：宽度自适应，不设置固定宽度
    return {
      xs: 24,
      sm: 12,
      md: 'auto',
      lg: 'auto',
      xl: 'auto'
    }
  }
  // 多行模式：标准宽度
  return {
    xs: 24,
    sm: 12,
    md: 8,
    lg: 6,
    xl: 6
  }
})

const loading = ref(false)
const tableData = ref<any[]>([])
const deptOptions = ref<any[]>([])
const tenantOptions = ref<any[]>([])

const columns = computed(() => [
  { title: '部门名称', dataIndex: 'name', key: 'name', width: 200, resizable: true },
  ...(userStore.isSuperUser ? [{ title: '所属租户', key: 'tenant_name', width: 150, resizable: true }] : []),
  { title: '备注', dataIndex: 'desc', key: 'desc', width: 250, ellipsis: true, resizable: true },
  { title: '操作', key: 'action', width: 150, fixed: 'right' },
])

const modalVisible = ref(false)
const modalLoading = ref(false)
const modalAction = ref<'add' | 'edit'>('add')
const modalTitle = computed(() => (modalAction.value === 'add' ? '新增部门' : '编辑部门'))
const modalFormRef = ref()
const initForm = {
  tenant_id: undefined,
  parent_id: undefined,
  name: '',
  desc: '',
  order: 0,
}
const modalForm = ref({ ...initForm })
const isDisabled = ref(false)

const modalRules = {
  name: [{ required: true, message: '请输入部门名称', trigger: ['input', 'blur', 'change'] }],
}

async function loadData() {
  loading.value = true
  try {
    const params: any = {}
    if (queryParams.tenant_id) params.tenant_id = queryParams.tenant_id
    const res: any = await api.getDepts(params)
    tableData.value = res.data || []
  } finally {
    loading.value = false
  }
}

async function loadDepts() {
  const params: any = {}
  if (queryParams.tenant_id) params.tenant_id = queryParams.tenant_id
  const res: any = await api.getDepts(params)
  deptOptions.value = res.data || []
}

async function loadTenants() {
  if (!userStore.isSuperUser) return
  const res: any = await api.getTenantSelect()
  tenantOptions.value = (res.data || []).map((item: any) => ({ label: item.name, value: item.id }))
}

function handleSearch() {
  loadData()
  loadDepts()
}

function handleReset() {
  queryParams.name = ''
  queryParams.tenant_id = undefined
  handleSearch()
}

function handleAdd() {
  modalAction.value = 'add'
  modalForm.value = { ...initForm }
  isDisabled.value = false
  modalVisible.value = true
}

function handleEdit(record: any) {
  modalAction.value = 'edit'
  if (record.parent_id === 0) {
    isDisabled.value = true
  } else {
    isDisabled.value = false
  }
  modalForm.value = { ...record }
  modalVisible.value = true
}

async function handleSave() {
  try {
    await modalFormRef.value.validate()
    modalLoading.value = true
    const apiFn = modalAction.value === 'add' ? api.createDept : api.updateDept
    const res: any = await apiFn(modalForm.value)
    if (res.code === 200) {
      window.$message?.success(modalAction.value === 'add' ? '新增成功' : '编辑成功')
      modalVisible.value = false
      loadData()
      loadDepts()
    }
  } catch (error: any) {
    if (error.errorFields) return
    console.error('保存失败', error)
  } finally {
    modalLoading.value = false
  }
}

async function handleDelete(record: any) {
  try {
    const res: any = await api.deleteDept({ dept_id: record.id })
    if (res.code === 200) {
      window.$message?.success('删除成功')
      loadData()
      loadDepts()
    }
  } catch (error) {
    console.error('删除失败', error)
  }
}

onMounted(() => {
  loadData()
  loadDepts()
  loadTenants()
})
</script>

<style scoped lang="less">
.dept-page {
  .table-actions {
    margin-bottom: 16px;
  }
}
</style>
