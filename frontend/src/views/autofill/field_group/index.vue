<template>
  <div class="field-group-management">
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
          <a-form-item label="字段组名称" class="filter-item">
            <a-input v-model:value="queryParams.group_name" placeholder="请输入字段组名称" allow-clear
              @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="应用名称" class="filter-item">
            <a-select v-model:value="queryParams.app_name" placeholder="请选择应用" allow-clear :options="appOptions"
              @change="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="页面" class="filter-item">
            <a-select v-model:value="queryParams.page_id" placeholder="请选择页面" allow-clear :options="pageOptions"
              @change="handleSearch" />
          </a-form-item>
        </a-col>
      </template>

      <!-- 操作按钮 -->
      <template #actions>
        <a-button v-permission="'post/api/v1/autofill/field_group/create'" type="primary" @click="handleAdd">
          <PlusOutlined />
          新建字段组
        </a-button>
      </template>

      <!-- 表格列自定义 -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'is_active'">
          <a-tag :color="record.is_active ? 'green' : 'red'">
            {{ record.is_active ? '启用' : '禁用' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'prompt_template_base'">
          <a-tooltip :title="record.prompt_template_base">
            <span class="ellipsis-text">{{ record.prompt_template_base || '-' }}</span>
          </a-tooltip>
        </template>
        <template v-if="column.key === 'created_at'">
          <span v-if="record.created_at">{{ formatDateTime(record.created_at) }}</span>
          <span v-else>-</span>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button type="link" size="small" @click="handleViewDetail(record)">详情</a-button>
            <a-button type="link" size="small" @click="handleManageFields(record)">管理字段</a-button>
            <a-button v-permission="'post/api/v1/autofill/field_group/update'" type="link" size="small"
              @click="handleEdit(record)">编辑</a-button>
            <a-popconfirm title="确定删除该字段组吗？" @confirm="handleDelete(record)">
              <a-button v-permission="'delete/api/v1/autofill/field_group/delete'" type="link" danger
                size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>

      <!-- 弹窗表单 -->
      <template #modal-form="{ form }">
        <a-form-item v-if="userStore.isSuperUser" label="所属租户" name="tenant_id">
          <a-select v-model:value="form.tenant_id" placeholder="请选择租户" :options="tenantOptions"
            @change="(val: number) => handleModalTenantChange(val, form)" />
        </a-form-item>
        <a-form-item label="字段组名称" name="group_name">
          <a-input v-model:value="form.group_name" placeholder="请输入字段组名称" />
        </a-form-item>
        <a-form-item label="所属页面" name="page_id">
          <a-select v-model:value="form.page_id" placeholder="请选择页面" :options="pageOptions"
            :disabled="modalAction === 'edit'" @change="handlePageChange" />
        </a-form-item>
        <a-form-item label="Prompt模板" name="prompt_template_base">
          <a-textarea v-model:value="form.prompt_template_base"
            placeholder="请输入Prompt基础模板，使用{{fields_instructions}}和{{query}}作为占位符" :rows="6" />
        </a-form-item>
        <a-form-item label="输出模板" name="output_templates">
          <div class="output-templates-editor">
            <div v-for="key in Object.keys(form.output_templates)" :key="key" class="template-item">
              <a-card size="small" :title="key" class="template-card">
                <template #extra>
                  <a-button type="link" danger size="small" @click="removeOutputTemplate(key)">
                    <DeleteOutlined />
                  </a-button>
                </template>
                <a-form-item label="模板内容" class="mb-2">
                  <a-textarea v-model:value="form.output_templates[key].template" placeholder="请输入模板内容" :rows="4" />
                </a-form-item>
                <a-form-item label="描述" class="mb-0">
                  <a-input v-model:value="form.output_templates[key].description" placeholder="请输入模板描述" />
                </a-form-item>
              </a-card>
            </div>
            <a-button type="dashed" block @click="showAddTemplateModal">
              <PlusOutlined />
              添加输出模板
            </a-button>
          </div>
        </a-form-item>
        <a-form-item label="字段组描述" name="description">
          <a-textarea v-model:value="form.description" placeholder="请输入字段组描述" :rows="3" />
        </a-form-item>
        <a-form-item label="状态" name="is_active">
          <a-switch v-model:checked="form.is_active" />
        </a-form-item>
      </template>
    </CrudTable>

    <!-- 字段管理弹窗 -->
    <a-modal v-model:open="fieldModalVisible" :title="`管理字段 - ${currentFieldGroup?.group_name}`" width="1000px"
      :footer="null">
      <FieldSpecManagement :field-group-id="currentFieldGroup?.id" :field-group-name="currentFieldGroup?.group_name"
        @close="fieldModalVisible = false" />
    </a-modal>

    <!-- 详情弹窗 -->
    <a-modal v-model:open="detailModalVisible" title="字段组详情" width="1200px" :footer="null">
      <div v-if="detailLoading" class="detail-loading">
        <a-spin size="large" />
      </div>
      <div v-else-if="detailData" class="detail-content">
        <!-- 基本信息 -->
        <a-card title="基本信息" class="detail-card">
          <a-descriptions :column="3">
            <a-descriptions-item label="字段组名称">{{ detailData.basic_info?.group_name }}</a-descriptions-item>
            <a-descriptions-item label="编码">{{ detailData.basic_info?.group_code }}</a-descriptions-item>
            <a-descriptions-item label="应用">{{ detailData.basic_info?.app_name }}</a-descriptions-item>
            <a-descriptions-item label="页面">{{ detailData.basic_info?.page_name }}</a-descriptions-item>
            <a-descriptions-item label="版本">v{{ detailData.basic_info?.version }}</a-descriptions-item>
            <a-descriptions-item label="状态">
              <a-tag :color="detailData.basic_info?.is_active ? 'green' : 'red'">
                {{ detailData.basic_info?.is_active ? '启用' : '禁用' }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="描述" :span="3">{{ detailData.basic_info?.description || '-'
              }}</a-descriptions-item>
          </a-descriptions>
        </a-card>

        <!-- Prompt信息 -->
        <a-card title="Prompt信息" class="detail-card">
          <a-tabs>
            <a-tab-pane key="assembled" tab="组装后的Prompt">
              <a-typography-paragraph>
                <pre class="code-block">{{ detailData.prompt_info?.assembled_prompt }}</pre>
              </a-typography-paragraph>
            </a-tab-pane>
            <a-tab-pane key="template" tab="基础模板">
              <a-typography-paragraph>
                <pre class="code-block">{{ detailData.prompt_info?.template_base }}</pre>
              </a-typography-paragraph>
            </a-tab-pane>

          </a-tabs>
        </a-card>

        <!-- Function Calling Schema -->
        <a-card title="Function Calling Schema" class="detail-card">
          <JsonViewer :data="detailData.function_calling?.schema" title="Schema" :max-height="300"
            :show-toolbar="true" />
        </a-card>

        <!-- 输出模板 -->
        <a-card title="输出模板" class="detail-card">
          <a-tabs v-if="detailData.output_templates && Object.keys(detailData.output_templates).length > 0">
            <a-tab-pane v-for="(template, key) in detailData.output_templates" :key="key" :tab="key">
              <a-typography-paragraph>
                <pre class="code-block">{{ template.template }}</pre>
              </a-typography-paragraph>
              <a-descriptions size="small" :column="1">
                <a-descriptions-item label="描述">{{ template.description || '-' }}</a-descriptions-item>
              </a-descriptions>
            </a-tab-pane>
          </a-tabs>
          <a-empty v-else description="暂无输出模板" />
        </a-card>

        <!-- 字段明细 -->
        <a-card title="字段明细" class="detail-card">
          <a-table :dataSource="detailData.field_specs" :columns="fieldSpecColumns" size="small" :pagination="false">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'field_type'">
                <a-tag>{{ record.field_type }}</a-tag>
              </template>
              <template v-if="column.key === 'is_active'">
                <a-tag :color="record.is_active ? 'green' : 'red'">
                  {{ record.is_active ? '启用' : '禁用' }}
                </a-tag>
              </template>
              <template v-if="column.key === 'options'">
                <span v-if="record.options?.items">
                  {{record.options.items.filter((i: any) => !i.is_deleted).length}} 个选项
                </span>
                <span v-else>-</span>
              </template>
            </template>
          </a-table>
        </a-card>

        <!-- 操作按钮 -->
        <div class="detail-actions">
          <a-button type="primary" @click="handleExportMd">
            <DownloadOutlined />
            导出Markdown
          </a-button>
        </div>
      </div>
    </a-modal>

    <!-- 添加输出模板弹窗 -->
    <a-modal v-model:open="addTemplateModalVisible" title="添加输出模板" @ok="confirmAddTemplate">
      <a-form>
        <a-form-item label="模板名称" required>
          <a-input v-model:value="newTemplateKey" placeholder="请输入模板名称，如：summary、report等" />
        </a-form-item>
        <a-form-item label="模板内容">
          <a-textarea v-model:value="newTemplateForm.template" placeholder="请输入模板内容" :rows="4" />
        </a-form-item>
        <a-form-item label="描述">
          <a-input v-model:value="newTemplateForm.description" placeholder="请输入模板描述" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import JsonViewer from '@/components/JsonViewer/index.vue'
import { useUserStore } from '@/store'
import { formatDateTime } from '@/utils'
import FieldSpecManagement from '@/views/autofill/field_spec/index.vue'
import { DeleteOutlined, DownloadOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'FieldGroupManagement' })

const userStore = useUserStore()
const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  group_name: '',
  app_name: undefined as string | undefined,
  page_id: undefined as number | undefined,
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
  group_name: '',
  group_code: '',
  page_id: undefined as number | undefined,
  page_name: '',
  prompt_template_base: '',
  output_templates: {} as Record<string, any>,
  description: '',
  tenant_id: undefined as number | undefined,
  is_active: true,
})

