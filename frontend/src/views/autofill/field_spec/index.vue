<template>
  <div class="field-spec-management">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
      :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
      modal-width="700px" :row-selection="rowSelection" @search="handleSearch" @reset="handleReset"
      @table-change="handleTableChange" @modal-ok="handleSave">
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col v-if="userStore.isSuperUser" :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="租户" class="filter-item">
            <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户" allow-clear :options="tenantOptions"
              @change="handleTenantChange" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="应用名称" class="filter-item">
            <a-select v-model:value="queryParams.app_name" placeholder="请选择应用" allow-clear :options="appOptions"
              @change="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="字段名" class="filter-item">
            <a-input v-model:value="queryParams.field_name" placeholder="请输入字段名" allow-clear
              @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="字段标签" class="filter-item">
            <a-input v-model:value="queryParams.field_label" placeholder="请输入字段标签" allow-clear
              @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="字段类型" class="filter-item">
            <a-select v-model:value="queryParams.field_type" placeholder="请选择字段类型" allow-clear
              :options="fieldTypeOptions" @change="handleSearch" />
          </a-form-item>
        </a-col>
      </template>

      <!-- 操作按钮 -->
      <template #actions>
        <a-space>
          <a-button v-permission="'post/api/v1/autofill/field_spec/create'" type="primary" @click="handleAdd">
            <PlusOutlined />
            新建字段
          </a-button>
          <a-popconfirm title="确定批量删除选中的字段吗？" description="此操作不可恢复，请谨慎操作！" ok-text="确定" cancel-text="取消"
            ok-type="danger" @confirm="handleBatchDelete">
            <a-button v-permission="'delete/api/v1/autofill/field_spec/batch_delete'" danger
              :disabled="selectedRowKeys.length === 0">
              <DeleteOutlined />
              批量删除
            </a-button>
          </a-popconfirm>
          <a-typography-text v-if="selectedRowKeys.length > 0" type="secondary">
            已选择 {{ selectedRowKeys.length }} 项
          </a-typography-text>
        </a-space>
      </template>

      <!-- 表格列自定义 -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'field_type'">
          <a-tag :color="getFieldTypeColor(record.field_type)">
            {{ getFieldTypeLabel(record.field_type) }}
          </a-tag>
        </template>
        <template v-if="column.key === 'is_active'">
          <a-tag :color="record.is_active ? 'green' : 'red'">
            {{ record.is_active ? '启用' : '禁用' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'created_at'">
          <span v-if="record.created_at">{{ formatDateTime(record.created_at) }}</span>
          <span v-else>-</span>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button v-permission="'post/api/v1/autofill/field_spec/update'" type="link" size="small"
              @click="handleEdit(record)">编辑</a-button>
            <a-popconfirm title="确定删除该字段吗？" @confirm="handleDelete(record)">
              <a-button v-permission="'delete/api/v1/autofill/field_spec/delete'" type="link" danger
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
        <a-form-item label="应用名称" name="app_name" required>
          <a-select v-model:value="form.app_name" placeholder="请选择应用" :options="appOptions" />
        </a-form-item>
        <a-form-item label="关联字段组" name="field_group_id">
          <a-select v-model:value="form.field_group_id" placeholder="请选择关联字段组（可选）" allow-clear
            :options="fieldGroupOptions" />
          <a-typography-text type="secondary">
            选择字段组后，该字段将自动关联到指定字段组（可选）
          </a-typography-text>
        </a-form-item>
        <a-form-item label="字段名" name="field_name">
          <a-input v-model:value="form.field_name" placeholder="请输入字段名（最多50个字符）" :disabled="modalAction === 'edit'" />
        </a-form-item>
        <a-form-item label="字段标签" name="field_label">
          <a-input v-model:value="form.field_label" placeholder="请输入字段显示名称" />
        </a-form-item>
        <a-form-item label="字段类型" name="field_type">
          <a-radio-group v-model:value="form.field_type" :disabled="modalAction === 'edit'">
            <a-radio value="text">文本输入</a-radio>
            <a-radio value="select_single">下拉单选</a-radio>
            <a-radio value="select_multi">下拉多选</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="填写指引" name="fill_instruction">
          <a-textarea v-model:value="form.fill_instruction" placeholder="请输入字段填写指引，用于生成LLM描述" :rows="3" />
        </a-form-item>

        <!-- 下拉单选/多选类型选项配置 -->
        <template v-if="form.field_type === 'select_single' || form.field_type === 'select_multi'">
          <a-divider orientation="left">选项配置</a-divider>

          <!-- 多选时显示选项数限制 -->
          <template v-if="form.field_type === 'select_multi'">
            <a-form-item label="选项数限制" class="selection-limit-item">
              <a-row :gutter="16">
                <a-col :span="12">
                  <div class="limit-input-wrapper">
                    <span class="limit-label">最少选择</span>
                    <a-input-number v-model:value="form.options.min_selections" :min="1"
                      :max="form.options.max_selections || 100" style="width: 100%" />
                  </div>
                </a-col>
                <a-col :span="12">
                  <div class="limit-input-wrapper">
                    <span class="limit-label">最多选择</span>
                    <a-input-number v-model:value="form.options.max_selections" :min="form.options.min_selections || 1"
                      :max="100" style="width: 100%" />
                  </div>
                </a-col>
              </a-row>
            </a-form-item>
          </template>

          <a-form-item label="选项列表">
            <OptionsMarkdownEditor v-model="optionsMarkdown" :height="400"
              placeholder="## 道路救援&#10;- 选项值: EVT001&#10;- 填写说明: 道路救援服务说明&#10;  - 服务范围：高速公路、城市道路&#10;    - 高速公路：24小时救援&#10;    - 城市道路：工作日服务&#10;  - 响应时间：30分钟内&#10;&#10;## 智能网联&#10;- 选项值: EVT002&#10;- 填写说明: 智能网联相关问题&#10;  - 系统故障诊断&#10;    - 软件问题&#10;    - 硬件问题"
              @change="handleOptionsChange" />
          </a-form-item>
        </template>

        <a-form-item label="状态" name="is_active">
          <a-switch v-model:checked="form.is_active" />
        </a-form-item>
      </template>
    </CrudTable>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import OptionsMarkdownEditor from '@/components/OptionsMarkdownEditor/index.vue'
import { useUserStore } from '@/store'
import { formatDateTime } from '@/utils'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, onMounted, reactive, ref } from 'vue'

interface Props {
  fieldGroupId?: number
  fieldGroupName?: string
}

const props = withDefaults(defineProps<Props>(), {
  fieldGroupId: undefined,
  fieldGroupName: ''
})

const emit = defineEmits<{
  close: []
}>()

defineOptions({ name: 'FieldSpecManagement' })

const userStore = useUserStore()
const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  field_name: '',
  field_label: '',
  field_type: undefined as string | undefined,
  app_name: undefined as string | undefined,
  tenant_id: undefined as number | undefined,
})

