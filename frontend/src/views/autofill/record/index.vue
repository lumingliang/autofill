<template>
  <div class="record-page">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" :show-add-button="false"
      @search="handleSearch" @reset="handleReset" @table-change="handleTableChange">
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="会话ID" class="filter-item">
            <a-input v-model:value="queryParams.session_id" placeholder="请输入会话ID" allow-clear
              @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="手机号" class="filter-item">
            <a-input v-model:value="queryParams.phone" placeholder="请输入手机号" allow-clear @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="用户标识" class="filter-item">
            <a-input v-model:value="queryParams.user_unique_id" placeholder="请输入用户唯一标识" allow-clear
              @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="应用名称" class="filter-item">
            <a-select v-model:value="queryParams.app_name" placeholder="请选择应用" allow-clear :options="appOptions"
              @change="handleSearch" />
          </a-form-item>
        </a-col>
      </template>

      <!-- 表格列自定义 -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="getStatusColor(record.status)">
            {{ getStatusText(record.status) }}
          </a-tag>
        </template>
        <template v-if="column.key === 'created_at'">
          <span v-if="record.created_at">{{ formatDateTime(record.created_at) }}</span>
          <span v-else>-</span>
        </template>
        <template v-if="column.key === 'action'">
          <a-button type="link" size="small" @click="viewDetail(record)">查看详情</a-button>
        </template>
      </template>

    </CrudTable>

    <!-- 查看详情弹窗 -->
    <a-modal v-model:open="detailModalVisible" title="填单详情" width="1000px" :footer="null">
      <div v-if="currentRecord">
        <!-- 基本信息 -->
        <a-descriptions :column="2" bordered size="small">
          <a-descriptions-item label="会话ID">{{ currentRecord.session_id }}</a-descriptions-item>
          <a-descriptions-item label="应用名称">{{ currentRecord.app_name }}</a-descriptions-item>
          <a-descriptions-item label="处理状态">
            <a-tag :color="getStatusColor(currentRecord.status)">
              {{ getStatusText(currentRecord.status) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="创建时间">{{ formatDateTime(currentRecord.created_at) }}</a-descriptions-item>
          <a-descriptions-item label="处理时间" v-if="currentRecord.processed_at">
            {{ formatDateTime(currentRecord.processed_at) }}
          </a-descriptions-item>
          <a-descriptions-item label="错误信息" v-if="currentRecord.error_msg">
            <span style="color: red">{{ currentRecord.error_msg }}</span>
          </a-descriptions-item>
        </a-descriptions>

        <a-divider />

        <!-- 分步详情 -->
        <div v-if="hasStepData">
          <h4>分步填单记录</h4>
          <a-tabs v-model:activeKey="activeDetailTab">
            <a-tab-pane v-for="(step, index) in mergedSteps" :key="String(index)" :tab="`步骤 ${Number(step.step || index) + 1}`">
              <!-- 步骤概览 -->
              <a-descriptions :column="2" bordered size="small">
                <a-descriptions-item label="步骤">{{ Number(step.step || index) + 1 }}</a-descriptions-item>
                <a-descriptions-item label="时间">{{ formatDateTime(step.timestamp) }}</a-descriptions-item>
                <a-descriptions-item label="用时" v-if="step.timing?.elapsed_time">
                  {{ step.timing.elapsed_time.toFixed(2) }}s
                </a-descriptions-item>
                <a-descriptions-item label="Token" v-if="step.timing?.total_tokens">
                  {{ step.timing.total_tokens }}
                </a-descriptions-item>
              </a-descriptions>

              <a-divider />

              <!-- Query内容（可复制） -->
              <div v-if="step.request?.query" style="margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                  <h4 style="margin: 0;">Query内容（用户对话）</h4>
                  <a-button type="primary" size="small" @click="copyToClipboard(step.request.query)">
                    复制
                  </a-button>
                </div>
                <a-textarea :value="step.request.query" :rows="6" readonly style="background-color: #f5f5f5;" />
              </div>

              <!-- 请求数据 -->
              <div v-if="step.request" style="margin-bottom: 16px;">
                <h4>请求参数</h4>
                <JsonViewer :data="step.request" title="请求参数" :max-height="300" />
              </div>

              <!-- 提取结果 -->
              <div v-if="step.fields && Object.keys(step.fields).length > 0">
                <h4>提取结果</h4>
                <a-table :dataSource="formatFieldsForTable(step.fields)" :columns="fieldResultColumns" size="small" bordered :pagination="false" />
              </div>
            </a-tab-pane>
          </a-tabs>
        </div>

        <!-- 无数据提示 -->
        <div v-else>
          <a-empty description="暂无填单数据" />
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { useUserStore } from '@/store'
import { formatDateTime } from '@/utils'
import { message } from 'ant-design-vue'
import { computed, onMounted, reactive, ref, watch } from 'vue'

defineOptions({ name: 'RecordPage' })

const userStore = useUserStore()
const isSuperUser = computed(() => userStore.isSuperUser)
const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  session_id: '',
  phone: '',
  user_unique_id: '',
  app_name: '',
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
const appOptions = ref<any[]>([])
const currentRecord = ref<any>(null)
const detailModalVisible = ref(false)
const activeDetailTab = ref('0')

// 状态映射
const statusMap: Record<string, { text: string; color: string }> = {
  pending: { text: '待处理', color: 'default' },
  queued: { text: '队列中', color: 'orange' },
  processing: { text: '处理中', color: 'blue' },
  completed: { text: '已完成', color: 'green' },
  failed: { text: '失败', color: 'red' },
  timeout: { text: '超时', color: 'red' },
}

const getStatusText = (status?: string) => {
  return statusMap[status || 'pending']?.text || status || '待处理'
}

const getStatusColor = (status?: string) => {
  return statusMap[status || 'pending']?.color || 'default'
}

// 判断是否有分步数据
const hasStepData = computed(() => {
  return mergedSteps.value.length > 0
})

// 合并 data 和 result 为统一的步骤数据
const mergedSteps = computed(() => {
  if (!currentRecord.value) return []

  const data = currentRecord.value.data || []
  const result = currentRecord.value.result || []

  // 如果 result 是数组（分步结果）
  if (Array.isArray(result) && result.length > 0) {
    return result.map((step: any, index: number) => {
      const dataItem = data[index] || {}
      return {
        step: step.step || index + 1,
        timestamp: step.timestamp || dataItem.timestamp,
        timing: step.timing || {},
        request: dataItem.request || {},
        fields: step.fields || {},
      }
    })
  }

  // 如果只有 data，按 data 展示
  if (data.length > 0) {
    return data.map((item: any, index: number) => ({
      step: item.step || index + 1,
      timestamp: item.timestamp,
      timing: {},
      request: item.request || {},
      fields: {},
    }))
  }

  return []
})

// 提取结果表格列定义
const fieldResultColumns = [
  { title: '字段名', dataIndex: 'fieldName', key: 'fieldName' },
  { title: '字段标签', dataIndex: 'fieldLabel', key: 'fieldLabel' },
  { title: '字段类型', dataIndex: 'fieldType', key: 'fieldType' },
  { title: '提取值', dataIndex: 'value', key: 'value' },
]

// 将字段格式化为表格数据
const formatFieldsForTable = (fields: any) => {
  if (!fields || typeof fields !== 'object') return []

  return Object.entries(fields).map(([key, value]: [string, any]) => {
    // 新格式: {"llm_res": "xxx"} 或 {"llm_res": "xxx", "error": "xxx"}
    if (value && typeof value === 'object' && 'llm_res' in value) {
      return {
        fieldName: key,
        fieldLabel: key,
        fieldType: 'llm_result',
        value: value.llm_res || '',
      }
    }

    // 旧格式: {type, label, value}
    const fieldType = value?.type || 'unknown'
    const fieldLabel = value?.label || key
    let displayValue = ''

    if (fieldType === 'select_single' && value?.value) {
      displayValue = value.value.label || value.value.value || ''
    } else if (fieldType === 'select_multi' && Array.isArray(value?.value)) {
      displayValue = value.value.map((v: any) => v.label || v.value).join(', ')
    } else {
      displayValue = value?.value || ''
    }

    return {
      fieldName: key,
      fieldLabel: fieldLabel,
      fieldType: fieldType,
      value: displayValue,
    }
  })
}

// 复制到剪贴板
const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text).then(() => {
    message.success('已复制到剪贴板')
  }).catch(() => {
    message.error('复制失败')
  })
}

