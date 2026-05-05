<template>
  <div class="dropdown-page">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
      :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
      modal-width="700px" @search="handleSearch" @reset="handleReset" @table-change="handleTableChange"
      @modal-ok="handleSave">
      <!-- 筛选条件 -->
      <template #filter-items>
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
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="父选项ID" class="filter-item">
            <a-input-number v-model:value="queryParams.parent_id" placeholder="0表示顶级" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col v-if="userStore.isSuperUser" :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="租户" class="filter-item">
            <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户" allow-clear :options="tenantOptions"
              @change="handleSearch" />
          </a-form-item>
        </a-col>
      </template>

      <!-- 操作按钮 -->
      <template #actions>
        <a-button v-permission="'post/api/v1/autofill/dropdown/create'" type="primary" @click="handleAdd">
          <PlusOutlined />
          新建选项
        </a-button>
        <a-button style="margin-left: 8px" @click="showTreeModal">
          <ApartmentOutlined />
          查看树形结构
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
        <template v-if="column.key === 'parent_id'">
          <a-tag v-if="record.parent_id === 0" color="blue">顶级</a-tag>
          <span v-else>{{ record.parent_id }}</span>
        </template>
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
            <a-button v-permission="'post/api/v1/autofill/dropdown/update'" type="link" size="small"
              @click="handleEdit(record)">编辑</a-button>
            <a-popconfirm title="确定删除该选项吗？" @confirm="handleDelete(record)">
              <a-button v-permission="'delete/api/v1/autofill/dropdown/delete'" type="link" danger
                size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>

      <!-- 弹窗表单 -->
      <template #modal-form="{ form }">
        <a-form-item label="选项值" name="option_value">
          <a-input v-model:value="form.option_value" placeholder="请输入选项值" />
        </a-form-item>
        <a-form-item label="应用名称" name="app_name">
          <a-select v-model:value="form.app_name" placeholder="请选择应用" :options="appOptions" @change="(val) => handleAppChange(val, form)" />
        </a-form-item>
        <a-form-item label="分类" name="class_name">
          <a-input v-model:value="form.class_name" placeholder="请输入分类名称" />
        </a-form-item>
        <a-form-item label="父选项ID" name="parent_id">
          <a-input-number v-model:value="form.parent_id" placeholder="0表示顶级选项" style="width: 100%" />
        </a-form-item>
        <a-form-item label="摘要" name="summary">
          <a-textarea v-model:value="form.summary" placeholder="请输入字段摘要" :rows="2" />
        </a-form-item>
        <a-form-item label="详细说明" name="description">
          <a-textarea v-model:value="form.description" placeholder="请输入详细说明" :rows="4" />
        </a-form-item>
      </template>
    </CrudTable>

    <!-- 树形结构弹窗 -->
    <a-modal v-model:open="treeModalVisible" title="下拉选项树形结构" width="700px" :footer="null">
      <a-form :model="treeQuery" layout="inline" style="margin-bottom: 16px">
        <a-form-item label="应用名称">
          <a-select v-model:value="treeQuery.app_name" placeholder="请选择应用" :options="appOptions" style="width: 180px" @change="handleTreeAppChange" />
        </a-form-item>
        <a-form-item label="分类">
          <a-select v-model:value="treeQuery.class_name" placeholder="请选择分类" :options="classOptions" style="width: 180px" allow-clear />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="fetchTreeData">查询</a-button>
        </a-form-item>
      </a-form>
      <a-tree :tree-data="treeData" :field-names="{ title: 'option_value', key: 'id', children: 'children' }"
        block-node>
        <template #title="{ option_value, summary }">
          <span>{{ option_value }}</span>
          <span v-if="summary" style="color: #999; margin-left: 8px">({{ summary }})</span>
        </template>
      </a-tree>
    </a-modal>

    <!-- CSV导入弹窗 -->
    <a-modal v-model:open="importModalVisible" title="CSV批量导入下拉选项" width="600px" :confirm-loading="importLoading"
      @ok="handleImport" @cancel="importModalVisible = false">
      <a-form :model="importForm" :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="应用名称" required>
          <a-select v-model:value="importForm.app_name" placeholder="请选择应用" :options="appOptions" style="width: 100%" />
        </a-form-item>
        <a-form-item label="CSV文件" required>
          <a-upload v-model:file-list="fileList" :before-upload="beforeUpload" accept=".csv">
            <a-button>
              <UploadOutlined />
              选择文件
            </a-button>
          </a-upload>
          <div style="margin-top: 8px; color: #999; font-size: 12px">
            CSV格式：option_value,summary,class_name,parent_option_value
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
import { ApartmentOutlined, DownloadOutlined, PlusOutlined, UploadOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'DropdownPage' })