// 租户选项
const tenantOptions = ref<{ label: string; value: number }[]>([])

// 应用选项
const appOptions = ref<{ label: string; value: string }[]>([])

// 表格数据
const loading = ref(false)
const tableData = ref<any[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
})

// 多选相关
const selectedRowKeys = ref<number[]>([])
const selectedRows = ref<any[]>([])

// 行选择配置
const rowSelection = computed(() => ({
  type: 'checkbox' as const,
  selectedRowKeys: selectedRowKeys.value,
  onChange: (keys: number[], rows: any[]) => {
    selectedRowKeys.value = keys
    selectedRows.value = rows
  },
  preserveSelectedRowKeys: true,
}))

// 弹窗数据
const modalTitle = ref('')
const modalLoading = ref(false)
const modalAction = ref<'add' | 'edit'>('add')

const modalForm = reactive({
  id: undefined as number | undefined,
  tenant_id: undefined as number | undefined,
  app_name: undefined as string | undefined,
  field_group_id: undefined as number | undefined,
  field_name: '',
  field_label: '',
  field_type: 'text',
  fill_instruction: '',
  options: {
    items: [] as any[],
    min_selections: 1,
    max_selections: 0,
  },
  is_active: true,
})

// Markdown 格式的选项列表
const optionsMarkdown = ref('')

// 字段组选项
const fieldGroupOptions = ref<{ label: string; value: number }[]>([])

// 计算属性
const columns = computed(() => [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '字段名', dataIndex: 'field_name', key: 'field_name' },
  { title: '字段标签', dataIndex: 'field_label', key: 'field_label' },
  { title: '字段类型', key: 'field_type', width: 120 },
  { title: '状态', key: 'is_active', width: 100 },
  { title: '创建时间', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 150, fixed: 'right' },
])

const fieldTypeOptions = [
  { label: '文本输入', value: 'text' },
  { label: '下拉单选', value: 'select_single' },
  { label: '下拉多选', value: 'select_multi' },
]

const filterItemCount = computed(() => userStore.isSuperUser ? 5 : 4)

const modalRules = computed(() => {
  const rules: any = {
    app_name: [
      { required: true, message: '请选择应用名称', trigger: 'change' },
    ],
    field_name: [
      { required: true, message: '请输入字段名', trigger: 'blur' },
      { max: 50, message: '字段名最多50个字符', trigger: 'blur' },
    ],
    field_label: [
      { required: true, message: '请输入字段标签', trigger: 'blur' },
    ],
    field_type: [
      { required: true, message: '请选择字段类型', trigger: 'change' },
    ],
  }
  if (userStore.isSuperUser) {
    rules.tenant_id = [
      { required: true, message: '请选择所属租户', trigger: 'change', type: 'number' },
    ]
  }
  return rules
})