// 字段管理弹窗
const fieldModalVisible = ref(false)
const currentFieldGroup = ref<any>(null)

// 添加输出模板弹窗
const addTemplateModalVisible = ref(false)
const newTemplateKey = ref('')
const newTemplateForm = reactive({
  template: '',
  description: ''
})

// 详情弹窗
const detailModalVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref<any>(null)
const currentDetailId = ref<number | null>(null)

// 字段明细表格列
const fieldSpecColumns = [
  { title: '字段名', dataIndex: 'field_name', key: 'field_name' },
  { title: '标签', dataIndex: 'field_label', key: 'field_label' },
  { title: '类型', key: 'field_type', width: 100 },
  { title: '填写说明', dataIndex: 'fill_instruction', key: 'fill_instruction', ellipsis: true },
  { title: '选项', key: 'options', width: 100 },
  { title: '状态', key: 'is_active', width: 80 },
]

// 其他数据
const appOptions = ref<any[]>([])
const pageOptions = ref<any[]>([])
const tenantOptions = ref<any[]>([])

// 计算属性
const columns = computed(() => [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '编码', dataIndex: 'group_code', key: 'group_code', width: 150 },
  { title: '字段组名称', dataIndex: 'group_name', key: 'group_name' },
  { title: '页面名称', dataIndex: 'page_name', key: 'page_name' },
  { title: '应用名称', dataIndex: 'app_name', key: 'app_name' },
  { title: '状态', key: 'is_active', width: 100 },
  { title: '创建时间', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 220, fixed: 'right' },
])

