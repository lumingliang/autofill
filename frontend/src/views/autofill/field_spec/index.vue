<template>
  <div class="field-spec-management">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
      :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
      modal-width="800px" :row-selection="rowSelection" @search="handleSearch" @reset="handleReset"
      @table-change="handleTableChange" @modal-ok="handleSave">
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="字段组" class="filter-item">
            <a-select v-model:value="queryParams.field_group_id" placeholder="请选择字段组" allow-clear
              :options="fieldGroupOptions" :disabled="!!props.fieldGroupId" @change="handleSearch" />
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
          <a-button @click="handleExport">
            <ExportOutlined />
            导出选中
          </a-button>
          <a-upload :custom-request="handleImport" :show-upload-list="false" accept=".csv">
            <a-button>
              <ImportOutlined />
              导入
            </a-button>
          </a-upload>
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
        <template v-if="column.key === 'field_groups'">
          <a-space v-if="record.field_groups && record.field_groups.length > 0" wrap>
            <a-tag v-for="group in record.field_groups" :key="group.id" color="blue">
              {{ group.group_name }}
            </a-tag>
          </a-space>
          <span v-else>-</span>
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
        <a-form-item label="关联字段组" name="field_group_ids">
          <a-select v-model:value="form.field_group_ids" placeholder="请选择关联字段组（可多选）" mode="multiple"
            :options="fieldGroupOptions" />
        </a-form-item>
        <a-form-item label="字段名" name="field_name">
          <a-input v-model:value="form.field_name" placeholder="请输入字段名（英文、数字、下划线）" :disabled="modalAction === 'edit'" />
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
            <div v-for="(item, index) in form.options.items" :key="index" class="option-item">
              <a-space direction="vertical" style="width: 100%">
                <a-space>
                  <a-input v-model:value="item.value" placeholder="选项值" style="width: 120px" />
                  <a-input v-model:value="item.label" placeholder="选项标签" style="width: 120px" />
                  <a-input v-model:value="item.fill_instruction" placeholder="填写说明" style="width: 150px" />
                  <a-button type="link" danger @click="removeOption(index)">
                    <DeleteOutlined />
                  </a-button>
                </a-space>
                <!-- 选项的人工标注数组 -->
                <div class="option-corrections">
                  <div class="correction-label">人工标注：</div>
                  <div v-for="(corr, corrIndex) in item.corrections" :key="corrIndex" class="correction-item">
                    <a-space>
                      <a-textarea v-model:value="corr.text" placeholder="批注内容" :rows="2" style="width: 400px" />
                      <a-button type="link" danger @click="removeOptionCorrection(index, corrIndex)">
                        <DeleteOutlined />
                      </a-button>
                    </a-space>
                  </div>
                  <a-button type="dashed" block @click="addOptionCorrection(index)" style="margin-top: 8px">
                    <PlusOutlined />
                    添加批注
                  </a-button>
                </div>
              </a-space>
            </div>
            <a-button type="dashed" block @click="addOption">
              <PlusOutlined />
              添加选项
            </a-button>
          </a-form-item>
        </template>

        <!-- Text类型批注配置 -->
        <template v-if="form.field_type === 'text'">
          <a-divider orientation="left">全局批注</a-divider>
          <a-form-item label="批注列表">
            <div v-for="(item, index) in form.corrections" :key="index" class="correction-item">
              <a-space>
                <a-textarea v-model:value="item.text" placeholder="批注内容" :rows="2" style="width: 400px" />
                <a-button type="link" danger @click="removeCorrection(index)">
                  <DeleteOutlined />
                </a-button>
              </a-space>
            </div>
            <a-button type="dashed" block @click="addCorrection">
              <PlusOutlined />
              添加批注
            </a-button>
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
import { useUserStore } from '@/store'
import { formatDateTime } from '@/utils'
import { DeleteOutlined, ExportOutlined, ImportOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'

interface Props {
  fieldGroupId?: number
  fieldGroupName?: string
}

const props = withDefaults(defineProps<Props>(), {
  fieldGroupId: undefined,
  fieldGroupName: '',
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
  field_group_id: props.fieldGroupId,
})

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
  field_group_ids: [] as number[],
  field_name: '',
  field_label: '',
  field_type: 'text',
  fill_instruction: '',
  options: {
    items: [] as any[],
    min_selections: 1,
    max_selections: 0,  // 0表示无限制
  },
  corrections: [] as any[],
  is_active: true,
})

