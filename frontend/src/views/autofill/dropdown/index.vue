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
        <a-form-item label="选项编码" name="option_value">
          <a-input v-model:value="form.option_value" placeholder="请输入选项编码（唯一标识）" />
        </a-form-item>
        <a-form-item label="应用名称" name="app_name">
          <a-select v-model:value="form.app_name" placeholder="请选择应用" :options="appOptions"
            @change="(val: string) => handleAppChange(val, form)" />
        </a-form-item>
        <a-form-item label="分类" name="class_name">
          <a-input v-model:value="form.class_name" placeholder="请输入分类名称" />
        </a-form-item>
        <a-form-item label="父选项ID" name="parent_id">
          <a-input-number v-model:value="form.parent_id" placeholder="0表示顶级选项" style="width: 100%" />
        </a-form-item>
        <a-form-item label="显示标签" name="summary">
          <a-textarea v-model:value="form.summary" placeholder="请输入显示标签（下拉框中显示的文本）" :rows="2" />
        </a-form-item>
        <a-form-item label="选项说明" name="description">
          <a-textarea v-model:value="form.description" placeholder="请输入选项说明（帮助提示信息）" :rows="4" />
        </a-form-item>
      </template>
    </CrudTable>

    <!-- 树形结构弹窗 -->
    <a-modal v-model:open="treeModalVisible" title="下拉选项树形结构" width="700px" :footer="null">
      <a-form :model="treeQuery" layout="inline" style="margin-bottom: 16px">
        <a-form-item label="应用名称">
          <a-select v-model:value="treeQuery.app_name" placeholder="请选择应用" :options="appOptions" style="width: 180px"
            @change="handleTreeAppChange" />
        </a-form-item>
        <a-form-item label="分类">
          <a-select v-model:value="treeQuery.class_name" placeholder="请选择分类" :options="classOptions"
            style="width: 180px" allow-clear />
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
    <a-modal v-model:open="importModalVisible" title="CSV批量导入下拉选项" width="900px" :confirm-loading="importLoading"
      @ok="handleImport" @cancel="importModalVisible = false">
      <a-form :model="importForm" :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="应用名称" required>
          <a-select v-model:value="importForm.app_name" placeholder="请选择应用" :options="appOptions" style="width: 100%" />
        </a-form-item>
        <a-form-item label="分类名称">
          <a-input v-model:value="importForm.class_name" placeholder="请输入分类名称，默认为'事件类型'" />
        </a-form-item>
        <a-form-item label="CSV文件" required>
          <div @drop.prevent="handleDrop" @dragover.prevent @dragenter.prevent>
            <a-upload-dragger v-model:file-list="fileList" :custom-request="handleCustomRequest"
              @change="handleFileChange" accept=".csv" :disabled="!importForm.app_name" :multiple="false"
              :openFileDialogOnClick="true">
              <p class="ant-upload-drag-icon">
                <UploadOutlined />
              </p>
              <p class="ant-upload-text">点击或拖拽CSV文件到此处上传</p>
              <p class="ant-upload-hint">
                请先选择应用，然后上传CSV文件，系统将自动识别字段映射。支持一级、二级或三级层级结构导入。
              </p>
            </a-upload-dragger>
          </div>
        </a-form-item>

        <!-- 字段映射配置 -->
        <div v-if="csvPreview.fields.length > 0">
          <a-divider>字段映射配置</a-divider>

          <!-- 一级字段映射 -->
          <a-card size="small" title="一级选项字段映射" style="margin-bottom: 16px">
            <a-row :gutter="24">
              <a-col :span="12">
                <a-form-item label="显示标签字段" required>
                  <a-select v-model:value="importForm.fieldMapping.level1_name" :options="csvFieldOptions"
                    placeholder="选择显示标签字段" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="选项编码字段" required>
                  <a-select v-model:value="importForm.fieldMapping.level1_id" :options="csvFieldOptions"
                    placeholder="选择选项编码字段" style="width: 100%" />
                </a-form-item>
              </a-col>
            </a-row>
            <a-row :gutter="24">
              <a-col :span="12">
                <a-form-item label="选项说明字段">
                  <a-select v-model:value="importForm.fieldMapping.level1_desc" :options="csvFieldOptions"
                    placeholder="选择选项说明字段（可选）" style="width: 100%" allow-clear />
                </a-form-item>
              </a-col>
            </a-row>
          </a-card>

          <!-- 二级字段映射 -->
          <a-card size="small" title="二级选项字段映射（可选）" style="margin-bottom: 16px">
            <a-row :gutter="24">
              <a-col :span="12">
                <a-form-item label="显示标签字段">
                  <a-select v-model:value="importForm.fieldMapping.level2_name" :options="csvFieldOptions"
                    placeholder="不导入二级则留空" style="width: 100%" allow-clear />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="选项编码字段">
                  <a-select v-model:value="importForm.fieldMapping.level2_id" :options="csvFieldOptions"
                    placeholder="不导入二级则留空" style="width: 100%" allow-clear />
                </a-form-item>
              </a-col>
            </a-row>
            <a-row :gutter="24">
              <a-col :span="12">
                <a-form-item label="选项说明字段">
                  <a-select v-model:value="importForm.fieldMapping.level2_desc" :options="csvFieldOptions"
                    placeholder="选择选项说明字段（可选）" style="width: 100%" allow-clear />
                </a-form-item>
              </a-col>
            </a-row>
          </a-card>

          <!-- 三级字段映射 -->
          <a-card size="small" title="三级选项字段映射（可选）" style="margin-bottom: 16px">
            <a-row :gutter="24">
              <a-col :span="12">
                <a-form-item label="显示标签字段">
                  <a-select v-model:value="importForm.fieldMapping.level3_name" :options="csvFieldOptions"
                    placeholder="不导入三级则留空" style="width: 100%" allow-clear />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="选项编码字段">
                  <a-select v-model:value="importForm.fieldMapping.level3_id" :options="csvFieldOptions"
                    placeholder="不导入三级则留空" style="width: 100%" allow-clear />
                </a-form-item>
              </a-col>
            </a-row>
            <a-row :gutter="24">
              <a-col :span="12">
                <a-form-item label="选项说明字段">
                  <a-select v-model:value="importForm.fieldMapping.level3_desc" :options="csvFieldOptions"
                    placeholder="选择选项说明字段（可选）" style="width: 100%" allow-clear />
                </a-form-item>
              </a-col>
            </a-row>
          </a-card>

          <!-- 样例数据预览 -->
          <a-card size="small" title="样例数据预览">
            <a-table :dataSource="csvPreview.sampleData" :columns="csvPreviewColumns" size="small"
              :pagination="false" />
          </a-card>
        </div>
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
  class_name: '事件类型',
  fieldMapping: {
    level1_name: '',
    level1_id: '',
    level1_desc: '',
    level2_name: '',
    level2_id: '',
    level2_desc: '',
    level3_name: '',
    level3_id: '',
    level3_desc: '',
  } as Record<string, string>,
})
const fileList = ref<any[]>([])
const csvFile = ref<File | null>(null)  // 存储原始文件对象
const csvPreview = reactive({
  fields: [] as string[],
  sampleData: [] as any[],
  totalRows: 0,
})

