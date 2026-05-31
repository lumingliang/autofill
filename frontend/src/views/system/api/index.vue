<template>
  <div class="api-page">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
      @search="handleSearch" @reset="handleReset" @table-change="handleTableChange">
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="API编码" class="filter-item">
            <a-input v-model:value="queryParams.api_code" placeholder="请输入API编码" allow-clear @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
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
        <a-button type="primary" @click="handleRefreshApi">
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
        <template v-if="column.key === 'api_code'">
          <a-tooltip :title="record.api_code">
            {{ record.api_code }}
          </a-tooltip>
        </template>
      </template>
    </CrudTable>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { SyncOutlined } from '@ant-design/icons-vue'
import { computed, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'ApiPage' })

const crudTableRef = ref<InstanceType<typeof CrudTable>>()

const queryParams = reactive({
  api_code: '',
  path: '',
  summary: '',
  tags: '',
})

const loading = ref(false)
const tableData = ref<any[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
})

const columns = computed(() => [
  { title: 'API编码', dataIndex: 'api_code', key: 'api_code', width: 200, ellipsis: true },
  { title: 'API路径', dataIndex: 'path', key: 'path', width: 250, ellipsis: true },
  { title: '请求方式', dataIndex: 'method', key: 'method', width: 100 },
  { title: 'API简介', dataIndex: 'summary', key: 'summary', width: 200, ellipsis: true },
  { title: 'Tags', dataIndex: 'tags', key: 'tags', width: 150, ellipsis: true },
])

const filterItemCount = computed(() => 4)

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
  queryParams.api_code = ''
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