// 方法
const fetchData = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.current,
      page_size: pagination.pageSize,
      field_name: queryParams.field_name,
      field_label: queryParams.field_label,
      field_type: queryParams.field_type,
    }
    if (queryParams.app_name) {
      params.app_name = queryParams.app_name
    }
    if (userStore.isSuperUser && queryParams.tenant_id) {
      params.tenant_id = queryParams.tenant_id
    }
    const res: any = await api.getFieldSpecList(params)
    if (res.code === 200) {
      tableData.value = res.data || []
      pagination.total = res.total || 0
    }
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.current = 1
  fetchData()
}

const handleReset = () => {
  queryParams.field_name = ''
  queryParams.field_label = ''
  queryParams.field_type = undefined
  queryParams.app_name = undefined
  if (userStore.isSuperUser) {
    queryParams.tenant_id = undefined
  }
  pagination.current = 1
  fetchData()
}

// 加载字段组列表
const fetchFieldGroups = async (tenantId?: number) => {
  try {
    const params: any = { page_size: 1000 }
    if (tenantId && tenantId > 0) {
      params.tenant_id = tenantId
    }
    const res: any = await api.getFieldGroupList(params)
    if (res.code === 200) {
      fieldGroupOptions.value = (res.data || []).map((item: any) => ({
        label: `${item.group_name} (${item.group_code})`,
        value: item.id,
      }))
    }
  } catch (error) {
    console.error('加载字段组列表失败', error)
  }
}

// 获取字段类型标签
const getFieldTypeLabel = (type: string) => {
  const option = fieldTypeOptions.find(opt => opt.value === type)
  return option?.label || type
}

// 获取字段类型颜色
const getFieldTypeColor = (type: string) => {
  switch (type) {
    case 'text': return 'green'
    case 'select_single': return 'blue'
    case 'select_multi': return 'orange'
    default: return 'default'
  }
}

// 处理新增
const handleAdd = () => {
  modalAction.value = 'add'
  modalTitle.value = '新建字段'

  // 重置表单
  modalForm.id = undefined
  modalForm.tenant_id = userStore.isSuperUser ? undefined : userStore.userInfo?.tenant_id
  modalForm.app_name = props.fieldGroupName || undefined
  modalForm.field_group_id = props.fieldGroupId
  modalForm.field_name = ''
  modalForm.field_label = ''
  modalForm.field_type = 'text'
  modalForm.fill_instruction = ''
  modalForm.options = {
    items: [],
    min_selections: 1,
    max_selections: 0,
  }
  modalForm.is_active = true

  optionsMarkdown.value = ''

  crudTableRef.value?.openAddModal()
}

// 处理编辑
const handleEdit = async (record: any) => {
  modalAction.value = 'edit'
  modalTitle.value = '编辑字段'

  modalForm.id = record.id
  modalForm.tenant_id = record.tenant_id
  modalForm.app_name = record.app_name
  modalForm.field_group_id = record.field_group_id
  modalForm.field_name = record.field_name
  modalForm.field_label = record.field_label
  modalForm.field_type = record.field_type
  modalForm.fill_instruction = record.fill_instruction || ''
  modalForm.options = {
    items: record.options?.items || [],
    min_selections: record.options?.min_selections || 1,
    max_selections: record.options?.max_selections || 0,
  }
  modalForm.is_active = record.is_active

  optionsMarkdown.value = convertOptionsToMarkdown(modalForm.options.items)

  crudTableRef.value?.openEditModal(record)
}

