<template>
  <a-layout class="record-page crud-page">
    <a-layout-content style="padding: 16px">
      <a-card>
        <a-form :model="queryParams" class="crud-filter-form smart-filter-form">
          <a-row :gutter="16" class="filter-row">
            <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
              <a-form-item label="会话ID" class="filter-item">
                <a-input v-model:value="queryParams.session_id" placeholder="请输入会话ID" allow-clear
                  @pressEnter="handleSearch" />
              </a-form-item>
            </a-col>
            <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
              <a-form-item label="手机号" class="filter-item">
                <a-input v-model:value="queryParams.phone" placeholder="请输入手机号" allow-clear
                  @pressEnter="handleSearch" />
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
                  @change="handleSearch" style="min-width: 160px; width: 100%" :dropdown-match-select-width="false" />
              </a-form-item>
            </a-col>
            <a-col v-if="userStore.isSuperUser" :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
              <a-form-item label="租户" class="filter-item">
                <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户" allow-clear :options="tenantOptions"
                  @change="handleSearch" />
              </a-form-item>
            </a-col>
            <a-col v-bind="getActionColProps" class="filter-actions-col"
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

        <a-table class="crud-table" :columns="columns" :data-source="tableData" :loading="loading"
          :pagination="pagination" row-key="id" :scroll="{ x: 'max-content' }" @change="handleTableChange">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <a-tag :color="getStatusColor(record.status)">
                {{ getStatusText(record.status) }}
              </a-tag>
            </template>
            <template v-if="column.key === 'data'">
              <a-button type="link" size="small" @click="viewData(record)">查看数据</a-button>
            </template>
            <template v-if="column.key === 'result'">
              <a-button v-if="record.result" type="link" size="small" @click="viewResult(record)">查看结果</a-button>
              <span v-else>-</span>
            </template>
            <template v-if="column.key === 'created_at'">
              <span v-if="record.created_at">{{ formatDateTime(record.created_at) }}</span>
              <span v-else>-</span>
            </template>
            <template v-if="column.key === 'action'">
              <a-space>
                <a-button v-permission="'post/api/v1/autofill/record/update'" type="link" size="small"
                  @click="handleEdit(record)">编辑</a-button>
                <a-popconfirm title="确定删除该记录吗？" @confirm="handleDelete(record)">
                  <a-button v-permission="'delete/api/v1/autofill/record/delete'" type="link" danger size="small">删除</a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>
        </a-table>
      </a-card>

      <!-- 查看数据弹窗 -->
      <a-modal v-model:open="viewModalVisible" title="填单数据" width="700px" :footer="null">
        <pre class="json-viewer">{{ JSON.stringify(currentRecord?.data, null, 2) }}</pre>
      </a-modal>

      <!-- 查看AI结果弹窗 -->
      <a-modal v-model:open="resultModalVisible" title="AI填单结果" width="700px" :footer="null">
        <div v-if="currentRecord?.result">
          <a-descriptions :column="1" bordered>
            <a-descriptions-item label="处理状态">
              <a-tag :color="getStatusColor(currentRecord.status)">
                {{ getStatusText(currentRecord.status) }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="处理时间" v-if="currentRecord.processed_at">
              {{ formatDateTime(currentRecord.processed_at) }}
            </a-descriptions-item>
            <a-descriptions-item label="错误信息" v-if="currentRecord.error_msg">
              <span style="color: red">{{ currentRecord.error_msg }}</span>
            </a-descriptions-item>
            <a-descriptions-item label="AI结果数据">
              <pre class="json-viewer">{{ JSON.stringify(currentRecord.result, null, 2) }}</pre>
            </a-descriptions-item>
          </a-descriptions>
        </div>
        <div v-else>
          <a-empty description="暂无AI结果数据" />
        </div>
      </a-modal>

      <!-- 编辑数据弹窗 -->
      <a-modal v-model:open="editModalVisible" title="编辑填单数据" :confirm-loading="editLoading" @ok="handleSave"
        @cancel="editModalVisible = false" width="700px">
        <a-form ref="editFormRef" :model="editForm" :label-col="{ span: 4 }" :wrapper-col="{ span: 19 }">
          <a-form-item label="会话ID">
            <span>{{ currentRecord?.session_id }}</span>
          </a-form-item>
          <a-form-item label="手机号" name="phone">
            <a-input v-model:value="editForm.phone" placeholder="请输入手机号" />
          </a-form-item>
          <a-form-item label="用户标识" name="user_unique_id">
            <a-input v-model:value="editForm.user_unique_id" placeholder="请输入用户唯一标识" />
          </a-form-item>
          <a-form-item label="用户名称" name="user_name">
            <a-input v-model:value="editForm.user_name" placeholder="请输入用户名称" />
          </a-form-item>
          <a-form-item label="填单数据" name="data">
            <a-textarea v-model:value="dataJsonStr" placeholder="请输入JSON格式的数据" :rows="10" />
          </a-form-item>
        </a-form>
      </a-modal>
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '@/store'
import api from '@/api'
import { formatDateTime } from '@/utils'
import { message } from 'ant-design-vue'

const userStore = useUserStore()

const queryParams = reactive<any>({
  session_id: '',
  phone: '',
  user_unique_id: '',
  app_name: '',
  tenant_id: undefined,
})

const tenantOptions = ref<any[]>([])
const appOptions = ref<any[]>([])

const filterItemCount = computed(() => {
  let count = 4
  if (userStore.isSuperUser) count++
  return count
})

const getActionColProps = computed(() => {
  const isSingleLine = filterItemCount.value <= 2
  if (isSingleLine) {
    return { xs: 24, sm: 12, md: 8, lg: 6, xl: 6 }
  }
  return { xs: 24, sm: 24, md: 24, lg: 24, xl: 24 }
})

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '会话ID', dataIndex: 'session_id', key: 'session_id', ellipsis: true },
  { title: '手机号', dataIndex: 'phone', key: 'phone' },
  { title: '用户标识', dataIndex: 'user_unique_id', key: 'user_unique_id', ellipsis: true },
  { title: '用户名称', dataIndex: 'user_name', key: 'user_name' },
  { title: '应用名称', dataIndex: 'app_name', key: 'app_name' },
  { title: 'AI状态', key: 'status', width: 100 },
  { title: '填单数据', key: 'data', width: 100 },
  { title: 'AI结果', key: 'result', width: 100 },
  { title: '创建时间', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 150, fixed: 'right' },
]