const userStore = useUserStore()
const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  app_name: '',
  class_name: '',
  parent_id: undefined as number | undefined,
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
  option_value: '',
  app_name: '',
  tenant_id: undefined as number | undefined,
  class_name: '',
  parent_id: 0,
  summary: '',
  description: '',
})

// 其他数据
const tenantOptions = ref<any[]>([])
const appOptions = ref<any[]>([])

// 树形结构相关
const treeModalVisible = ref(false)
const treeQuery = reactive({
  app_name: undefined as string | undefined,
  class_name: '',
})
const treeData = ref<any[]>([])
const classOptions = ref<any[]>([])

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
  { title: '选项值', dataIndex: 'option_value', key: 'option_value' },
  { title: '应用名称', dataIndex: 'app_name', key: 'app_name' },
  { title: '分类', dataIndex: 'class_name', key: 'class_name' },
  { title: '父选项', key: 'parent_id', width: 100 },
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
  option_value: [{ required: true, message: '请输入选项值', trigger: 'blur' }],
  app_name: [{ required: true, message: '请选择应用', trigger: 'change' }],
  class_name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
}

// 加载数据
const fetchData = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.current,
      page_size: pagination.pageSize,
      app_name: queryParams.app_name,
      class_name: queryParams.class_name,
      tenant_id: queryParams.tenant_id,
    }
    if (queryParams.parent_id !== undefined) {
      params.parent_id = queryParams.parent_id
    }
    const res: any = await api.getDropdownList(params)
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
  queryParams.app_name = ''
  queryParams.class_name = ''
  queryParams.parent_id = undefined
  queryParams.tenant_id = undefined
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
  modalTitle.value = '新建选项'
  Object.assign(modalForm, {
    id: undefined,
    option_value: '',
    app_name: '',
    tenant_id: undefined,
    class_name: '',
    parent_id: 0,
    summary: '',
    description: '',
  })
  crudTableRef.value?.openAddModal()
}

const handleAppChange = (appName: string, form: any) => {
  // 应用改变时，租户会自动从应用继承，不需要手动设置
  form.tenant_id = undefined
}

const handleEdit = (record: any) => {
  modalAction.value = 'edit'
  modalTitle.value = '编辑选项'
  Object.assign(modalForm, { ...record })
  crudTableRef.value?.openEditModal(record)
}

const handleSave = async (form: Record<string, any>, action: 'add' | 'edit') => {
  modalLoading.value = true
  try {
    const apiCall = action === 'add' ? api.createDropdown : api.updateDropdown
    const res: any = await apiCall(form)
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
    const res: any = await api.deleteDropdown({ id: record.id })
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

// 树形结构
const showTreeModal = () => {
  treeQuery.app_name = undefined
  treeQuery.class_name = ''
  treeData.value = []
  classOptions.value = []
  treeModalVisible.value = true
}

const handleTreeAppChange = async (appName: string) => {
  treeQuery.class_name = ''
  classOptions.value = []
  treeQuery.app_name = appName
  if (!appName) return
  try {
    const res: any = await api.getDropdownClasses({ app_name: appName })
    if (res.code === 200) {
      classOptions.value = (res.data || []).map((name: string) => ({
        label: name,
        value: name
      }))
    }
  } catch (error) {
    console.error('获取分类列表失败', error)
  }
}

const fetchTreeData = async () => {
  if (!treeQuery.app_name) {
    message.warning('请选择应用名称')
    return
  }
  try {
    const params: any = { app_name: treeQuery.app_name }
    if (treeQuery.class_name) {
      params.class_name = treeQuery.class_name
    }
    const res: any = await api.getDropdownTree(params)
    if (res.code === 200) {
      treeData.value = res.data || []
    }
  } catch (error) {
    console.error('获取树形数据失败', error)
  }
}

// CSV导入
const showImportModal = () => {
  importForm.app_name = ''
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
  if (fileList.value.length === 0) {
    message.error('请选择CSV文件')
    return
  }

  importLoading.value = true
  try {
    const res: any = await api.importDropdownFromCsv(fileList.value[0], importForm.app_name)
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
  const csvContent = 'option_value,summary,class_name,parent_option_value\n选项值1,摘要说明,分类1,父选项值'
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = 'dropdown_import_template.csv'
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
.dropdown-page {

  .ellipsis-text {
    display: inline-block;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