// CSV字段选项
const csvFieldOptions = computed(() => {
  return csvPreview.fields.map((field: string) => ({
    label: field,
    value: field,
  }))
})

// CSV预览表格列
const csvPreviewColumns = computed(() => {
  return csvPreview.fields.map((field: string) => ({
    title: field,
    dataIndex: field,
    key: field,
    ellipsis: true,
  }))
})

// 计算属性
const columns = computed(() => [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '选项编码', dataIndex: 'option_value', key: 'option_value' },
  { title: '显示标签', key: 'summary', ellipsis: true },
  { title: '应用名称', dataIndex: 'app_name', key: 'app_name' },
  { title: '分类', dataIndex: 'class_name', key: 'class_name' },
  { title: '父选项', key: 'parent_id', width: 100 },
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
  importForm.class_name = '事件类型'
  importForm.fieldMapping = {
    level1_name: '',
    level1_id: '',
    level1_desc: '',
    level2_name: '',
    level2_id: '',
    level2_desc: '',
    level3_name: '',
    level3_id: '',
    level3_desc: '',
  }
  csvPreview.fields = []
  csvPreview.sampleData = []
  csvPreview.totalRows = 0
  fileList.value = []
  csvFile.value = null
  importModalVisible.value = true
}

const beforeUpload = (file: any) => {
  fileList.value = [file]
  csvFile.value = file
  return false
}

// 自定义上传请求（阻止默认上传行为）
const handleCustomRequest = () => {
  // 不做任何操作，阻止默认上传
}