const tableData = ref<any[]>([])
const loading = ref(false)
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

const viewModalVisible = ref(false)
const resultModalVisible = ref(false)
const currentRecord = ref<any>(null)

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

const editModalVisible = ref(false)
const editLoading = ref(false)
const editFormRef = ref<any>(null)
const editForm = reactive<any>({
  id: undefined,
  phone: '',
  user_unique_id: '',
  user_name: '',
  data: {},
})
const dataJsonStr = ref('')

watch(dataJsonStr, (val) => {
  try {
    editForm.data = JSON.parse(val)
  } catch (e) {
    // 忽略解析错误
  }
})

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

const fetchTenantOptions = async () => {
  if (!userStore.isSuperUser) return
  try {
    const res: any = await api.getTenantSelect()
    if (res.code === 200) {
      tenantOptions.value = (res.data || []).map((t: any) => ({
        label: t.name,
        value: t.id,
      }))
    }
  } catch (error) {
    console.error('获取租户列表失败', error)
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
  queryParams.tenant_id = undefined
  pagination.current = 1
  fetchData()
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchData()
}

const viewData = (record: any) => {
  currentRecord.value = record
  viewModalVisible.value = true
}

const viewResult = (record: any) => {
  currentRecord.value = record
  resultModalVisible.value = true
}

const handleEdit = (record: any) => {
  currentRecord.value = record
  editForm.id = record.id
  editForm.phone = record.phone || ''
  editForm.user_unique_id = record.user_unique_id || ''
  editForm.user_name = record.user_name || ''
  editForm.data = record.data || {}
  dataJsonStr.value = JSON.stringify(record.data || {}, null, 2)
  editModalVisible.value = true
}

const handleSave = async () => {
  try {
    // 验证JSON格式
    try {
      JSON.parse(dataJsonStr.value)
    } catch (e) {
      message.error('填单数据格式不正确，请输入有效的JSON')
      return
    }

    editLoading.value = true
    const res: any = await api.updateRecord({ ...editForm })

    if (res.code === 200) {
      message.success('更新成功')
      editModalVisible.value = false
      fetchData()
    } else {
      message.error(res.msg || '操作失败')
    }
  } catch (error) {
    console.error('保存失败', error)
  } finally {
    editLoading.value = false
  }
}

const handleDelete = async (record: any) => {
  try {
    const res: any = await api.deleteRecord({ id: record.id })
    if (res.code === 200) {
      message.success('删除成功')
      fetchData()
    } else {
      message.error(res.msg || '删除失败')
    }
  } catch (error) {
    console.error('删除失败', error)
  }
}

onMounted(() => {
  fetchTenantOptions()
  fetchAppOptions()
  fetchData()
})
</script>

<style scoped>
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
</style>
