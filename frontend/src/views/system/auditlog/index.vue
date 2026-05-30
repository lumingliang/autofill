<template>
  <div class="auditlog-page">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" :show-add-button="false"
      @search="handleSearch" @reset="handleReset" @table-change="handleTableChange">
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="用户名称" class="filter-item">
            <a-input v-model:value="queryParams.username" placeholder="请输入用户名称" allow-clear
              @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="功能模块" class="filter-item">
            <a-input v-model:value="queryParams.module" placeholder="请输入功能模块" allow-clear @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="接口概要" class="filter-item">
            <a-input v-model:value="queryParams.summary" placeholder="请输入接口概要" allow-clear @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="请求方法" class="filter-item">
            <a-select v-model:value="queryParams.method" placeholder="请选择请求方法" allow-clear :options="methodOptions" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="请求路径" class="filter-item">
            <a-input v-model:value="queryParams.path" placeholder="请输入请求路径" allow-clear @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="状态码" class="filter-item">
            <a-input v-model:value="queryParams.status" placeholder="请输入状态码" allow-clear @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="操作时间" class="filter-item">
            <a-range-picker v-model:value="dateRange" format="YYYY-MM-DD HH:mm:ss" :placeholder="['开始时间', '结束时间']"
              @change="handleDateRangeChange" style="width: 100%" />
          </a-form-item>
        </a-col>
      </template>

      <!-- 表格列自定义 -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'method'">
          <a-tag :color="getMethodColor(record.method)">
            {{ record.method }}
          </a-tag>
        </template>
        <template v-if="column.key === 'request_body'">
          <a-popover placement="right" trigger="hover" :overlay-style="{ width: '500px' }">
            <template #content>
              <JsonViewer :data="record.request_args" title="请求参数" :max-height="300" :show-toolbar="false" />
            </template>
            <a-button type="link" size="small">
              <EyeOutlined />
            </a-button>
          </a-popover>
        </template>
        <template v-if="column.key === 'response_body'">
          <a-popover placement="right" trigger="hover" :overlay-style="{ width: '500px' }">
            <template #content>
              <JsonViewer :data="record.response_body" title="响应内容" :max-height="300" :show-toolbar="false" />
            </template>
            <a-button type="link" size="small">
              <EyeOutlined />
            </a-button>
          </a-popover>
        </template>
        <template v-if="column.key === 'created_at'">
          {{ formatDateTime(record.created_at) }}
        </template>
      </template>
    </CrudTable>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { useUserStore } from '@/store'
import { formatDateTime } from '@/utils'
import { EyeOutlined } from '@ant-design/icons-vue'
import { computed, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'AuditLogPage' })

const userStore = useUserStore()
const isSuperUser = computed(() => userStore.isSuperUser)

const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  username: '',
  module: '',
  summary: '',
  method: undefined as string | undefined,
  path: '',
  status: '',
  start_time: '',
  end_time: '',
})

// 表格数据
const loading = ref(false)
const tableData = ref<any[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
})

// 其他数据
const dateRange = ref<any[]>([])
const tenantOptions = ref<any[]>([])

// 计算属性
const columns = computed(() => [
  { title: '用户名称', dataIndex: 'username', key: 'username', width: 120, ellipsis: true },
  { title: '接口概要', dataIndex: 'summary', key: 'summary', width: 200, ellipsis: true },
  { title: '功能模块', dataIndex: 'module', key: 'module', width: 120, ellipsis: true },
  { title: '请求方法', key: 'method', width: 100 },
  { title: '请求路径', dataIndex: 'path', key: 'path', width: 250, ellipsis: true },
  { title: '状态码', dataIndex: 'status', key: 'status', width: 80 },
  { title: '请求体', key: 'request_body', width: 80 },
  { title: '响应体', key: 'response_body', width: 80 },
  { title: '响应时间(s)', dataIndex: 'response_time', key: 'response_time', width: 120 },
  { title: '操作时间', key: 'created_at', width: 180 },
])

const filterItemCount = computed(() => {
  // 基础字段：用户名称、功能模块、接口概要、请求方法、请求路径、状态码、操作时间 = 7个
  return 7
})

const methodOptions = ref([
  { label: 'GET', value: 'GET' },
  { label: 'POST', value: 'POST' },
  { label: 'PUT', value: 'PUT' },
  { label: 'DELETE', value: 'DELETE' },
])

function getMethodColor(method: string) {
  const map: Record<string, string> = {
    GET: 'green',
    POST: 'blue',
    PUT: 'orange',
    DELETE: 'red',
  }
  return map[method?.toUpperCase()] || 'default'
}

function formatJSON(data: any) {
  try {
    return typeof data === 'string'
      ? JSON.stringify(JSON.parse(data), null, 2)
      : JSON.stringify(data, null, 2)
  } catch (e) {
    return data || '无数据'
  }
}

// 加载数据
async function loadData() {
  loading.value = true
  try {
    // 构建请求参数，过滤空值并转换类型
    const params: any = {
      page: pagination.current,
      page_size: pagination.pageSize,
    }

    // 只添加有值的参数
    if (queryParams.username) params.username = queryParams.username
    if (queryParams.module) params.module = queryParams.module
    if (queryParams.summary) params.summary = queryParams.summary
    if (queryParams.method) params.method = queryParams.method
    if (queryParams.path) params.path = queryParams.path
    if (queryParams.status) params.status = parseInt(queryParams.status)
    if (queryParams.start_time) params.start_time = queryParams.start_time
    if (queryParams.end_time) params.end_time = queryParams.end_time

    const res: any = await api.getAuditLogList(params)
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
  Object.assign(queryParams, {
    username: '',
    module: '',
    summary: '',
    method: undefined,
    path: '',
    status: '',
    start_time: '',
    end_time: '',
  })
  dateRange.value = []
  handleSearch()
}

function handleTableChange(p: any) {
  pagination.current = p.current
  pagination.pageSize = p.pageSize
  loadData()
}

function handleDateRangeChange(dates: any, dateStrings: string[]) {
  if (dateStrings && dateStrings.length === 2) {
    queryParams.start_time = dateStrings[0]
    queryParams.end_time = dateStrings[1]
  } else {
    queryParams.start_time = ''
    queryParams.end_time = ''
  }
}

async function loadTenants() {
  if (!isSuperUser.value) return
  const res: any = await api.getTenantSelect()
  tenantOptions.value = (res.data || []).map((item: any) => ({ label: item.name, value: item.id }))
}

onMounted(() => {
  loadData()
  loadTenants()
})
</script>