// 处理保存
const handleSave = async () => {
  modalLoading.value = true
  try {
    const data = {
      ...modalForm,
      options: {
        ...modalForm.options,
        items: modalForm.options.items,
      },
    }

    let res: any
    if (modalAction.value === 'add') {
      res = await api.createFieldSpec(data)
    } else {
      res = await api.updateFieldSpec(data)
    }

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

// 处理删除
const handleDelete = async (record: any) => {
  try {
    const res: any = await api.deleteFieldSpec({ id: record.id })
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

// 批量删除
const handleBatchDelete = async () => {
  if (selectedRowKeys.value.length === 0) {
    message.warning('请选择要删除的字段')
    return
  }
  try {
    const res: any = await api.batchDeleteFieldSpecs({ ids: selectedRowKeys.value })
    if (res.code === 200) {
      message.success(`成功删除 ${res.data?.deleted_count || 0} 个字段`)
      selectedRowKeys.value = []
      fetchData()
    } else {
      message.error(res.msg || '删除失败')
    }
  } catch (error: any) {
    message.error(error.message || '删除失败')
  }
}

// 其他方法
const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchData()
}

const handleTenantChange = () => {
  handleSearch()
}

const handleModalTenantChange = (val: number, form: any) => {
  form.tenant_id = val
  fetchFieldGroups(val)
}

// Markdown 转换方法（支持多行填写说明层级缩进）
const convertOptionsToMarkdown = (items: any[]): string => {
  if (!items || items.length === 0) return ''

  return items.map((item, index) => {
    const lines: string[] = []
    lines.push(`## ${item.label || ''}`)

    if (item.value) {
      lines.push(`- 选项值: ${item.value}`)
    }

    if (item.fill_instruction) {
      const instructionLines = item.fill_instruction.split('\n')
      // 第一行作为填写说明标题
      lines.push(`- 填写说明: ${instructionLines[0]}`)

      // 后续行添加2空格缩进，作为填写说明的延续
      for (let i = 1; i < instructionLines.length; i++) {
        const line = instructionLines[i].trim()
        if (line) {
          // 添加2空格缩进，表示这是填写说明的延续行
          lines.push(`  ${line}`)
        }
      }
    }

    if (index < items.length - 1) {
      lines.push('')
    }
    return lines.join('\n')
  }).join('\n')
}

// 处理选项编辑器变化
const handleOptionsChange = (markdown: string, items: any[]) => {
  optionsMarkdown.value = markdown
  modalForm.options.items = items
}

const parseMarkdownToOptions = () => {
  const markdown = optionsMarkdown.value.trim()
  if (!markdown) {
    modalForm.options.items = []
    return
  }

  const items: any[] = []
  const lines = markdown.split('\n')
  let currentItem: any = null
  let isCollectingInstruction = false
  let instructionIndentLevel = 0

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmedLine = line.trim()

    if (!trimmedLine) continue

    const headerMatch = trimmedLine.match(/^##\s*(.+)$/)
    if (headerMatch) {
      if (currentItem) {
        items.push(currentItem)
      }
      currentItem = {
        label: headerMatch[1].trim(),
        value: '',
        fill_instruction: '',
        is_deleted: false,
      }
      isCollectingInstruction = false
      instructionIndentLevel = 0
      continue
    }

    if (!currentItem) continue

    const valueMatch = trimmedLine.match(/^-\s*选项值[:：]\s*(.*)$/i)
    if (valueMatch) {
      currentItem.value = valueMatch[1].trim()
      isCollectingInstruction = false
      instructionIndentLevel = 0
      continue
    }

    const instructionMatch = trimmedLine.match(/^-\s*填写说明[:：]\s*(.*)$/i)
    if (instructionMatch) {
      currentItem.fill_instruction = instructionMatch[1].trim()
      isCollectingInstruction = true
      const leadingSpaces = line.match(/^(\s*)/)?.[1] || ''
      instructionIndentLevel = Math.floor(leadingSpaces.length / 2) + 1
      continue
    }

    // 多行填写说明（以2个或更多空格开头表示延续）
    if (isCollectingInstruction) {
      const leadingSpaces = line.match(/^(\s*)/)?.[1] || ''

      // 如果以2个或更多空格开头，表示这是填写说明的延续行
      if (leadingSpaces.length >= 2) {
        // 只取内容部分，不保留缩进（因为存储时只需要纯文本）
        currentItem.fill_instruction += '\n' + trimmedLine
      } else {
        // 缩进不足，结束填写说明收集
        isCollectingInstruction = false
        instructionIndentLevel = 0
      }
    }
  }

  if (currentItem) {
    items.push(currentItem)
  }

  modalForm.options.items = items
}

// 初始化
onMounted(async () => {
  await fetchData()
  await fetchFieldGroups()

  // 加载租户和应用选项
  try {
    const tenantRes: any = await api.getTenantSelect()
    if (tenantRes.code === 200) {
      tenantOptions.value = (tenantRes.data || []).map((item: any) => ({
        label: item.name,
        value: item.id,
      }))
    }

    const appRes: any = await api.getAppSelect({ page_size: 1000 })
    if (appRes.code === 200) {
      appOptions.value = (appRes.data || []).map((item: any) => ({
        label: item.label || item.app_name,
        value: item.value || item.app_name,
      }))
    }
  } catch (error) {
    console.error('加载选项失败', error)
  }
})
</script>

<style scoped>
.field-spec-management {
  padding: 20px;
}

.filter-item-col {
  margin-bottom: 16px;
}

.limit-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.limit-label {
  white-space: nowrap;
  font-size: 14px;
  color: rgba(0, 0, 0, 0.65);
}
</style>