// 处理拖拽事件，阻止浏览器默认行为
const handleDrop = (e: DragEvent) => {
  e.preventDefault()
  e.stopPropagation()

  const files = e.dataTransfer?.files
  if (!files || files.length === 0) return

  const file = files[0]
  if (!file.name.endsWith('.csv')) {
    message.error('请选择CSV文件')
    return
  }

  if (!importForm.app_name) {
    message.error('请先选择应用名称')
    return
  }

  // 手动触发文件处理
  const fileInfo = {
    file: {
      originFileObj: file,
      name: file.name,
      status: 'done'
    },
    fileList: [{ originFileObj: file, name: file.name, status: 'done' }]
  }
  handleFileChange(fileInfo)
}

// 处理文件变化（点击选择或拖拽上传都会触发）
const handleFileChange = async (info: any) => {
  // 获取实际的 File 对象
  const file = info.file.originFileObj || info.file
  if (!file) return

  // 检查文件类型
  if (!file.name || !file.name.endsWith('.csv')) {
    message.error('请选择CSV文件')
    fileList.value = []
    csvFile.value = null
    return
  }

  if (!importForm.app_name) {
    message.error('请先选择应用名称')
    fileList.value = []
    csvFile.value = null
    return
  }

  // 预览CSV结构
  try {
    const res: any = await api.previewCsvStructure(file)
    if (res.code === 200) {
      csvPreview.fields = res.data.fields || []
      csvPreview.sampleData = res.data.sample_data || []
      csvPreview.totalRows = res.data.total_rows || 0

      // 应用建议的字段映射
      const suggested = res.data.suggested_mapping || {}
      importForm.fieldMapping = {
        level1_name: suggested.level1_name || '',
        level1_id: suggested.level1_id || '',
        level1_desc: suggested.level1_desc || '',
        level2_name: suggested.level2_name || '',
        level2_id: suggested.level2_id || '',
        level2_desc: suggested.level2_desc || '',
        level3_name: suggested.level3_name || '',
        level3_id: suggested.level3_id || '',
        level3_desc: suggested.level3_desc || '',
      }

      csvFile.value = file
      message.success(`CSV解析成功，共 ${csvPreview.totalRows} 行数据`)
    } else {
      message.error(res.msg || '解析CSV失败')
      fileList.value = []
      csvFile.value = null
    }
  } catch (error) {
    console.error('预览CSV失败', error)
    message.error('预览CSV失败')
    fileList.value = []
    csvFile.value = null
  }
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

  // 验证字段映射 - 一级必填，二级三级可选
  const fm = importForm.fieldMapping
  if (!fm.level1_name || !fm.level1_id) {
    message.error('请选择一级选项的显示标签字段和选项编码字段')
    return
  }
  // 如果选择了二级名称字段，则二级编码字段也必须选择
  if ((fm.level2_name && !fm.level2_id) || (!fm.level2_name && fm.level2_id)) {
    message.error('二级选项的显示标签字段和选项编码字段必须同时填写或同时留空')
    return
  }
  // 如果选择了三级名称字段，则三级编码字段也必须选择
  if ((fm.level3_name && !fm.level3_id) || (!fm.level3_name && fm.level3_id)) {
    message.error('三级选项的显示标签字段和选项编码字段必须同时填写或同时留空')
    return
  }

  importLoading.value = true
  try {
    const res: any = await api.importHierarchicalDropdownFromCsv(
      csvFile.value!,
      importForm.app_name,
      importForm.class_name,
      fm.level1_name,
      fm.level1_id,
      fm.level1_desc,
      fm.level2_name,
      fm.level2_id,
      fm.level2_desc,
      fm.level3_name,
      fm.level3_id,
      fm.level3_desc
    )

    if (res.code === 200) {
      const data = res.data || {}
      const level2Text = data.level2_count > 0 ? `，二级：${data.level2_count}个` : ''
      const level3Text = data.level3_count > 0 ? `，三级：${data.level3_count}个` : ''
      message.success(`导入成功！一级：${data.level1_count}个${level2Text}${level3Text}`)
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
  const csvContent = '一级事件类型,一级事件类型ID,一级事件类型填写说明,二级事件类型,二级事件类型ID,二级事件类型填写说明,三级事件类型,三级事件类型ID,三级事件类型填写说明\n道路救援,EVT001,请选择道路救援类型,拖车服务,EVT001001,车辆无法移动时使用,标准拖车,EVT001001001,普通道路拖车服务'
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
