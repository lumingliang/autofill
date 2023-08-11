<template>
  <div class="template-page">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
      :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
      modal-width="800px" @search="handleSearch" @reset="handleReset" @table-change="handleTableChange"
      @modal-ok="handleSave">
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col v-if="userStore.isSuperUser" :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="租户" class="filter-item">
            <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户" allow-clear :options="tenantOptions"
              @change="handleTenantChange" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="模板名称" class="filter-item">
            <a-input v-model:value="queryParams.name" placeholder="请输入模板名称" allow-clear @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="应用名称" class="filter-item">
            <a-select v-model:value="queryParams.app_name" placeholder="请选择应用" allow-clear :options="appOptions"
              @change="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="分类" class="filter-item">
            <a-input v-model:value="queryParams.class_name" placeholder="请输入分类名称" allow-clear
              @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
      </template>

      <!-- 操作按钮 -->
      <template #actions>
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
      </template>

      <!-- 表格列自定义 -->
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

      <!-- 弹窗表单 -->
      <template #modal-form="{ form }">
        <a-form-item label="模板名称" name="name">
          <a-input v-model:value="form.name" placeholder="请输入模板名称" />
        </a-form-item>
        <a-form-item label="应用名称" name="app_name">
          <a-select v-model:value="form.app_name" placeholder="请选择应用" :options="appOptions" />
        </a-form-item>
        <a-form-item v-if="userStore.isSuperUser" label="租户" name="tenant_id">
          <a-select v-model:value="form.tenant_id" placeholder="请选择租户" :options="tenantOptions" />
        </a-form-item>
        <a-form-item label="分类" name="class_name">
          <a-input v-model:value="form.class_name" placeholder="请输入分类名称" />
        </a-form-item>
        <a-form-item label="摘要" name="summary">
          <a-textarea v-model:value="form.summary" placeholder="请输入模板摘要" :rows="2" />
        </a-form-item>
        <a-form-item label="模板内容" name="template_content">
          <a-textarea v-model:value="form.template_content" placeholder="请输入模板内容" :rows="10" />
        </a-form-item>
      </template>
    </CrudTable>

    <!-- CSV导入弹窗 -->
    <a-modal v-model:open="importModalVisible" title="CSV批量导入总结模板" width="600px" :confirm-loading="importLoading"
      @ok="handleImport" @cancel="importModalVisible = false">
      <a-form :model="importForm" :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="应用名称" required>
          <a-select v-model:value="importForm.app_name" placeholder="请选择应用" :options="appOptions" style="width: 100%" />
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
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { useUserStore } from '@/store'
import { formatDateTime } from '@/utils'
import { DownloadOutlined, PlusOutlined, UploadOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'TemplatePage' })

const userStore = useUserStore()
const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  name: '',
  app_name: '',
  class_name: '',
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
const modalAction = ref<'add' | 'edit'>('add')
const modalForm = reactive({
  id: undefined as number | undefined,
  name: '',
  app_name: '',
  tenant_id: undefined as number | undefined,
  class_name: '',
  summary: '',
  template_content: '',
})

// 其他数据
const tenantOptions = ref<any[]>([])
const appOptions = ref<any[]>([])

// CSV导入相关
const importModalVisible = ref(false)
const importLoading = ref(false)
const importForm = reactive({
  app_name: '',
  tenant_id: undefined as number | undefined,
})
const fileList = ref<any[]>([])

// 计算属性
const columns = computed(() => [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '模板名称', dataIndex: 'name', key: 'name' },
  { title: '应用名称', dataIndex: 'app_name', key: 'app_name' },
  { title: '分类', dataIndex: 'class_name', key: 'class_name' },
  { title: '摘要', key: 'summary', ellipsis: true },
  { title: '创建时间', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 150, fixed: 'right' },
])

const filterItemCount = computed(() => {
  let count = 3
  if (userStore.isSuperUser) count++
  return count
})

const modalRules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  app_name: [{ required: true, message: '请选择应用', trigger: 'change' }],
  tenant_id: [{ required: true, message: '请选择租户', trigger: 'change', type: 'number' }],
  class_name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
}

// 加载数据
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

const fetchAppOptions = async (tenantId?: number) => {
  try {
    const params: any = {}
    // 如果指定了租户，只加载该租户的应用
    if (tenantId && tenantId > 0) {
      params.tenant_id = tenantId
    }
    const res: any = await api.getAppSelect(params)
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

const handleTenantChange = (tenantId: number) => {
  // 重置应用选择
  queryParams.app_name = ''
  // 重新加载该租户的应用
  fetchAppOptions(tenantId)
  // 刷新数据
  handleSearch()
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchData()
}

const handleAdd = () => {
  modalAction.value = 'add'
  modalTitle.value = '新建模板'
  Object.assign(modalForm, {
    id: undefined,
    name: '',
    app_name: '',
    tenant_id: userStore.isSuperUser ? undefined : userStore.userInfo?.current_tenant_id,
    class_name: '',
    summary: '',
    template_content: '',
  })
  crudTableRef.value?.openAddModal()
}

const handleEdit = (record: any) => {
  modalAction.value = 'edit'
  modalTitle.value = '编辑模板'
  Object.assign(modalForm, { ...record })
  crudTableRef.value?.openEditModal(record)
}

const handleSave = async (form: Record<string, any>, action: 'add' | 'edit') => {
  modalLoading.value = true
  try {
    const apiCall = action === 'add' ? api.createTemplate : api.updateTemplate
    const res: any = await apiCall({ ...form })
    if (res.code === 200) {
      message.success(action === 'add' ? '创建成功' : '更新成功')
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

// CSV导入
const showImportModal = () => {
  importForm.app_name = ''
  importForm.tenant_id = userStore.isSuperUser ? undefined : userStore.userInfo?.current_tenant_id
  fileList.value = []
  importModalVisible.value = true
}

const beforeUpload = (file: any) => {
  fileList.value = [file]
  return false
}

const handleImport = async () => {
  if (!importForm.app_name) {
    message.error('请选择应用名称')
    return
  }
  if (userStore.isSuperUser && !importForm.tenant_id) {
    message.error('请选择租户')
    return
  }
  if (fileList.value.length === 0) {
    message.error('请选择CSV文件')
    return
  }

  importLoading.value = true
  try {
    const formData = new FormData()
    formData.append('file', fileList.value[0])
    formData.append('app_name', importForm.app_name)
    if (importForm.tenant_id) {
      formData.append('tenant_id', String(importForm.tenant_id))
    }

    const res: any = await api.importTemplateFromCsv(fileList.value[0], importForm.app_name, importForm.tenant_id)
    if (res.code === 200) {
      message.success(`导入成功，共导入 ${res.data?.count || 0} 条记录`)
      importModalVisible.value = false
      fetchData()
    } else {
      message.error(res.msg || '导入失败')
    }
  } catch (error) {
    console.error('导入失败', error)
    message.error('导入失败')
  } finally {
    importLoading.value = false
  }
}

const downloadTemplate = () => {
  const csvContent = 'name,class_name,summary,template_content\n示例模板,分类1,这是一个示例模板,模板内容...'
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = 'template_import_template.csv'
  link.click()
  URL.revokeObjectURL(link.href)
}

onMounted(() => {
  fetchData()
  fetchTenantOptions()
  fetchAppOptions()
})
</script>

<style scoped lang="less">
.template-page {

  .ellipsis-text {
    display: inline-block;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
