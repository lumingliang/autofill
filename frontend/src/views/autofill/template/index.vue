<template>
  <a-layout class="template-page crud-page">
    <a-layout-content style="padding: 16px">
      <a-card>
        <a-form :model="queryParams" class="crud-filter-form smart-filter-form">
          <a-row :gutter="16" class="filter-row">
            <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
              <a-form-item label="模板名称" class="filter-item">
                <a-input v-model:value="queryParams.name" placeholder="请输入模板名称" allow-clear
                  @pressEnter="handleSearch" />
              </a-form-item>
            </a-col>
            <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
              <a-form-item label="应用名称" class="filter-item">
                <a-select v-model:value="queryParams.app_name" placeholder="请选择应用" allow-clear :options="appOptions"
                  @change="handleSearch" style="min-width: 160px; width: 100%" :dropdown-match-select-width="false" />
              </a-form-item>
            </a-col>
            <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
              <a-form-item label="分类" class="filter-item">
                <a-input v-model:value="queryParams.class_name" placeholder="请输入分类名称" allow-clear
                  @pressEnter="handleSearch" />
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

        <div class="table-actions">
          <a-button v-permission="'post/api/v1/autofill/template/create'" type="primary" @click="handleAdd">
            <PlusOutlined />
            新建模板
          </a-button>
          <a-button style="margin-left: 8px" @click="showImportModal">
            <UploadOutlined />
            CSV导入
          </a-button>
          <a-button style="margin-left: 8px" @click="downloadTemplate">
            <DownloadOutlined />
            下载模板
          </a-button>
        </div>

        <a-table class="crud-table" :columns="columns" :data-source="tableData" :loading="loading"
          :pagination="pagination" row-key="id" :scroll="{ x: 'max-content' }" @change="handleTableChange">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'summary'">
              <a-tooltip :title="record.summary">
                <span class="ellipsis-text">{{ record.summary }}</span>
              </a-tooltip>
            </template>
            <template v-if="column.key === 'created_at'">
              <span v-if="record.created_at">{{ formatDateTime(record.created_at) }}</span>
              <span v-else>-</span>
            </template>
            <template v-if="column.key === 'action'">
              <a-space>
                <a-button v-permission="'post/api/v1/autofill/template/update'" type="link" size="small"
                  @click="handleEdit(record)">编辑</a-button>
                <a-popconfirm title="确定删除该模板吗？" @confirm="handleDelete(record)">
                  <a-button v-permission="'delete/api/v1/autofill/template/delete'" type="link" danger
                    size="small">删除</a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>
        </a-table>
      </a-card>

      <!-- 新增/编辑 弹窗 -->
      <a-modal v-model:open="modalVisible" :title="modalTitle" :confirm-loading="modalLoading" @ok="handleSave"
        @cancel="modalVisible = false" width="800px">
        <a-form ref="modalFormRef" :model="modalForm" :rules="modalRules" :label-col="{ span: 4 }"
          :wrapper-col="{ span: 19 }">
          <a-form-item label="模板名称" name="name">
            <a-input v-model:value="modalForm.name" placeholder="请输入模板名称" />
          </a-form-item>
          <a-form-item label="应用名称" name="app_name">
            <a-select v-model:value="modalForm.app_name" placeholder="请选择应用" :options="appOptions"
              style="min-width: 200px; width: 100%" :dropdown-match-select-width="false" />
          </a-form-item>
          <a-form-item v-if="userStore.isSuperUser" label="租户" name="tenant_id">
            <a-select v-model:value="modalForm.tenant_id" placeholder="请选择租户" :options="tenantOptions" />
          </a-form-item>
          <a-form-item label="分类" name="class_name">
            <a-input v-model:value="modalForm.class_name" placeholder="请输入分类名称" />
          </a-form-item>
          <a-form-item label="摘要" name="summary">
            <a-textarea v-model:value="modalForm.summary" placeholder="请输入模板摘要" :rows="2" />
          </a-form-item>
          <a-form-item label="模板内容" name="template_content">
            <a-textarea v-model:value="modalForm.template_content" placeholder="请输入模板内容" :rows="10" />
          </a-form-item>
        </a-form>
      </a-modal>

      <!-- CSV导入弹窗 -->
      <a-modal v-model:open="importModalVisible" title="CSV批量导入总结模板" width="600px" :confirm-loading="importLoading"
        @ok="handleImport" @cancel="importModalVisible = false">
        <a-form :model="importForm" :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
          <a-form-item label="应用名称" required>
            <a-select v-model:value="importForm.app_name" placeholder="请选择应用" :options="appOptions"
              style="width: 100%" />
          </a-form-item>
          <a-form-item v-if="userStore.isSuperUser" label="租户" required>
            <a-select v-model:value="importForm.tenant_id" placeholder="请选择租户" :options="tenantOptions"
              style="width: 100%" />
          </a-form-item>
          <a-form-item label="CSV文件" required>
            <a-upload v-model:file-list="fileList" :before-upload="beforeUpload" accept=".csv">
              <a-button>
                <UploadOutlined />
                选择文件
              </a-button>
            </a-upload>
            <div style="margin-top: 8px; color: #999; font-size: 12px">
              CSV格式：name,class_name,summary,template_content
            </div>
          </a-form-item>
        </a-form>
      </a-modal>
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { PlusOutlined, SearchOutlined, ReloadOutlined, UploadOutlined, DownloadOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '@/store'
import api from '@/api'
import { formatDateTime } from '@/utils'
import { message } from 'ant-design-vue'

const userStore = useUserStore()

const queryParams = reactive<any>({
  name: '',
  app_name: '',
  class_name: '',
  tenant_id: undefined,
})

const tenantOptions = ref<any[]>([])
const appOptions = ref<any[]>([])

const filterItemCount = computed(() => {
  let count = 3
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
  { title: '模板名称', dataIndex: 'name', key: 'name' },
  { title: '应用名称', dataIndex: 'app_name', key: 'app_name' },
  { title: '分类', dataIndex: 'class_name', key: 'class_name' },
  { title: '摘要', key: 'summary', ellipsis: true },
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

const modalVisible = ref(false)
const modalLoading = ref(false)
const modalAction = ref<'add' | 'edit'>('add')
const modalTitle = computed(() => modalAction.value === 'add' ? '新建模板' : '编辑模板')
const modalFormRef = ref<any>(null)
const modalForm = reactive<any>({
  id: undefined,
  name: '',
  app_name: '',
  tenant_id: undefined,
  class_name: '',
  summary: '',
  template_content: '',
})

const modalRules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  app_name: [{ required: true, message: '请选择应用', trigger: 'change' }],
  tenant_id: [{ required: true, message: '请选择租户', trigger: 'change', type: 'number' }],
  class_name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
}

// CSV导入相关
const importModalVisible = ref(false)
const importLoading = ref(false)
const importForm = reactive({
  app_name: '',
  tenant_id: undefined as number | undefined,
})
const fileList = ref<any[]>([])

const fetchData = async () => {
  loading.value = true
  try {
    const res: any = await api.getTemplateList({
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
  queryParams.name = ''
  queryParams.app_name = ''
  queryParams.class_name = ''
  queryParams.tenant_id = undefined
  pagination.current = 1
  fetchData()
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchData()
}

const resetModalForm = () => {
  modalForm.id = undefined
  modalForm.name = ''
  modalForm.app_name = ''
  modalForm.tenant_id = userStore.isSuperUser ? undefined : userStore.userInfo?.current_tenant_id
  modalForm.class_name = ''
  modalForm.summary = ''
  modalForm.template_content = ''
}

const handleAdd = () => {
  modalAction.value = 'add'
  resetModalForm()
  modalVisible.value = true
}

const handleEdit = (record: any) => {
  modalAction.value = 'edit'
  resetModalForm()
  Object.assign(modalForm, record)
  modalVisible.value = true
}

const handleSave = async () => {
  try {
    await modalFormRef.value?.validate()
    modalLoading.value = true

    const apiCall = modalAction.value === 'add' ? api.createTemplate : api.updateTemplate
    const res: any = await apiCall({ ...modalForm })

    if (res.code === 200) {
      message.success(modalAction.value === 'add' ? '创建成功' : '更新成功')
      modalVisible.value = false
      fetchData()
    } else {
      message.error(res.msg || '操作失败')
    }
  } catch (error) {
    console.error('保存失败', error)
  } finally {
    modalLoading.value = false
  }
}

const handleDelete = async (record: any) => {
  try {
    const res: any = await api.deleteTemplate({ id: record.id })
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

// CSV导入相关方法
const showImportModal = () => {
  importForm.app_name = queryParams.app_name
  importForm.tenant_id = queryParams.tenant_id
  fileList.value = []
  importModalVisible.value = true
}

const beforeUpload = (file: File) => {
  if (!file.name.endsWith('.csv')) {
    message.error('请上传CSV文件')
    return false
  }
  fileList.value = [file]
  return false // 阻止自动上传
}

const handleImport = async () => {
  if (!importForm.app_name) {
    message.error('请选择应用名称')
    return
  }
  if (fileList.value.length === 0) {
    message.error('请选择CSV文件')
    return
  }
  if (userStore.isSuperUser && !importForm.tenant_id) {
    message.error('请选择租户')
    return
  }

  importLoading.value = true
  try {
    const res: any = await api.importTemplateFromCsv(
      fileList.value[0].originFileObj || fileList.value[0],
      importForm.app_name,
      importForm.tenant_id
    )
    if (res.code === 200) {
      const data = res.data || {}
      message.success(`导入成功！新建${data.created}条，更新${data.updated}条`)
      importModalVisible.value = false
      fetchData()
    } else {
      message.error(res.msg || '导入失败')
    }
  } catch (error: any) {
    message.error(error.message || '导入失败')
  } finally {
    importLoading.value = false
  }
}

const downloadTemplate = () => {
  const template = `name,class_name,summary,template_content
预约充电故障,充电故障,车主反馈预约充电功能异常，需排查充电设置及系统问题,车主X先生反馈：手机设置预约充电...
动力电池故障,电池系统,车主反馈动力电池异常报警，需安排检测及维修,车主X先生反馈：车辆仪表显示动力电池故障...
车机系统卡顿,智能网联,车主反馈车机系统卡顿/黑屏/死机，需排查系统问题,车主X先生反馈：车机出现卡顿/黑屏...`

  const blob = new Blob([template], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = 'template_import_template.csv'
  link.click()
  URL.revokeObjectURL(link.href)
}

onMounted(() => {
  fetchTenantOptions()
  fetchAppOptions()
  fetchData()
})
</script>

<style scoped>
.ellipsis-text {
  display: inline-block;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
