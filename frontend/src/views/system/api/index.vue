<template>
  <div class="api-page">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
      :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
      @search="handleSearch" @reset="handleReset" @table-change="handleTableChange" @modal-ok="handleSave">
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="路径" class="filter-item">
            <a-input v-model:value="queryParams.path" placeholder="请输入API路径" allow-clear @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="API简介" class="filter-item">
            <a-input v-model:value="queryParams.summary" placeholder="请输入API简介" allow-clear
              @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="Tags" class="filter-item">
            <a-input v-model:value="queryParams.tags" placeholder="请输入API模块" allow-clear @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
      </template>

      <!-- 操作按钮 -->
      <template #actions>
        <a-button v-permission="'post/api/v1/api/create'" type="primary" @click="handleAdd">
          <PlusOutlined />
          新建API
        </a-button>
        <a-button v-permission="'post/api/v1/api/refresh'" class="ml-2" @click="handleRefreshApi">
          <SyncOutlined />
          刷新API
        </a-button>
      </template>

      <!-- 表格列自定义 -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'method'">
          <a-tag :color="getMethodColor(record.method)">
            {{ record.method }}
          </a-tag>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button v-permission="'post/api/v1/api/update'" type="link" size="small"
              @click="handleEdit(record)">编辑</a-button>
            <a-popconfirm title="确定删除该API吗？" @confirm="handleDelete(record)">
              <a-button v-permission="'delete/api/v1/api/delete'" type="link" danger size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>

      <!-- 弹窗表单 -->
      <template #modal-form="{ form }">
        <a-form-item label="API路径" name="path">
          <a-input v-model:value="form.path" placeholder="请输入API路径" />
        </a-form-item>
        <a-form-item label="请求方式" name="method">
          <a-input v-model:value="form.method" placeholder="请输入请求方式" />
        </a-form-item>
        <a-form-item label="API简介" name="summary">
          <a-input v-model:value="form.summary" placeholder="请输入API简介" />
        </a-form-item>
        <a-form-item label="Tags" name="tags">
          <a-input v-model:value="form.tags" placeholder="请输入Tags" />
        </a-form-item>
      </template>
    </CrudTable>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { PlusOutlined, SyncOutlined } from '@ant-design/icons-vue'
import { computed, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'ApiPage' })

const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  path: '',
  summary: '',
  tags: '',
})

// 表格数据
const loading = ref(false)
const tableData = ref<any[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
})

// 弹窗数据
const modalTitle = ref('')
const modalLoading = ref(false)
const modalForm = reactive({
  id: undefined as number | undefined,
  path: '',
  method: '',
  summary: '',
  tags: '',
})

// 计算属性
const columns = computed(() => [
  { title: 'API路径', dataIndex: 'path', key: 'path', width: 250, ellipsis: true },
  { title: '请求方式', dataIndex: 'method', key: 'method', width: 100 },
  { title: 'API简介', dataIndex: 'summary', key: 'summary', width: 200, ellipsis: true },
  { title: 'Tags', dataIndex: 'tags', key: 'tags', width: 150, ellipsis: true },
  { title: '操作', key: 'action', width: 150, fixed: 'right' },
])

const filterItemCount = computed(() => 3)

const modalRules = {
  path: [{ required: true, message: '请输入API路径', trigger: ['input', 'blur', 'change'] }],
  method: [{ required: true, message: '请输入请求方式', trigger: ['input', 'blur', 'change'] }],
  summary: [{ required: true, message: '请输入API简介', trigger: ['input', 'blur', 'change'] }],
  tags: [{ required: true, message: '请输入Tags', trigger: ['input', 'blur', 'change'] }],
}

function getMethodColor(method: string) {
  const map: Record<string, string> = {
    GET: 'green',
    POST: 'blue',
    PUT: 'orange',
    DELETE: 'red',
  }
  return map[method?.toUpperCase()] || 'default'
}

// 加载数据
async function loadData() {
  loading.value = true
  try {
    const params = {
      ...queryParams,
      page: pagination.current,
      page_size: pagination.pageSize,
    }
    const res: any = await api.getApis(params)
    tableData.value = res.data || []
    pagination.total = res.total || 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.current = 1
  loadData()
}

function handleReset() {
  queryParams.path = ''
  queryParams.summary = ''
  queryParams.tags = ''
  handleSearch()
}

function handleTableChange(p: any) {
  pagination.current = p.current
  pagination.pageSize = p.pageSize
  loadData()
}

function handleAdd() {
  modalTitle.value = '新增API'
  Object.assign(modalForm, {
    id: undefined,
    path: '',
    method: '',
    summary: '',
    tags: '',
  })
  crudTableRef.value?.openAddModal()
}

function handleEdit(record: any) {
  modalTitle.value = '编辑API'
  Object.assign(modalForm, { ...record })
  crudTableRef.value?.openEditModal(record)
}

async function handleSave(form: Record<string, any>, action: 'add' | 'edit') {
  modalLoading.value = true
  try {
    const apiFn = action === 'add' ? api.createApi : api.updateApi
    const res: any = await apiFn({ ...form })
    if (res.code === 200) {
      window.$message?.success(action === 'add' ? '新增成功' : '编辑成功')
      crudTableRef.value?.closeModal()
      loadData()
    }
  } finally {
    modalLoading.value = false
  }
}

async function handleDelete(record: any) {
  try {
    const res: any = await api.deleteApi({ api_id: record.id })
    if (res.code === 200) {
      window.$message?.success('删除成功')
      loadData()
    }
  } catch (error) {
    console.error('删除失败', error)
  }
}

async function handleRefreshApi() {
  try {
    await api.refreshApi({})
    window.$message?.success('刷新完成')
    loadData()
  } catch (error) {
    console.error('刷新失败', error)
  }
}

onMounted(loadData)
</script>

<style scoped lang="less">
.api-page {

  .ml-2 {
    margin-left: 8px;
  }
}
</style>