// 选项数据 - 新的字段类型：文本输入、下拉单选、下拉多选
const fieldTypeOptions = [
  { label: '文本输入', value: 'text' },
  { label: '下拉单选', value: 'select_single' },
  { label: '下拉多选', value: 'select_multi' },
]

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
const fieldGroupOptions = ref<{ label: string; value: number }[]>([])

// 计算属性
const columns = computed(() => [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '字段名', dataIndex: 'field_name', key: 'field_name' },
  { title: '字段标签', dataIndex: 'field_label', key: 'field_label' },
  { title: '字段类型', key: 'field_type', width: 120 },
  { title: '关联字段组', key: 'field_groups', width: 200 },
  { title: '状态', key: 'is_active', width: 100 },
  { title: '创建时间', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 150, fixed: 'right' },
])

const filterItemCount = computed(() => 4)

const modalRules = {
  field_group_ids: [
    { required: true, message: '请至少选择一个关联字段组', trigger: 'change', type: 'array' },
  ],
  field_name: [
    { required: true, message: '请输入字段名', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '字段名只能包含英文、数字、下划线', trigger: 'blur' },
  ],
  field_label: [
    { required: true, message: '请输入字段标签', trigger: 'blur' },
  ],
  field_type: [
    { required: true, message: '请选择字段类型', trigger: 'change' },
  ],
}

