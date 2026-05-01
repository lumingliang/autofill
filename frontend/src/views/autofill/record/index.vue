<template>
  <div class="record-page">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" :show-add-button="false"
      show-modal :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" modal-width="700px"
      @search="handleSearch" @reset="handleReset" @table-change="handleTableChange" @modal-ok="handleSave">
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
        <a-col v-if="isSuperUser" :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="租户" class="filter-item">
            <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户" allow-clear :options="tenantOptions"
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
              <a-button v-permission="'delete/api/v1/autofill/record/delete'" type="link" danger
                size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>

      <!-- 弹窗表单 -->
      <template #modal-form="{ form }">
        <a-form-item label="会话ID">
          <span>{{ currentRecord?.session_id }}</span>
        </a-form-item>
        <a-form-item label="手机号" name="phone">
          <a-input v-model:value="form.phone" placeholder="请输入手机号" />
        </a-form-item>
        <a-form-item label="用户标识" name="user_unique_id">
          <a-input v-model:value="form.user_unique_id" placeholder="请输入用户唯一标识" />
        </a-form-item>
        <a-form-item label="用户名称" name="user_name">
          <a-input v-model:value="form.user_name" placeholder="请输入用户名称" />
        </a-form-item>
        <a-form-item label="填单数据" name="data">
          <a-textarea v-model:value="dataJsonStr" placeholder="请输入JSON格式的数据" :rows="10" />
        </a-form-item>
      </template>
    </CrudTable>

    <!-- 查看数据弹窗 -->
    <a-modal v-model:open="viewModalVisible" title="填单数据" width="800px" :footer="null">
      <JsonViewer :data="currentRecord?.data" title="填单数据" :max-height="500" />
    </a-modal>

    <!-- 查看AI结果弹窗 -->
    <a-modal v-model:open="resultModalVisible" title="AI填单结果" width="800px" :footer="null">
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
            <JsonViewer :data="currentRecord.result" title="AI结果" :max-height="400" />
          </a-descriptions-item>
        </a-descriptions>
      </div>
      <div v-else>
        <a-empty description="暂无AI结果数据" />
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
  tenant_id: undefined as number | undefined,
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
  phone: '',
  user_unique_id: '',
  user_name: '',
  data: {} as Record<string, any>,
})

// 其他数据
const tenantOptions = ref<any[]>([])
const appOptions = ref<any[]>([])
const currentRecord = ref<any>(null)
const viewModalVisible = ref(false)
const resultModalVisible = ref(false)
const dataJsonStr = ref('')

watch(dataJsonStr, (val) => {
  try {
    modalForm.data = JSON.parse(val)
  } catch (e) {
    // 忽略解析错误
  }
})

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

// 计算属性
const columns = computed(() => [
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
])

const filterItemCount = computed(() => {
  let count = 4
  if (isSuperUser.value) count++
  return count
})

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

const fetchTenantOptions = async () => {
  if (!isSuperUser.value) return
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
  modalTitle.value = '编辑填单数据'
  Object.assign(modalForm, {
    id: record.id,
    phone: record.phone || '',
    user_unique_id: record.user_unique_id || '',
    user_name: record.user_name || '',
    data: record.data || {},
  })
  dataJsonStr.value = JSON.stringify(record.data || {}, null, 2)
  crudTableRef.value?.openEditModal(record)
}

const handleSave = async (form: Record<string, any>) => {
  // 验证JSON格式
  try {
    JSON.parse(dataJsonStr.value)
  } catch (e) {
    message.error('填单数据格式不正确，请输入有效的JSON')
    return
  }

  modalLoading.value = true
  try {
    const res: any = await api.updateRecord({ ...form })
    if (res.code === 200) {
      message.success('更新成功')
      crudTableRef.value?.closeModal()
      fetchData()
    } else {
      message.error(res.msg || '操作失败')
    }
  } finally {
    modalLoading.value = false
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

<style scoped lang="less">
.record-page {
  padding: 16px;

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
