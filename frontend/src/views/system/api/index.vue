<template>
  <div class="api-page crud-page">
    <a-card>
      <a-form :model="queryParams" class="crud-filter-form smart-filter-form">
        <a-row :gutter="16" class="filter-row">
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
          <a-col v-bind="getActionColProps" class="filter-actions-col"
            :class="filterItemCount <= 3 ? 'single-line' : 'multi-line'">
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
        <a-button v-permission="'post/api/v1/api/create'" type="primary" @click="handleAdd">
          <PlusOutlined />
          新建API
        </a-button>
        <a-button v-permission="'post/api/v1/api/refresh'" class="ml-2" @click="handleRefreshApi">
          <SyncOutlined />
          刷新API
        </a-button>
      </div>

      <a-table class="crud-table" :columns="columns" :data-source="tableData" :loading="loading"
        :pagination="pagination" row-key="id" :scroll="{ x: 'max-content' }" @change="handleTableChange">
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
      </a-table>
    </a-card>

    <!-- 新增/编辑 弹窗 -->
    <a-modal v-model:open="modalVisible" :title="modalTitle" :confirm-loading="modalLoading" @ok="handleSave"
      @cancel="modalVisible = false">
      <a-form ref="modalFormRef" :model="modalForm" :rules="modalRules" :label-col="{ span: 6 }"
        :wrapper-col="{ span: 16 }">
        <a-form-item label="API路径" name="path">
          <a-input v-model:value="modalForm.path" placeholder="请输入API路径" />
        </a-form-item>
        <a-form-item label="请求方式" name="method">
          <a-input v-model:value="modalForm.method" placeholder="请输入请求方式" />
        </a-form-item>
        <a-form-item label="API简介" name="summary">
          <a-input v-model:value="modalForm.summary" placeholder="请输入API简介" />
        </a-form-item>
        <a-form-item label="Tags" name="tags">
          <a-input v-model:value="modalForm.tags" placeholder="请输入Tags" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { PlusOutlined, SyncOutlined } from '@ant-design/icons-vue'
import api from '@/api'

const queryParams = reactive<any>({
  path: '',
  summary: '',
  tags: '',
})

// 计算表单项数量（用于控制按钮布局）
const filterItemCount = 3 // API页面固定3个表单项

// 操作按钮列的栅格配置
// 单行时宽度自适应，多行时占据标准宽度
const getActionColProps = computed(() => {
  const isSingleLine = filterItemCount <= 3
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
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

const columns = [
  { title: 'API路径', dataIndex: 'path', key: 'path', width: 250, ellipsis: true, resizable: true },
  { title: '请求方式', dataIndex: 'method', key: 'method', width: 100, resizable: true },
  { title: 'API简介', dataIndex: 'summary', key: 'summary', width: 200, ellipsis: true, resizable: true },
  { title: 'Tags', dataIndex: 'tags', key: 'tags', width: 150, ellipsis: true, resizable: true },
  { title: '操作', key: 'action', width: 150, fixed: 'right' },
]

const modalVisible = ref(false)
const modalLoading = ref(false)
const modalAction = ref<'add' | 'edit'>('add')
const modalTitle = computed(() => (modalAction.value === 'add' ? '新增API' : '编辑API'))
const modalFormRef = ref()
const modalForm = reactive<any>({
  path: '',
  method: '',
  summary: '',
  tags: '',
})

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
  modalAction.value = 'add'
  Object.assign(modalForm, {
    path: '',
    method: '',
    summary: '',
    tags: '',
  })
  modalVisible.value = true
}

function handleEdit(record: any) {
  modalAction.value = 'edit'
  Object.assign(modalForm, { ...record })
  modalVisible.value = true
}

async function handleSave() {
  try {
    await modalFormRef.value.validate()
    modalLoading.value = true
    const apiFn = modalAction.value === 'add' ? api.createApi : api.updateApi
    const res: any = await apiFn({ ...modalForm })
    if (res.code === 200) {
      window.$message?.success(modalAction.value === 'add' ? '新增成功' : '编辑成功')
      modalVisible.value = false
      loadData()
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

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="less">
.api-page {
  .table-actions {
    margin-bottom: 16px;
  }

  .ml-2 {
    margin-left: 8px;
  }
}
</style>
