<template>
  <div class="batch-test-list">
    <CrudTable
      ref="crudTableRef"
      :columns="columns"
      :data-source="tableData"
      :loading="loading"
      :pagination="pagination"
      :filter-model="queryParams"
      :filter-item-count="1"
      row-key="id"
      @search="handleSearch"
      @reset="handleReset"
      @table-change="handleTableChange"
    >
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="任务名称" class="filter-item">
            <a-input
              v-model:value="queryParams.keyword"
              placeholder="请输入任务名称"
              allow-clear
              @pressEnter="handleSearch"
            />
          </a-form-item>
        </a-col>
      </template>

      <!-- 操作按钮 -->
      <template #actions>
        <a-button type="primary" @click="showImportModal">
          <PlusOutlined />
          导入文件
        </a-button>
      </template>

      <!-- 表格列自定义 -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="getStatusColor(record.status)">
            {{ getStatusText(record.status) }}
          </a-tag>
        </template>

        <template v-if="column.key === 'progress'">
          <div class="progress-info">
            <span class="success">成功: {{ record.success_count }}</span>
            <span class="fail">失败: {{ record.fail_count }}</span>
            <span class="total">总计: {{ record.row_count }}</span>
          </div>
          <a-progress
            :percent="calculateProgress(record)"
            :stroke-color="getProgressColor(record)"
            size="small"
          />
        </template>

        <template v-if="column.key === 'created_at'">
          <span v-if="record.created_at">{{ record.created_at }}</span>
          <span v-else>-</span>
        </template>

        <template v-if="column.key === 'action'">
          <a-space>
            <a-button type="link" size="small" @click="showDetailModal(record)">
              查看
            </a-button>
            <a-button
              v-if="record.status === 2 || record.status === 3"
              type="link"
              size="small"
              @click="exportResults(record)"
            >
              导出
            </a-button>
            <a-button
              v-if="record.status === 1"
              type="link"
              size="small"
              danger
              @click="stopTask(record)"
            >
              停止
            </a-button>
            <a-button
              v-if="record.status !== 1"
              type="link"
              size="small"
              @click="retryTask(record)"
            >
              重试
            </a-button>
            <a-popconfirm
              title="确定删除该任务吗？"
              @confirm="deleteTask(record)"
            >
              <a-button type="link" size="small" danger>
                删除
              </a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </CrudTable>

    <!-- 导入文件弹窗 -->
    <a-modal
      v-model:open="importModalVisible"
      title="导入批量测试文件"
      :confirm-loading="importLoading"
      @ok="handleImport"
      @cancel="closeImportModal"
      width="600px"
    >
      <a-form :model="importForm" layout="vertical">
        <a-form-item label="选择文件" required>
          <a-upload-dragger
            v-model:file-list="fileList"
            :before-upload="beforeUpload"
            @remove="handleRemove"
            accept=".csv,.xlsx,.xls"
            :multiple="false"
          >
            <p class="ant-upload-drag-icon">
              <UploadOutlined />
            </p>
            <p class="ant-upload-text">点击或拖拽文件到此处上传</p>
            <p class="ant-upload-hint">
              支持格式：.csv, .xlsx, .xls，必须包含 'query' 列，最大文件大小：50MB
            </p>
          </a-upload-dragger>
        </a-form-item>

        <a-form-item label="Dify Agent" required>
          <a-select
            v-model:value="importForm.dify_agent_id"
            placeholder="请选择 Dify Agent"
            :loading="agentLoading"
            show-search
            :filter-option="filterAgentOption"
          >
            <a-select-option
              v-for="agent in agentList"
              :key="agent.value"
              :value="agent.value"
            >
              {{ agent.label }}
            </a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="任务名称">
          <a-input
            v-model:value="importForm.task_name"
            placeholder="可选，默认使用文件名"
          />
        </a-form-item>

        <a-form-item label="备注">
          <a-textarea
            v-model:value="importForm.remark"
            placeholder="可选"
            :rows="3"
          />
        </a-form-item>
      </a-form>

      <!-- 文件预览 -->
      <div v-if="filePreview" class="file-preview">
        <a-divider>文件预览</a-divider>
        <div class="preview-info">
          <p>文件名：{{ filePreview.file_name }}</p>
          <p>数据行数：{{ filePreview.row_count }}</p>
          <p>
            是否包含 query 列：
            <a-tag :color="filePreview.has_query_column ? 'success' : 'error'">
              {{ filePreview.has_query_column ? '是' : '否' }}
            </a-tag>
          </p>
        </div>
        <a-table
          v-if="filePreview.sample_data && filePreview.sample_data.length > 0"
          :columns="previewColumns"
          :data-source="filePreview.sample_data"
          size="small"
          :pagination="false"
        />
      </div>
    </a-modal>

    <!-- 任务详情弹窗 -->
    <a-modal
      v-model:open="detailModalVisible"
      title="任务详情"
      :footer="null"
      width="1000px"
    >
      <div v-if="currentTask" class="task-detail">
        <!-- 任务基本信息 -->
        <a-descriptions :column="3" bordered>
          <a-descriptions-item label="任务名称">{{ currentTask.task_name }}</a-descriptions-item>
          <a-descriptions-item label="版本号">v{{ currentTask.version_no }}</a-descriptions-item>
          <a-descriptions-item label="状态">
            <a-tag :color="getStatusColor(currentTask.status)">
              {{ getStatusText(currentTask.status) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="Dify Agent">{{ currentTask.dify_agent_name }}</a-descriptions-item>
          <a-descriptions-item label="文件名">{{ currentTask.file_name }}</a-descriptions-item>
          <a-descriptions-item label="数据行数">{{ currentTask.row_count }}</a-descriptions-item>
          <a-descriptions-item label="成功数">
            <span class="success-text">{{ currentTask.success_count }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="失败数">
            <span class="fail-text">{{ currentTask.fail_count }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="待执行">
            {{ currentTask.row_count - currentTask.success_count - currentTask.fail_count }}
          </a-descriptions-item>
          <a-descriptions-item label="创建时间" :span="3">{{ currentTask.created_at }}</a-descriptions-item>
          <a-descriptions-item label="备注" :span="3">{{ currentTask.remark || '-' }}</a-descriptions-item>
        </a-descriptions>

        <!-- 进度条 -->
        <div class="detail-progress">
          <div class="progress-label">
            执行进度: {{ currentTask.success_count + currentTask.fail_count }} / {{ currentTask.row_count }}
          </div>
          <a-progress
            :percent="calculateProgress(currentTask)"
            :stroke-color="getProgressColor(currentTask)"
            :status="currentTask.status === 1 ? 'active' : 'normal'"
          />
        </div>

        <!-- 统计卡片 -->
        <a-row :gutter="16" class="stats-row">
          <a-col :span="6">
            <a-card>
              <a-statistic title="总数据" :value="currentTask.row_count || 0" />
            </a-card>
          </a-col>
          <a-col :span="6">
            <a-card>
              <a-statistic
                title="成功"
                :value="currentTask.success_count || 0"
                value-style="color: #52c41a"
              />
            </a-card>
          </a-col>
          <a-col :span="6">
            <a-card>
              <a-statistic
                title="失败"
                :value="currentTask.fail_count || 0"
                value-style="color: #ff4d4f"
              />
            </a-card>
          </a-col>
          <a-col :span="6">
            <a-card>
              <a-statistic
                title="待执行"
                :value="(currentTask.row_count || 0) - (currentTask.success_count || 0) - (currentTask.fail_count || 0)"
                value-style="color: #1890ff"
              />
            </a-card>
          </a-col>
        </a-row>

        <!-- 测试结果列表 -->
        <a-card title="测试结果" class="results-card" size="small">
          <template #extra>
            <a-radio-group v-model:value="resultStatusFilter" @change="handleResultFilterChange" size="small">
              <a-radio-button :value="undefined">全部</a-radio-button>
              <a-radio-button :value="0">待执行</a-radio-button>
              <a-radio-button :value="1">执行中</a-radio-button>
              <a-radio-button :value="2">成功</a-radio-button>
              <a-radio-button :value="3">失败</a-radio-button>
            </a-radio-group>
          </template>

          <a-table
            :columns="resultColumns"
            :data-source="resultList"
            :loading="resultLoading"
            :pagination="resultPagination"
            @change="handleResultTableChange"
            row-key="id"
            size="small"
            :scroll="{ x: 800 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'status'">
                <a-tag :color="getStatusColor(record.status)">
                  {{ getStatusText(record.status) }}
                </a-tag>
              </template>

              <template v-if="column.key === 'query'">
                <div class="query-cell" :title="record.query">
                  {{ record.query }}
                </div>
              </template>

              <template v-if="column.key === 'answer'">
                <div class="answer-cell" :title="record.answer">
                  {{ record.answer || '-' }}
                </div>
              </template>

              <template v-if="column.key === 'execution_time'">
                <span v-if="record.execution_time_ms">
                  {{ record.execution_time_ms }}ms
                </span>
                <span v-else>-</span>
              </template>

              <template v-if="column.key === 'action'">
                <a-button type="link" size="small" @click="viewResultDetail(record)">
                  详情
                </a-button>
              </template>
            </template>
          </a-table>
        </a-card>
      </div>
    </a-modal>

    <!-- 结果详情弹窗 -->
    <a-modal
      v-model:open="resultDetailModalVisible"
      title="结果详情"
      width="800px"
      :footer="null"
    >
      <a-descriptions v-if="selectedResult" :column="1" bordered>
        <a-descriptions-item label="Query">
          {{ selectedResult.query }}
        </a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-tag :color="getStatusColor(selectedResult.status)">
            {{ getStatusText(selectedResult.status) }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="执行耗时">
          {{ selectedResult.execution_time_ms ? selectedResult.execution_time_ms + 'ms' : '-' }}
        </a-descriptions-item>
        <a-descriptions-item label="开始时间">
          {{ selectedResult.started_at || '-' }}
        </a-descriptions-item>
        <a-descriptions-item label="完成时间">
          {{ selectedResult.completed_at || '-' }}
        </a-descriptions-item>
        <a-descriptions-item v-if="selectedResult.error_msg" label="错误信息">
          <span class="error-text">{{ selectedResult.error_msg }}</span>
        </a-descriptions-item>
        <a-descriptions-item v-if="selectedResult.answer" label="Answer">
          <pre class="answer-pre">{{ selectedResult.answer }}</pre>
        </a-descriptions-item>
      </a-descriptions>

      <!-- 动态显示 Dify 返回的其他字段 -->
      <div v-if="selectedResult && getExtraFields().length > 0" class="extra-fields">
        <a-divider>其他字段</a-divider>
        <a-descriptions :column="1" bordered>
          <a-descriptions-item
            v-for="field in getExtraFields()"
            :key="field.key"
            :label="field.key"
          >
            <pre v-if="isJson(field.value)" class="json-pre">{{ formatJson(field.value) }}</pre>
            <span v-else>{{ field.value }}</span>
          </a-descriptions-item>
        </a-descriptions>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined, UploadOutlined } from '@ant-design/icons-vue'
import CrudTable from '@/components/CrudTable/index.vue'
import {
  getBatchTestTaskList,
  getBatchTestTaskDetail,
  getBatchTestResults,
  deleteBatchTestTask,
  stopBatchTestTask,
  retryBatchTestTask,
  importBatchTestFile,
  previewBatchTestFile,
  getDifyAgentSelect,
  exportBatchTestResults,
  type BatchTestTask
} from '@/api/autofill/batch_test'

const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  keyword: ''
})

// 列表数据
const loading = ref(false)
const tableData = ref<BatchTestTask[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

// 表格列定义
const columns = [
  {
    title: '任务名称',
    dataIndex: 'task_name',
    key: 'task_name',
    ellipsis: true
  },
  {
    title: 'Dify Agent',
    dataIndex: 'dify_agent_name',
    key: 'dify_agent_name',
    width: 150
  },
  {
    title: '文件名',
    dataIndex: 'file_name',
    key: 'file_name',
    ellipsis: true
  },
  {
    title: '数据行数',
    dataIndex: 'row_count',
    key: 'row_count',
    width: 100
  },
  {
    title: '状态',
    key: 'status',
    width: 100
  },
  {
    title: '进度',
    key: 'progress',
    width: 200
  },
  {
    title: '创建时间',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 180
  },
  {
    title: '操作',
    key: 'action',
    width: 200,
    fixed: 'right'
  }
]

// 导入弹窗
const importModalVisible = ref(false)
const importLoading = ref(false)
const fileList = ref<any[]>([])
const currentFile = ref<File | null>(null)
const filePreview = ref<any>(null)
const agentLoading = ref(false)
const agentList = ref<{ label: string; value: number }[]>([])

const importForm = reactive({
  dify_agent_id: undefined as number | undefined,
  task_name: '',
  remark: ''
})

const previewColumns = ref<any[]>([])

// 详情弹窗
const detailModalVisible = ref(false)
const currentTask = ref<BatchTestTask | null>(null)

// 结果列表
const resultLoading = ref(false)
const resultList = ref<any[]>([])
const resultStatusFilter = ref<number | undefined>(undefined)
const resultPagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

// 结果列定义
const resultColumns = [
  {
    title: '行号',
    dataIndex: 'row_index',
    key: 'row_index',
    width: 80
  },
  {
    title: 'Query',
    dataIndex: 'query',
    key: 'query',
    ellipsis: true
  },
  {
    title: '状态',
    key: 'status',
    width: 100
  },
  {
    title: 'Answer',
    key: 'answer',
    ellipsis: true
  },
  {
    title: '执行耗时',
    key: 'execution_time',
    width: 100
  },
  {
    title: '开始时间',
    dataIndex: 'started_at',
    key: 'started_at',
    width: 180
  },
  {
    title: '完成时间',
    dataIndex: 'completed_at',
    key: 'completed_at',
    width: 180
  },
  {
    title: '操作',
    key: 'action',
    width: 80,
    fixed: 'right'
  }
]

// 结果详情弹窗
const resultDetailModalVisible = ref(false)
const selectedResult = ref<any>(null)

// 状态映射
const statusMap: Record<number, { text: string; color: string }> = {
  0: { text: '待执行', color: 'default' },
  1: { text: '执行中', color: 'processing' },
  2: { text: '已完成', color: 'success' },
  3: { text: '失败', color: 'error' },
  4: { text: '已停止', color: 'warning' }
}

function getStatusText(status: number): string {
  return statusMap[status]?.text || '未知'
}

function getStatusColor(status: number): string {
  return statusMap[status]?.color || 'default'
}

function calculateProgress(record: BatchTestTask): number {
  if (record.row_count === 0) return 0
  const completed = record.success_count + record.fail_count
  return Math.round((completed / record.row_count) * 100)
}

function getProgressColor(record: BatchTestTask): string {
  if (record.fail_count > 0) return '#ff4d4f'
  return '#52c41a'
}

// 加载任务列表
async function loadTaskList() {
  loading.value = true
  try {
    const res: any = await getBatchTestTaskList({
      page: pagination.current,
      page_size: pagination.pageSize,
      keyword: queryParams.keyword
    })
    if (res.code === 200) {
      tableData.value = res.data || []
      pagination.total = res.total || 0
    } else {
      message.error(res.msg || '获取任务列表失败')
    }
  } catch (error) {
    message.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

function handleTableChange(p: any) {
  pagination.current = p.current
  pagination.pageSize = p.pageSize
  loadTaskList()
}

function handleSearch() {
  pagination.current = 1
  loadTaskList()
}

function handleReset() {
  queryParams.keyword = ''
  pagination.current = 1
  loadTaskList()
}

// 显示详情弹窗
async function showDetailModal(record: BatchTestTask) {
  detailModalVisible.value = true
  // 获取完整任务详情
  try {
    const res: any = await getBatchTestTaskDetail(record.id)
    if (res.code === 200) {
      currentTask.value = res.data
      // 加载结果列表
      await loadResults()
    } else {
      message.error(res.msg || '获取任务详情失败')
      currentTask.value = record
    }
  } catch (error) {
    message.error('获取任务详情失败')
    currentTask.value = record
  }
}

// 加载结果列表
async function loadResults() {
  if (!currentTask.value) return
  resultLoading.value = true
  try {
    const res: any = await getBatchTestResults(currentTask.value.id, {
      page: resultPagination.current,
      page_size: resultPagination.pageSize,
      status: resultStatusFilter.value
    })
    if (res.code === 200) {
      resultList.value = res.data || []
      resultPagination.total = res.total || 0
    } else {
      message.error(res.msg || '获取结果列表失败')
    }
  } catch (error) {
    message.error('获取结果列表失败')
  } finally {
    resultLoading.value = false
  }
}

function handleResultTableChange(p: any) {
  resultPagination.current = p.current
  resultPagination.pageSize = p.pageSize
  loadResults()
}

function handleResultFilterChange() {
  resultPagination.current = 1
  loadResults()
}

// 查看结果详情
function viewResultDetail(record: any) {
  selectedResult.value = record
  resultDetailModalVisible.value = true
}

// 获取额外字段（排除已知字段）
function getExtraFields(): { key: string; value: any }[] {
  if (!selectedResult.value) return []

  const knownFields = [
    'id', 'row_index', 'query', 'status', 'execution_time_ms',
    'started_at', 'completed_at', 'error_msg', 'answer'
  ]

  return Object.entries(selectedResult.value)
    .filter(([key]) => !knownFields.includes(key) && !key.startsWith('col_'))
    .map(([key, value]) => ({ key, value }))
}

// 判断是否为 JSON
function isJson(value: any): boolean {
  if (typeof value !== 'string') return false
  try {
    JSON.parse(value)
    return true
  } catch {
    return false
  }
}

// 格式化 JSON
function formatJson(value: any): string {
  if (typeof value !== 'string') return JSON.stringify(value, null, 2)
  try {
    return JSON.stringify(JSON.parse(value), null, 2)
  } catch {
    return value
  }
}

// 停止任务
async function stopTask(record: BatchTestTask) {
  try {
    const res: any = await stopBatchTestTask(record.id)
    if (res.code === 200) {
      message.success('任务已停止')
      loadTaskList()
    } else {
      message.error(res.msg || '停止失败')
    }
  } catch (error) {
    message.error('停止失败')
  }
}

// 重试任务
async function retryTask(record: BatchTestTask) {
  try {
    const res: any = await retryBatchTestTask(record.id)
    if (res.code === 200) {
      message.success('任务已重新执行')
      loadTaskList()
    } else {
      message.error(res.msg || '重试失败')
    }
  } catch (error) {
    message.error('重试失败')
  }
}

// 删除任务
async function deleteTask(record: BatchTestTask) {
  try {
    const res: any = await deleteBatchTestTask(record.id)
    if (res.code === 200) {
      message.success('删除成功')
      loadTaskList()
    } else {
      message.error(res.msg || '删除失败')
    }
  } catch (error) {
    message.error('删除失败')
  }
}

// 导出结果
async function exportResults(record: BatchTestTask) {
  try {
    const res: any = await exportBatchTestResults(record.id)
    // 获取blob数据（响应拦截器返回的是整个response对象）
    const blob = res.data
    // 创建下载链接
    const blobUrl = new Blob([blob], { type: 'text/csv;charset=utf-8' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blobUrl)
    link.download = `${record.task_name}_v${record.version_no}_results.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(link.href)
    message.success('导出成功')
  } catch (error) {
    message.error('导出失败')
  }
}

// 导入弹窗
async function showImportModal() {
  importModalVisible.value = true
  fileList.value = []
  currentFile.value = null
  filePreview.value = null
  importForm.dify_agent_id = undefined
  importForm.task_name = ''
  importForm.remark = ''

  // 加载 Agent 列表
  agentLoading.value = true
  try {
    const res: any = await getDifyAgentSelect()
    if (res.code === 200) {
      agentList.value = res.data || []
    }
  } catch (error) {
    message.error('获取 Agent 列表失败')
  } finally {
    agentLoading.value = false
  }
}

function closeImportModal() {
  importModalVisible.value = false
}

// 文件上传前处理
async function beforeUpload(file: File): Promise<boolean> {
  // 检查文件类型
  const validTypes = ['.csv', '.xlsx', '.xls']
  const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase()
  if (!validTypes.includes(ext)) {
    message.error('只支持 .csv, .xlsx, .xls 格式的文件')
    return false
  }

  // 检查文件大小 (50MB)
  if (file.size > 50 * 1024 * 1024) {
    message.error('文件大小不能超过 50MB')
    return false
  }

  currentFile.value = file
  fileList.value = [file]

  // 预览文件
  try {
    const res: any = await previewBatchTestFile(file)
    if (res.code === 200) {
      filePreview.value = res.data

      // 生成预览表格列
      if (res.data.headers) {
        previewColumns.value = res.data.headers.map((h: string) => ({
          title: h,
          dataIndex: h,
          key: h,
          ellipsis: true
        }))
      }

      if (!res.data.has_query_column) {
        message.warning('文件必须包含 "query" 列')
      }
    } else {
      message.error(res.msg || '预览失败')
    }
  } catch (error) {
    message.error('预览失败')
  }

  return false // 阻止自动上传
}

function handleRemove() {
  fileList.value = []
  currentFile.value = null
  filePreview.value = null
}

// Agent下拉搜索过滤
function filterAgentOption(input: string, option: any) {
  return option.children.toLowerCase().includes(input.toLowerCase())
}

// 执行导入
async function handleImport() {
  if (!currentFile.value) {
    message.error('请选择文件')
    return
  }
  if (!importForm.dify_agent_id) {
    message.error('请选择 Dify Agent')
    return
  }
  if (filePreview.value && !filePreview.value.has_query_column) {
    message.error('文件必须包含 "query" 列')
    return
  }

  importLoading.value = true
  try {
    const res: any = await importBatchTestFile(
      currentFile.value,
      importForm.dify_agent_id,
      importForm.task_name,
      importForm.remark
    )
    if (res.code === 200) {
      message.success('导入成功，任务已开始执行')
      importModalVisible.value = false
      loadTaskList()
    } else {
      message.error(res.msg || '导入失败')
    }
  } catch (error) {
    message.error('导入失败')
  } finally {
    importLoading.value = false
  }
}

onMounted(() => {
  loadTaskList()
})
</script>

<style scoped lang="less">
.batch-test-list {
  padding: 24px;

  .progress-info {
    display: flex;
    gap: 12px;
    font-size: 12px;
    margin-bottom: 4px;

    .success {
      color: #52c41a;
    }

    .fail {
      color: #ff4d4f;
    }

    .total {
      color: #999;
    }
  }

  .file-preview {
    margin-top: 16px;

    .preview-info {
      margin-bottom: 16px;

      p {
        margin: 4px 0;
      }
    }
  }

  .task-detail {
    max-height: 70vh;
    overflow-y: auto;

    .success-text {
      color: #52c41a;
    }

    .fail-text {
      color: #ff4d4f;
    }

    .detail-progress {
      margin-top: 24px;

      .progress-label {
        margin-bottom: 8px;
        font-weight: 500;
      }
    }

    .stats-row {
      margin-top: 24px;
    }

    .results-card {
      margin-top: 24px;

      .query-cell,
      .answer-cell {
        max-width: 200px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .error-text {
      color: #ff4d4f;
    }

    .answer-pre {
      background: #f5f5f5;
      padding: 12px;
      border-radius: 4px;
      max-height: 300px;
      overflow: auto;
      white-space: pre-wrap;
      word-wrap: break-word;
    }

    .extra-fields {
      margin-top: 16px;

      .json-pre {
        background: #f5f5f5;
        padding: 12px;
        border-radius: 4px;
        max-height: 200px;
        overflow: auto;
        white-space: pre-wrap;
        word-wrap: break-word;
      }
    }
  }
}
</style>
