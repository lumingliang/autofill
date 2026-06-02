<template>
  <div class="dept-page">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading" :pagination="false"
      :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal :modal-title="modalTitle"
      :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules" @search="handleSearch"
      @reset="handleReset" @modal-ok="handleSave">
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="部门名称" class="filter-item">
            <a-input v-model:value="queryParams.name" placeholder="请输入部门名称" allow-clear @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
      </template>

      <!-- 操作按钮 -->
      <template #actions>
        <a-button v-permission="'post/api/v1/dept/create'" type="primary" @click="handleAdd">
          <PlusOutlined />
          新建部门
        </a-button>
      </template>

      <!-- 表格列自定义 -->
      <template #bodyCell="{ column, record }">
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

      <!-- 弹窗表单 -->
      <template #modal-form="{ form }">
        <a-form-item label="父级部门" name="parent_id">
          <a-tree-select v-model:value="form.parent_id" :tree-data="deptOptions"
            :field-names="{ label: 'name', value: 'id', children: 'children' }" placeholder="请选择父级部门" allow-clear
            tree-default-expand-all :disabled="isDisabled" />
        </a-form-item>
        <a-form-item label="部门名称" name="name">
          <a-input v-model:value="form.name" placeholder="请输入部门名称" />
        </a-form-item>
        <a-form-item label="备注" name="desc">
          <a-textarea v-model:value="form.desc" :rows="3" />
        </a-form-item>
        <a-form-item label="排序" name="order">
          <a-input-number v-model:value="form.order" :min="0" style="width: 100%" />
        </a-form-item>
      </template>
    </CrudTable>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { useUserStore } from '@/store'
import { PlusOutlined } from '@ant-design/icons-vue'
import { computed, onMounted, reactive, ref } from 'vue'

const userStore = useUserStore()
const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive<any>({
  name: '',
})

// 计算属性
const filterItemCount = computed(() => {
  return 1
})

const columns = computed(() => [
  { title: '部门名称', dataIndex: 'name', key: 'name' },
  { title: '备注', dataIndex: 'desc', key: 'desc', ellipsis: true },
  { title: '操作', key: 'action', width: 150, fixed: 'right' },
])

// 表格数据
const loading = ref(false)
const tableData = ref<any[]>([])
const deptOptions = ref<any[]>([])

// 弹窗数据
const modalTitle = computed(() => crudTableRef.value?.modalAction === 'add' ? '新增部门' : '编辑部门')
const modalLoading = ref(false)
const modalForm = reactive({
  parent_id: undefined,
  name: '',
  desc: '',
  order: 0,
})
const isDisabled = ref(false)

const modalRules = computed(() => ({
  name: [{ required: true, message: '请输入部门名称', trigger: ['input', 'blur', 'change'] }],
}))

// 方法
async function loadData() {
  loading.value = true
  try {
    const res: any = await api.getDepts()
    const data = res.data || []
    tableData.value = data
    deptOptions.value = data
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  loadData()
}

function handleReset() {
  queryParams.name = ''
  handleSearch()
}

function handleAdd() {
  // 检查是否选择了租户（超管需要选择租户，普通用户使用当前租户）
  // 注意：检查 currentTenant（右上角选择器的选择状态）而不是 currentTenantId（JWT中的租户ID）
  if (userStore.isSuperUser && !userStore.currentTenant) {
    window.$message?.warning('请先选择租户')
    return
  }

  isDisabled.value = false
  crudTableRef.value?.openAddModal()
}

function handleEdit(record: any) {
  // 检查是否选择了租户（超管需要选择租户，普通用户使用当前租户）
  // 注意：检查 currentTenant（右上角选择器的选择状态）而不是 currentTenantId（JWT中的租户ID）
  if (userStore.isSuperUser && !userStore.currentTenant) {
    window.$message?.warning('请先选择租户')
    return
  }

  isDisabled.value = record.parent_id === 0
  Object.assign(modalForm, record)
  crudTableRef.value?.openEditModal(record)
}

async function handleSave(form: any, action: 'add' | 'edit') {
  try {
    modalLoading.value = true
    const apiFn = action === 'add' ? api.createDept : api.updateDept
    const res: any = await apiFn(form)
    if (res.code === 200) {
      window.$message?.success(action === 'add' ? '新增成功' : '编辑成功')
      crudTableRef.value?.closeModal()
      loadData()
    }
  } catch (error: any) {
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
    }
  } catch (error) {
    console.error('删除失败', error)
  }
}

onMounted(() => {
  loadData()
})
</script>