const filterItemCount = computed(() => {
  let count = 3
  if (userStore.isSuperUser) count++
  return count
})

const modalRules = {
  group_name: [
    { required: true, message: '请输入字段组名称', trigger: 'blur' },
  ],
  page_id: [
    { required: true, message: '请选择页面', trigger: 'change' },
  ],
}

// 方法
// 加载数据
const fetchData = async () => {
  loading.value = true
  try {
    const res: any = await api.getFieldGroupList({
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

const fetchAppOptions = async (tenantId?: number) => {
  try {
    const params: any = {}
    // 如果指定了租户（大于0），只加载该租户的应用
    if (tenantId && tenantId > 0) {
      params.tenant_id = tenantId
    }
    const res: any = await api.getAppSelect(params)
    if (res.code === 200) {
      appOptions.value = (res.data || []).map((app: any) => ({
        label: app.label,
        value: app.value,
      }))
    }
  } catch (error) {
    console.error('获取应用列表失败:', error)
  }
}

const fetchPageOptions = async (tenantId?: number) => {
  try {
    const params: any = {}
    // 如果指定了租户（大于0），只加载该租户的页面
    if (tenantId && tenantId > 0) {
      params.tenant_id = tenantId
    }
    const res: any = await api.getPageSelect(params)
    if (res.code === 200) {
      pageOptions.value = (res.data || []).map((p: any) => ({
        label: p.label,
        value: p.value,
      }))
    }
  } catch (error) {
    console.error('获取页面列表失败:', error)
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
    console.error('获取租户列表失败:', error)
  }
}

const handlePageChange = (value: number) => {
  const page = pageOptions.value.find((p: any) => p.value === value)
  if (page) {
    modalForm.page_name = page.label.split(' (')[0]
  }
}

const handleSearch = () => {
  pagination.current = 1
  fetchData()
}

const handleReset = () => {
  queryParams.group_name = ''
  queryParams.app_name = undefined
  queryParams.page_id = undefined
  queryParams.tenant_id = undefined
  pagination.current = 1
  fetchData()
}

const handleTenantChange = (tenantId: number) => {
  // 重置应用和页面选择
  queryParams.app_name = undefined
  queryParams.page_id = undefined
  // 重新加载该租户的应用和页面
  fetchAppOptions(tenantId)
  fetchPageOptions(tenantId)
  // 刷新数据
  handleSearch()
}

// 弹窗中租户变更处理
const handleModalTenantChange = (tenantId: number, form: any) => {
  // 重置页面选择
  form.page_id = undefined
  // 重新加载该租户的页面
  fetchPageOptions(tenantId)
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchData()
}

const handleAdd = () => {
  modalAction.value = 'add'
  modalTitle.value = '新建字段组'
  modalForm.id = undefined
  modalForm.group_name = ''
  modalForm.group_code = ''
  modalForm.page_id = undefined
  modalForm.page_name = ''
  modalForm.prompt_template_base = `你是一个智能填单助手。请根据以下对话内容，提取指定字段的信息。

需要提取的字段：
{{fields_instructions}}

对话内容：
{{query}}

请严格按照字段要求提取信息，并以JSON格式返回结果。`
  modalForm.output_templates = {}
  modalForm.description = ''
  modalForm.tenant_id = userStore.isSuperUser ? undefined : userStore.userInfo?.current_tenant_id
  modalForm.is_active = true
  crudTableRef.value?.openAddModal()
}

const handleEdit = (record: any) => {
  modalAction.value = 'edit'
  modalTitle.value = '编辑字段组'
  modalForm.id = record.id
  modalForm.group_name = record.group_name
  modalForm.group_code = record.group_code
  modalForm.page_id = record.page_id
  modalForm.page_name = record.page_name
  modalForm.prompt_template_base = record.prompt_template_base
  modalForm.output_templates = record.output_templates || {}
  modalForm.description = record.description
  modalForm.tenant_id = record.tenant_id
  modalForm.is_active = record.is_active
  crudTableRef.value?.openEditModal(record)
}

const handleManageFields = (record: any) => {
  currentFieldGroup.value = record
  fieldModalVisible.value = true
}

// 输出模板相关方法
const showAddTemplateModal = () => {
  newTemplateKey.value = ''
  newTemplateForm.template = ''
  newTemplateForm.description = ''
  addTemplateModalVisible.value = true
}

const confirmAddTemplate = () => {
  if (!newTemplateKey.value.trim()) {
    message.error('请输入模板名称')
    return
  }
  if (modalForm.output_templates[newTemplateKey.value]) {
    message.error('该模板名称已存在')
    return
  }
  modalForm.output_templates[newTemplateKey.value] = {
    template: newTemplateForm.template,
    description: newTemplateForm.description
  }
  addTemplateModalVisible.value = false
  message.success('添加成功')
}

const removeOutputTemplate = (key: string) => {
  delete modalForm.output_templates[key]
}

// 查看详情
const handleViewDetail = async (record: any) => {
  currentDetailId.value = record.id
  detailModalVisible.value = true
  detailLoading.value = true
  try {
    const res: any = await api.getFieldGroupDetail({ id: record.id })
    if (res.code === 200) {
      detailData.value = res.data
    } else {
      message.error(res.msg || '获取详情失败')
    }
  } catch (error: any) {
    message.error(error.message || '获取详情失败')
  } finally {
    detailLoading.value = false
  }
}

// 导出Markdown
const handleExportMd = async () => {
  if (!currentDetailId.value) return
  try {
    const res: any = await api.exportFieldGroupMd({ id: currentDetailId.value })
    if (res.code === 200 && res.data?.markdown) {
      // 创建下载
      const blob = new Blob([res.data.markdown], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = res.data.filename || `field_group_${currentDetailId.value}.md`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      message.success('导出成功')
    } else {
      message.error(res.msg || '导出失败')
    }
  } catch (error: any) {
    message.error(error.message || '导出失败')
  }
}

const handleSave = async () => {
  modalLoading.value = true
  try {
    const apiFunc = modalAction.value === 'add' ? api.createFieldGroup : api.updateFieldGroup
    const res: any = await apiFunc({ ...modalForm })
    if (res.code === 200) {
      message.success(modalAction.value === 'add' ? '创建成功' : '更新成功')
      crudTableRef.value?.closeModal()
      fetchData()
    } else {
      message.error(res.msg || '操作失败')
    }
  } catch (error: any) {
    message.error(error.message || '操作失败')
  } finally {
    modalLoading.value = false
  }
}

const handleDelete = async (record: any) => {
  try {
    const res: any = await api.deleteFieldGroup({ id: record.id })
    if (res.code === 200) {
      message.success('删除成功')
      fetchData()
    } else {
      message.error(res.msg || '删除失败')
    }
  } catch (error: any) {
    message.error(error.message || '删除失败')
  }
}

onMounted(() => {
  fetchData()
  fetchAppOptions()
  fetchPageOptions()
  fetchTenantOptions()
})
</script>

<style scoped lang="less">
.field-group-management {

  .ellipsis-text {
    display: inline-block;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .detail-loading {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 300px;
  }

  .detail-content {
    max-height: 70vh;
    overflow-y: auto;

    .detail-card {
      margin-bottom: 16px;

      &:last-child {
        margin-bottom: 0;
      }
    }

    .code-block {
      background: #f5f5f5;
      padding: 16px;
      border-radius: 4px;
      overflow-x: auto;
      font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
      font-size: 13px;
      line-height: 1.6;
      white-space: pre-wrap;
      word-wrap: break-word;

      &.json {
        color: #333;
      }
    }

    .detail-actions {
      display: flex;
      justify-content: flex-end;
      padding-top: 16px;
      border-top: 1px solid #e8e8e8;
    }
  }

  .output-templates-editor {
    .template-item {
      margin-bottom: 12px;

      .template-card {
        .mb-2 {
          margin-bottom: 8px;
        }

        .mb-0 {
          margin-bottom: 0;
        }
      }
    }
  }
}
</style>