// 方法
// 加载数据
const fetchData = async () => {
  loading.value = true
  try {
    // 优先使用props中的fieldGroupId
    const fieldGroupId = props.fieldGroupId || queryParams.field_group_id
    const params: any = {
      page: pagination.current,
      page_size: pagination.pageSize,
      field_name: queryParams.field_name,
      field_label: queryParams.field_label,
      field_type: queryParams.field_type,
    }
    if (fieldGroupId) {
      params.field_group_id = fieldGroupId
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
  if (!props.fieldGroupId) {
    queryParams.field_group_id = undefined
  }
  pagination.current = 1
  fetchData()
}

// 加载字段组列表
const fetchFieldGroups = async () => {
  try {
    const res: any = await api.getFieldGroupList({ page_size: 1000 })
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

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchData()
}

const resetModalForm = () => {
  modalForm.id = undefined
  modalForm.field_group_ids = props.fieldGroupId ? [props.fieldGroupId] : []
  modalForm.field_name = ''
  modalForm.field_label = ''
  modalForm.field_type = 'text'
  modalForm.fill_instruction = ''
  modalForm.options = {
    items: [],
    min_selections: 1,
    max_selections: 0,  // 0表示无限制
  }
  modalForm.corrections = []
  modalForm.is_active = true
}

const handleAdd = () => {
  modalAction.value = 'add'
  modalTitle.value = '新建字段'
  resetModalForm()
  crudTableRef.value?.openAddModal()
}

const handleEdit = (record: any) => {
  modalAction.value = 'edit'
  modalTitle.value = '编辑字段'
  modalForm.id = record.id
  modalForm.field_group_ids = record.field_group_ids || []
  modalForm.field_name = record.field_name
  modalForm.field_label = record.field_label
  modalForm.field_type = record.field_type
  modalForm.fill_instruction = record.fill_instruction || ''
  modalForm.options = {
    items: record.options?.items || [],
    min_selections: record.options?.min_selections ?? 1,
    max_selections: record.options?.max_selections ?? 0,  // 0表示无限制
  }
  modalForm.is_active = record.is_active
  crudTableRef.value?.openEditModal(record)
  // 确保 corrections 是数组，避免 null 导致的问题（必须在 openEditModal 之后执行，因为 openEditModal 内部会 Object.assign 覆盖值）
  // 由于 Object.assign 会将 null 直接赋值给 corrections，我们需要重新赋值为数组
  const corrections = Array.isArray(record.corrections) ? record.corrections : []
    ; (modalForm as any).corrections = [...corrections]
}

const addOption = () => {
  modalForm.options.items.push({
    value: '',
    label: '',
    fill_instruction: '',
    corrections: [],
    is_deleted: false,
  })
}

const removeOption = (index: number) => {
  modalForm.options.items.splice(index, 1)
}

const addOptionCorrection = (optionIndex: number) => {
  const item = modalForm.options.items[optionIndex]
  if (!item.corrections) {
    item.corrections = []
  }
  item.corrections.push({
    text: '',
  })
}

const removeOptionCorrection = (optionIndex: number, correctionIndex: number) => {
  const item = modalForm.options.items[optionIndex]
  if (item.corrections) {
    item.corrections.splice(correctionIndex, 1)
  }
}

const addCorrection = () => {
  modalForm.corrections.push({
    id: Date.now().toString(),
    text: '',
    created_by: userStore.userInfo?.username || 'system',
    created_at: new Date().toISOString(),
  })
}

const removeCorrection = (index: number) => {
  modalForm.corrections.splice(index, 1)
}



const handleSave = async () => {
  modalLoading.value = true
  try {
    // 清理空选项（下拉单选/多选类型）
    if (modalForm.field_type === 'select_single' || modalForm.field_type === 'select_multi') {
      modalForm.options.items = modalForm.options.items.filter((item: any) => item.value && item.label)
    }
    // 清理空批注（文本输入类型）
    if (modalForm.field_type === 'text') {
      modalForm.corrections = modalForm.corrections.filter((item: any) => item.text)
    }

    const apiFunc = modalAction.value === 'add' ? api.createFieldSpec : api.updateFieldSpec
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

// 导出选中字段
const handleExport = async () => {
  if (selectedRowKeys.value.length === 0) {
    message.warning('请先选择要导出的字段')
    return
  }

  try {
    const res: any = await api.exportFieldSpecs({
      ids: selectedRowKeys.value
    })

    if (res.code === 200) {
      // 下载基础字段CSV
      const baseBlob = new Blob([res.data.base_csv], { type: 'text/csv;charset=utf-8;' })
      const baseLink = document.createElement('a')
      baseLink.href = URL.createObjectURL(baseBlob)
      baseLink.download = `field_specs_base_${new Date().getTime()}.csv`
      baseLink.click()

      // 下载选项详情CSV
      const optionsBlob = new Blob([res.data.options_csv], { type: 'text/csv;charset=utf-8;' })
      const optionsLink = document.createElement('a')
      optionsLink.href = URL.createObjectURL(optionsBlob)
      optionsLink.download = `field_specs_options_${new Date().getTime()}.csv`
      optionsLink.click()

      message.success('导出成功')
    } else {
      message.error(res.msg || '导出失败')
    }
  } catch (error: any) {
    message.error(error.message || '导出失败')
  }
}

// 导入字段
const handleImport = async (info: any) => {
  const file = info.file
  if (!file) return

  try {
    const res: any = await api.importFieldSpecs({
      file: file
    })

    if (res.code === 200) {
      message.success(`导入成功：${res.data.success_count} 个字段`)
      fetchData()
    } else {
      message.error(res.msg || '导入失败')
    }
  } catch (error: any) {
    message.error(error.message || '导入失败')
  }
}

watch(() => props.fieldGroupId, (newVal) => {
  queryParams.field_group_id = newVal
  modalForm.field_group_ids = newVal ? [newVal] : []
  // 使用 nextTick 确保查询参数更新后再获取数据
  nextTick(() => {
    fetchData()
  })
}, { immediate: true })

onMounted(() => {
  fetchFieldGroups()
  fetchData()
})
</script>

<style scoped lang="less">
.field-spec-management {

  .option-item,
  .correction-item {
    margin-bottom: 8px;
  }

  .selection-limit-item {
    .limit-input-wrapper {
      display: flex;
      flex-direction: column;

      .limit-label {
        font-size: 14px;
        color: rgba(0, 0, 0, 0.85);
        margin-bottom: 8px;
        line-height: 1.5715;
      }
    }
  }
}
</style>
