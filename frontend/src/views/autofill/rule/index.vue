<template>
  <div class="rule-page">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
      :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
      modal-width="600px" @search="handleSearch" @reset="handleReset" @table-change="handleTableChange"
      @modal-ok="handleSave">
      <template #filter-items>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="应用名称" class="filter-item">
            <a-select v-model:value="queryParams.app_name" placeholder="请选择应用" allow-clear :options="appOptions"
              @change="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="关键词" class="filter-item">
            <a-input v-model:value="queryParams.keyword" placeholder="请输入规则编码或名称" allow-clear
              @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="状态" class="filter-item">
            <a-select v-model:value="queryParams.status" placeholder="请选择状态" allow-clear :options="[
              { label: '启用', value: 1 },
              { label: '禁用', value: 0 },
            ]" />
          </a-form-item>
        </a-col>
      </template>

      <template #actions>
        <a-button v-permission="'post/api/v1/autofill/rule/create'" type="primary" @click="handleAdd">
          <PlusOutlined />
          新建规则
        </a-button>
      </template>

      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="record.status === 1 ? 'green' : 'red'">
            {{ record.status === 1 ? '启用' : '禁用' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'latest_version_no'">
          <a-tag v-if="record.latest_version_no > 0" color="blue">v{{ record.latest_version_no }}</a-tag>
          <span v-else>-</span>
        </template>
        <template v-if="column.key === 'updated_at'">
          <span v-if="record.updated_at">{{ formatDateTime(record.updated_at) }}</span>
          <span v-else>-</span>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button type="link" size="small" @click="handleEditContent(record)">
              <EditOutlined />
              编辑内容
            </a-button>
            <a-button v-permission="'post/api/v1/autofill/rule/update'" type="link" size="small"
              @click="handleEdit(record)">
              编辑
            </a-button>
            <a-popconfirm title="确定删除该规则吗？" @confirm="handleDelete(record)">
              <a-button v-permission="'delete/api/v1/autofill/rule/delete'" type="link" danger size="small">
                删除
              </a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>

      <template #modal-form="{ form }">
        <!-- 创建时：app_name 必填；编辑时：app_name 禁用 -->
        <a-form-item label="应用名称" name="app_name" :required="modalAction === 'add'">
          <a-select v-model:value="form.app_name" placeholder="请选择应用" allow-clear :options="appOptions"
            :disabled="modalAction === 'edit'" />
        </a-form-item>
        <a-form-item label="规则编码" name="rule_code">
          <a-input v-model:value="form.rule_code" placeholder="留空自动生成" :disabled="modalAction === 'edit'" />
        </a-form-item>
        <a-form-item label="规则名称" name="rule_name">
          <a-input v-model:value="form.rule_name" placeholder="请输入规则名称" />
        </a-form-item>
        <a-form-item label="规则描述" name="desc">
          <a-textarea v-model:value="form.desc" placeholder="请输入规则描述" :rows="3" />
        </a-form-item>
        <a-form-item v-if="modalAction === 'edit'" label="状态" name="status">
          <a-radio-group v-model:value="form.status">
            <a-radio :value="1">启用</a-radio>
            <a-radio :value="0">禁用</a-radio>
          </a-radio-group>
        </a-form-item>
      </template>
    </CrudTable>

    <!-- 规则内容编辑弹窗 -->
    <RuleContentModal v-model:open="contentModalVisible" :rule-id="currentRule?.id" :rule-code="currentRule?.rule_code"
      :rule-name="currentRule?.rule_name" @saved="handleContentSaved" />
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { useUserStore } from '@/store'
import { formatDateTime } from '@/utils'
import { EditOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, onMounted, reactive, ref } from 'vue'
import RuleContentModal from './components/RuleContentModal.vue'

defineOptions({ name: 'RulePage' })

const userStore = useUserStore()
const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  keyword: '',
  status: undefined as number | undefined,
  app_name: undefined as string | undefined,
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
const modalAction = ref<'add' | 'edit'>('add')
const modalForm = reactive({
  id: undefined as number | undefined,
  rule_code: '',
  rule_name: '',
  desc: '',
  status: 1,
  app_name: undefined as string | undefined,
})

// 内容编辑弹窗
const contentModalVisible = ref(false)
const currentRule = ref<any>(null)

// 其他数据
const appOptions = ref<any[]>([])

// 计算属性
const columns = computed(() => [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '规则编码', dataIndex: 'rule_code', key: 'rule_code', width: 200 },
  { title: '规则名称', dataIndex: 'rule_name', key: 'rule_name' },
  { title: '描述', dataIndex: 'desc', key: 'desc', ellipsis: true },
  { title: '最新版本', key: 'latest_version_no', width: 100, align: 'center' },
  { title: '状态', key: 'status', width: 100, align: 'center' },
  { title: '更新时间', key: 'updated_at', width: 180 },
  { title: '操作', key: 'action', width: 250, fixed: 'right' },
])

const filterItemCount = computed(() => 3)

const modalRules = computed(() => {
  const rules: Record<string, any[]> = {
    rule_name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  }
  // 创建时：应用名称必填
  if (modalAction.value === 'add') {
    rules.app_name = [{ required: true, message: '请选择应用名称', trigger: 'change' }]
  }
  return rules
})

// 加载数据
const fetchData = async () => {
  loading.value = true
  try {
    const res: any = await api.getRuleList({
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
      appOptions.value = (res.data || []).map((app: any) => ({
        label: app.label,
        value: app.value,
      }))
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
  queryParams.keyword = ''
  queryParams.status = undefined
  queryParams.app_name = undefined
  pagination.current = 1
  fetchData()
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchData()
}

const handleAdd = () => {
  modalAction.value = 'add'
  modalTitle.value = '新建规则'
  Object.assign(modalForm, {
    id: undefined,
    rule_code: '',
    rule_name: '',
    desc: '',
    status: 1,
    app_name: queryParams.app_name,
  })
  crudTableRef.value?.openAddModal()
}

const handleEdit = (record: any) => {
  modalAction.value = 'edit'
  modalTitle.value = '编辑规则'
  // 先重置表单到初始状态，避免旧数据干扰
  Object.assign(modalForm, {
    id: undefined,
    rule_code: '',
    rule_name: '',
    desc: '',
    status: 1,
    app_name: undefined as string | undefined,
  })
  // 再合并编辑的记录数据
  Object.assign(modalForm, { ...record })
  crudTableRef.value?.openEditModal(record)
}

const handleEditContent = (record: any) => {
  currentRule.value = record
  contentModalVisible.value = true
}

const handleContentSaved = () => {
  fetchData()
}

const handleSave = async (form: Record<string, any>, action: 'add' | 'edit') => {
  modalLoading.value = true
  try {
    // 构建请求数据
    const requestData: any = { ...form }

    let res: any
    if (action === 'add') {
      res = await api.createRule(requestData)
    } else {
      res = await api.updateRule(requestData)
    }

    if (res.code === 200) {
      message.success(action === 'add' ? '创建成功' : '更新成功')
      crudTableRef.value?.closeModal()
      fetchData()
    } else {
      message.error(res.msg || '操作失败')
    }
  } catch (error: any) {
    message.error(error?.response?.data?.msg || error?.message || '操作失败')
  } finally {
    modalLoading.value = false
  }
}

const handleDelete = async (record: any) => {
  try {
    const res: any = await api.deleteRule({ id: record.id })
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
  fetchData()
  fetchAppOptions()
})
</script>

<style scoped lang="less">
.rule-page {
  padding: 16px;
}
</style>
