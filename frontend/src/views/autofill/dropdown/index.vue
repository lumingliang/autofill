<template>
  <a-layout class="dropdown-page crud-page">
    <a-layout-content style="padding: 16px">
      <a-card>
        <a-form :model="queryParams" class="crud-filter-form smart-filter-form">
          <a-row :gutter="16" class="filter-row">
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
        </div>

        <a-table class="crud-table" :columns="columns" :data-source="tableData" :loading="loading"
          :pagination="pagination" row-key="id" :scroll="{ x: 'max-content' }" @change="handleTableChange">
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
        </a-table>
      </a-card>

      <!-- 新增/编辑 弹窗 -->
      <a-modal v-model:open="modalVisible" :title="modalTitle" :confirm-loading="modalLoading" @ok="handleSave"
        @cancel="modalVisible = false" width="700px">
        <a-form ref="modalFormRef" :model="modalForm" :rules="modalRules" :label-col="{ span: 6 }"
          :wrapper-col="{ span: 16 }">
          <a-form-item label="选项值" name="option_value">
            <a-input v-model:value="modalForm.option_value" placeholder="请输入选项值" />
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
          <a-form-item label="父选项ID" name="parent_id">
            <a-input-number v-model:value="modalForm.parent_id" placeholder="0表示顶级选项" style="width: 100%" />
          </a-form-item>
          <a-form-item label="摘要" name="summary">
            <a-textarea v-model:value="modalForm.summary" placeholder="请输入字段摘要" :rows="2" />
          </a-form-item>
          <a-form-item label="详细说明" name="description">
            <a-textarea v-model:value="modalForm.description" placeholder="请输入详细说明" :rows="4" />
          </a-form-item>
        </a-form>
      </a-modal>

      <!-- 树形结构弹窗 -->
      <a-modal v-model:open="treeModalVisible" title="下拉选项树形结构" width="600px" :footer="null">
        <a-form :model="treeQuery" layout="inline" style="margin-bottom: 16px">
          <a-form-item label="应用名称">
            <a-select v-model:value="treeQuery.app_name" placeholder="请选择应用" :options="appOptions"
              style="width: 200px" />
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
              CSV格式：option_value,summary,class_name,parent_option_value
            </div>
          </a-form-item>
        </a-form>
      </a-modal>
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { PlusOutlined, SearchOutlined, ReloadOutlined, ApartmentOutlined, UploadOutlined, DownloadOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '@/store'
import api from '@/api'
import { formatDateTime } from '@/utils'
import { message } from 'ant-design-vue'

const userStore = useUserStore()

const queryParams = reactive<any>({
  app_name: '',
  class_name: '',
  parent_id: undefined,
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
  { title: '选项值', dataIndex: 'option_value', key: 'option_value' },
  { title: '应用名称', dataIndex: 'app_name', key: 'app_name' },
  { title: '分类', dataIndex: 'class_name', key: 'class_name' },
  { title: '父选项', key: 'parent_id', width: 100 },
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
const modalTitle = computed(() => modalAction.value === 'add' ? '新建选项' : '编辑选项')
const modalFormRef = ref<any>(null)
const modalForm = reactive<any>({
  id: undefined,
  option_value: '',
  app_name: '',
  tenant_id: undefined,
  class_name: '',
  parent_id: 0,
  summary: '',
  description: '',
})

const modalRules = {
  option_value: [{ required: true, message: '请输入选项值', trigger: 'blur' }],
  app_name: [{ required: true, message: '请选择应用', trigger: 'change' }],
  tenant_id: [{ required: true, message: '请选择租户', trigger: 'change', type: 'number' }],
  class_name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
}

// 树形结构相关
const treeModalVisible = ref(false)
const treeQuery = reactive({
  app_name: '',
})
const treeData = ref<any[]>([])

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

const resetModalForm = () => {
  modalForm.id = undefined
  modalForm.option_value = ''
  modalForm.app_name = ''
  modalForm.tenant_id = userStore.isSuperUser ? undefined : userStore.userInfo?.current_tenant_id
  modalForm.class_name = ''
  modalForm.parent_id = 0
  modalForm.domain = ''
  modalForm.summary = ''
  modalForm.description = ''
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

    const apiCall = modalAction.value === 'add' ? api.createDropdown : api.updateDropdown
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

// 树形结构相关方法
const showTreeModal = () => {
  treeModalVisible.value = true
  treeQuery.app_name = queryParams.app_name
  if (treeQuery.app_name) {
    fetchTreeData()
  }
}

const fetchTreeData = async () => {
  if (!treeQuery.app_name) {
    message.warning('请选择应用')
    return
  }
  try {
    const res: any = await api.getDropdownTree({ app_name: treeQuery.app_name })
    if (res.code === 200) {
      treeData.value = res.data || []
    }
  } catch (error) {
    console.error('获取树形数据失败', error)
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
    const res: any = await api.importDropdownFromCsv(
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
  const template = `option_value,summary,class_name,parent_option_value
产品咨询,客户询问车辆配置、操作、活动、价格、网点、保修、保养、备件等相关信息。,业务类型,
4S店,客户询问车辆配置、操作、活动、价格、网点、保修、保养、备件等相关信息。,业务类型,
救援,客户反馈车辆无法行驶或无法继续安全行驶时，需协助的事件。,业务类型,
业务互转,,业务类型,
表扬,客户对产品或服务提出表扬。,业务类型,
建议,客户对产品或服务提出改进意见或建议,业务类型,
售前投诉,客户通过厂端内部平台反馈的售前类问题,投诉类型,
售后投诉,客户通过厂端内部平台反馈对售后维保或服务等存在不满或抱怨,投诉类型,
内部投诉,客户/经销商/服务店反馈对客服及公司职能部门服务等问题引起的纠纷或不满,投诉类型,
智能网联,客户反馈对比亚迪APP云控功能等问题的疑问/投诉/建议,业务类型,
三级报警,指比亚迪新能源汽车监控预警中心接收到客户车辆产生了第三级故障信息而触发报警，简称"三级报警"。,业务类型,`

  const blob = new Blob([template], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = 'dropdown_template.csv'
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