// 计算属性
const columns = computed(() => [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '会话ID', dataIndex: 'session_id', key: 'session_id', ellipsis: true },
  { title: '手机号', dataIndex: 'phone', key: 'phone' },
  { title: '用户标识', dataIndex: 'user_unique_id', key: 'user_unique_id', ellipsis: true },
  { title: '用户名称', dataIndex: 'user_name', key: 'user_name' },
  { title: '应用名称', dataIndex: 'app_name', key: 'app_name' },
  { title: 'AI状态', key: 'status', width: 100 },
  { title: '创建时间', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 100, fixed: 'right' },
])

const filterItemCount = computed(() => 4)

// 加载数据
const fetchData = async () => {
  loading.value = true
  try {
    const res: any = await api.getRecordList({
      page: pagination.current,
      page_size: pagination.pageSize,
      ...queryParams,
    })
    if (res.code === 200) {
      tableData.value = res.data || []
      pagination.total = res.total || 0
    }
  } finally {
    loading.value = false
  }
}

const fetchAppOptions = async () => {
  try {
    const res: any = await api.getAppSelect()
    if (res.code === 200) {
      appOptions.value = res.data || []
    }
  } catch (error) {
    console.error('获取应用列表失败', error)
  }
}

const handleSearch = () => {
  pagination.current = 1
  fetchData()
}

const handleReset = () => {
  queryParams.session_id = ''
  queryParams.phone = ''
  queryParams.user_unique_id = ''
  queryParams.app_name = ''
  pagination.current = 1
  fetchData()
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchData()
}

const viewDetail = (record: any) => {
  currentRecord.value = record
  detailModalVisible.value = true
  activeDetailTab.value = '0'
}

onMounted(() => {
  fetchAppOptions()
  fetchData()
})
</script>

<style scoped lang="less">
.record-page {

  .json-viewer {
    background: #f6f8fa;
    padding: 16px;
    border-radius: 4px;
    overflow: auto;
    max-height: 500px;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.5;
  }
}
</style>
