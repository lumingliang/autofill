<template>
  <div class="field-spec-management">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
      :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
      modal-width="800px" @search="handleSearch" @reset="handleReset" @table-change="handleTableChange"
      @modal-ok="handleSave">
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
        <a-button v-permission="'post/api/v1/autofill/field_spec/create'" type="primary" @click="handleAdd">
          <PlusOutlined />
          新建字段
        </a-button>
      </template>

      <!-- 表格列自定义 -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'field_type'">
          <a-tag :color="record.field_type === 'select' ? 'blue' : 'green'">
            {{ record.field_type === 'select' ? '下拉选择' : '文本输入' }}
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
        <a-form-item label="所属字段组" name="field_group_id">
          <a-select v-model:value="form.field_group_id" placeholder="请选择字段组" :disabled="!!props.fieldGroupId"
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
            <a-radio value="select">下拉选择</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="填写指引" name="fill_instruction">
          <a-textarea v-model:value="form.fill_instruction" placeholder="请输入字段填写指引，用于生成LLM描述" :rows="3" />
        </a-form-item>

        <!-- Select类型选项配置 -->
        <template v-if="form.field_type === 'select'">
          <a-divider orientation="left">选项配置</a-divider>
          <a-form-item label="选项来源" name="options.source">
            <a-radio-group v-model:value="form.options.source">
              <a-radio value="static">静态选项</a-radio>
              <a-radio value="api">API接口</a-radio>
            </a-radio-group>
          </a-form-item>
          <a-form-item v-if="form.options.source === 'api'" label="API标识" name="options.api_identifier">
            <a-input v-model:value="form.options.api_identifier" placeholder="请输入API标识" />
          </a-form-item>
          <template v-if="form.options.source === 'static'">
            <a-form-item label="选项列表">
              <div v-for="(item, index) in form.options.items" :key="index" class="option-item">
                <a-space>
                  <a-input v-model:value="item.value" placeholder="选项值" style="width: 150px" />
                  <a-input v-model:value="item.label" placeholder="选项标签" style="width: 150px" />
                  <a-input v-model:value="item.base_annotation" placeholder="基础说明" style="width: 200px" />
                  <a-button type="link" danger @click="removeOption(index)">
                    <DeleteOutlined />
                  </a-button>
                </a-space>
              </div>
              <a-button type="dashed" block @click="addOption">
                <PlusOutlined />
                添加选项
              </a-button>
            </a-form-item>
          </template>
        </template>

        <!-- Text类型批注配置 -->
        <template v-if="form.field_type === 'text'">
          <a-divider orientation="left">全局批注</a-divider>
          <a-form-item label="批注列表">
            <div v-for="(item, index) in form.corrections" :key="index" class="correction-item">
              <a-space>
                <a-input v-model:value="item.text" placeholder="批注内容" style="width: 400px" />
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
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, onMounted, reactive, ref, watch } from 'vue'

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

// 弹窗数据
const modalTitle = ref('')
const modalLoading = ref(false)
const modalAction = ref<'add' | 'edit'>('add')
const modalForm = reactive({
  id: undefined as number | undefined,
  field_group_id: props.fieldGroupId,
  field_name: '',
  field_label: '',
  field_type: 'text',
  fill_instruction: '',
  options: {
    source: 'static',
    api_identifier: '',
    items: [] as any[],
  },
  corrections: [] as any[],
  is_active: true,
})

// 选项数据
const fieldTypeOptions = [
  { label: '文本输入', value: 'text' },
  { label: '下拉选择', value: 'select' },
]
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

const filterItemCount = computed(() => 4)

const modalRules = {
  field_group_id: [
    { required: true, message: '请选择所属字段组', trigger: 'change' },
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
    const params: any = {
      page: pagination.current,
      page_size: pagination.pageSize,
      ...queryParams,
    }
    if (props.fieldGroupId) {
      params.field_group_id = props.fieldGroupId
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
  modalForm.field_group_id = props.fieldGroupId || queryParams.field_group_id
  modalForm.field_name = ''
  modalForm.field_label = ''
  modalForm.field_type = 'text'
  modalForm.fill_instruction = ''
  modalForm.options = {
    source: 'static',
    api_identifier: '',
    items: [],
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
  modalForm.field_group_id = record.field_group_id
  modalForm.field_name = record.field_name
  modalForm.field_label = record.field_label
  modalForm.field_type = record.field_type
  modalForm.fill_instruction = record.fill_instruction || ''
  modalForm.options = {
    source: record.options?.source || 'static',
    api_identifier: record.options?.api_identifier || '',
    items: record.options?.items || [],
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
    base_annotation: '',
    corrections: [],
    is_deleted: false,
  })
}

const removeOption = (index: number) => {
  modalForm.options.items.splice(index, 1)
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
    // 清理空选项
    if (modalForm.field_type === 'select') {
      modalForm.options.items = modalForm.options.items.filter((item: any) => item.value && item.label)
    }
    // 清理空批注
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

watch(() => props.fieldGroupId, (newVal) => {
  queryParams.field_group_id = newVal
  modalForm.field_group_id = newVal
  fetchData()
})

onMounted(() => {
  fetchFieldGroups()
  fetchData()
})
</script>

<style scoped lang="less">
.field-spec-management {
  padding: 16px;

  .option-item,
  .correction-item {
    margin-bottom: 8px;
  }
}
</style>
