<template>
  <div class="llm-config-page crud-page">
    <a-card>
      <FilterForm
        v-model:form="searchForm"
        :items="filterItems"
        @search="handleSearch"
        @reset="handleReset"
      />

      <div class="table-actions">
        <a-button v-permission="'post/api/v1/ai/llm_config/create'" type="primary" @click="handleClickAdd">
          <PlusOutlined />
          新增配置
        </a-button>
      </div>

      <CrudTable
        :columns="columns"
        :data-source="tableData"
        :loading="loading"
        :pagination="pagination"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'model_provider'">
            <a-tag :color="getProviderColor(record.model_provider)">
              {{ getProviderLabel(record.model_provider) }}
            </a-tag>
          </template>
          <template v-if="column.key === 'is_active'">
            <a-switch
              :checked="record.is_active"
              size="small"
              :loading="!!record.publishingActive"
              @change="() => handleUpdateActive(record)"
            />
          </template>
          <template v-if="column.key === 'is_default'">
            <a-tag v-if="record.is_default" color="blue">默认</a-tag>
            <span v-else>-</span>
          </template>
          <template v-if="column.key === 'temperature'">
            <a-tag color="orange">{{ record.temperature }}</a-tag>
          </template>
          <template v-if="column.key === 'max_tokens'">
            {{ record.max_tokens }}
          </template>
          <template v-if="column.key === 'created_at'">
            {{ formatDateTime(record.created_at) }}
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button
                v-permission="'post/api/v1/ai/llm_config/update'"
                type="link"
                size="small"
                @click="handleEdit(record)"
              >
                编辑
              </a-button>
              <a-popconfirm title="确定删除该配置吗？" @confirm="handleDelete(record)">
                <a-button
                  v-permission="'delete/api/v1/ai/llm_config/delete'"
                  type="link"
                  danger
                  size="small"
                >
                  删除
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </CrudTable>
    </a-card>

    <!-- 新增/编辑 弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="modalTitle"
      :confirm-loading="modalLoading"
      width="700px"
      @ok="handleSave"
      @cancel="modalVisible = false"
    >
      <a-form
        ref="modalFormRef"
        :model="modalForm"
        :rules="modalRules"
        :label-col="{ span: 6 }"
        :wrapper-col="{ span: 16 }"
      >
        <a-form-item label="配置名称" name="name">
          <a-input v-model:value="modalForm.name" placeholder="请输入配置名称" />
        </a-form-item>

        <a-form-item label="模型提供商" name="model_provider">
          <a-select
            v-model:value="modalForm.model_provider"
            placeholder="请选择模型提供商"
            :options="providerOptions"
          />
        </a-form-item>

        <a-form-item label="模型名称" name="model_name">
          <a-input v-model:value="modalForm.model_name" placeholder="例如：gpt-4, gpt-3.5-turbo" />
        </a-form-item>

        <a-form-item label="API密钥" name="api_key">
          <a-input-password v-model:value="modalForm.api_key" placeholder="请输入API密钥" />
        </a-form-item>

        <a-form-item label="API基础URL" name="api_base">
          <a-input v-model:value="modalForm.api_base" placeholder="可选，用于自定义API端点" />
        </a-form-item>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="温度" name="temperature" :label-col="{ span: 12 }" :wrapper-col="{ span: 12 }">
              <a-slider v-model:value="modalForm.temperature" :min="0" :max="2" :step="0.1" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="最大Token" name="max_tokens" :label-col="{ span: 10 }" :wrapper-col="{ span: 14 }">
              <a-input-number v-model:value="modalForm.max_tokens" :min="1" :max="8192" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="Top P" name="top_p">
          <a-slider v-model:value="modalForm.top_p" :min="0" :max="1" :step="0.1" />
        </a-form-item>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="启用" name="is_active" :label-col="{ span: 12 }" :wrapper-col="{ span: 12 }">
              <a-switch v-model:checked="modalForm.is_active" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="默认配置" name="is_default" :label-col="{ span: 10 }" :wrapper-col="{ span: 14 }">
              <a-switch v-model:checked="modalForm.is_default" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item v-if="isSuperuser" label="租户ID" name="tenant_id">
          <a-input-number v-model:value="modalForm.tenant_id" placeholder="为空表示全局配置" style="width: 100%" />
        </a-form-item>

        <a-form-item label="配置描述" name="description">
          <a-textarea v-model:value="modalForm.description" :rows="3" placeholder="请输入配置描述" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import type { FormInstance } from 'ant-design-vue'
import { useUserStore } from '@/store/modules/user'
import api from '@/api'
import FilterForm from '@/components/FilterForm/index.vue'
import CrudTable from '@/components/CrudTable/index.vue'
import { formatDateTime } from '@/utils/common'

const userStore = useUserStore()
const isSuperuser = computed(() => userStore.userInfo?.is_superuser || false)

// 搜索表单
const searchForm = reactive({
  name: '',
  model_provider: undefined,
  is_active: undefined,
})

// 筛选配置
const filterItems = [
  {
    key: 'name',
    label: '配置名称',
    component: 'input',
    props: { placeholder: '请输入配置名称' },
  },
  {
    key: 'model_provider',
    label: '模型提供商',
    component: 'select',
    props: {
      placeholder: '请选择模型提供商',
      options: [],
    },
  },
  {
    key: 'is_active',
    label: '状态',
    component: 'select',
    props: {
      placeholder: '请选择状态',
      options: [
        { label: '启用', value: true },
        { label: '禁用', value: false },
      ],
    },
  },
]

// 表格列
const columns = [
  { title: '配置名称', dataIndex: 'name', key: 'name', width: 150 },
  { title: '提供商', dataIndex: 'model_provider', key: 'model_provider', width: 120 },
  { title: '模型', dataIndex: 'model_name', key: 'model_name', width: 180 },
  { title: '温度', dataIndex: 'temperature', key: 'temperature', width: 80 },
  { title: '最大Token', dataIndex: 'max_tokens', key: 'max_tokens', width: 100 },
  { title: '默认', dataIndex: 'is_default', key: 'is_default', width: 80 },
  { title: '状态', dataIndex: 'is_active', key: 'is_active', width: 80 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', fixed: 'right', width: 150 },
]

// 表格数据
const tableData = ref([])
const loading = ref(false)
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

// 提供商选项
const providerOptions = ref([])

// 弹窗相关
const modalVisible = ref(false)
const modalLoading = ref(false)
const modalTitle = ref('新增配置')
const modalFormRef = ref<FormInstance>()
const isEdit = ref(false)
const currentId = ref<number | null>(null)

const modalForm = reactive({
  name: '',
  model_provider: undefined,
  model_name: '',
  api_key: '',
  api_base: '',
  temperature: 0.7,
  max_tokens: 2048,
  top_p: 1.0,
  is_active: true,
  is_default: false,
  tenant_id: undefined,
  description: '',
})

const modalRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  model_provider: [{ required: true, message: '请选择模型提供商', trigger: 'change' }],
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  api_key: [{ required: true, message: '请输入API密钥', trigger: 'blur' }],
}

// 获取提供商颜色
const providerColors: Record<string, string> = {
  openai: 'green',
  azure: 'blue',
  anthropic: 'purple',
  google: 'red',
  baidu: 'blue',
  alibaba: 'orange',
  zhipu: 'cyan',
  deepseek: 'geekblue',
  moonshot: 'gold',
  qianfan: 'lime',
  xunfei: 'volcano',
  minimax: 'magenta',
}

const getProviderColor = (provider: string) => {
  return providerColors[provider] || 'default'
}

const getProviderLabel = (provider: string) => {
  const option = providerOptions.value.find((item: any) => item.value === provider)
  return option?.label || provider
}

// 获取列表
const fetchList = async () => {
  loading.value = true
  try {
    const res: any = await api.getLLMConfigList({
      page: pagination.current,
      page_size: pagination.pageSize,
      name: searchForm.name || undefined,
      model_provider: searchForm.model_provider || undefined,
      is_active: searchForm.is_active,
    })
    if (res.code === 200) {
      tableData.value = res.data || []
      pagination.total = res.total || 0
    } else {
      message.error(res.msg || '获取列表失败')
    }
  } catch (error) {
    message.error('获取列表失败')
  } finally {
    loading.value = false
  }
}

// 获取提供商列表
const fetchProviders = async () => {
  try {
    const res: any = await api.getLLMProviders()
    if (res.code === 200) {
      providerOptions.value = res.data || []
      // 更新筛选器中的选项
      const providerFilter = filterItems.find(item => item.key === 'model_provider')
      if (providerFilter) {
        providerFilter.props.options = res.data || []
      }
    }
  } catch (error) {
    console.error('获取提供商列表失败', error)
  }
}

// 搜索
const handleSearch = () => {
  pagination.current = 1
  fetchList()
}

// 重置
const handleReset = () => {
  searchForm.name = ''
  searchForm.model_provider = undefined
  searchForm.is_active = undefined
  pagination.current = 1
  fetchList()
}

// 表格变化
const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchList()
}

// 新增
const handleClickAdd = () => {
  isEdit.value = false
  currentId.value = null
  modalTitle.value = '新增配置'
  resetModalForm()
  modalVisible.value = true
}

// 编辑
const handleEdit = (record: any) => {
  isEdit.value = true
  currentId.value = record.id
  modalTitle.value = '编辑配置'
  Object.assign(modalForm, {
    name: record.name,
    model_provider: record.model_provider,
    model_name: record.model_name,
    api_key: record.api_key,
    api_base: record.api_base || '',
    temperature: record.temperature,
    max_tokens: record.max_tokens,
    top_p: record.top_p,
    is_active: record.is_active,
    is_default: record.is_default,
    tenant_id: record.tenant_id,
    description: record.description || '',
  })
  modalVisible.value = true
}

// 保存
const handleSave = async () => {
  try {
    await modalFormRef.value?.validate()
    modalLoading.value = true

    const data = {
      ...modalForm,
      id: currentId.value,
    }

    const res: any = isEdit.value
      ? await api.updateLLMConfig(data)
      : await api.createLLMConfig(data)

    if (res.code === 200) {
      message.success(isEdit.value ? '更新成功' : '创建成功')
      modalVisible.value = false
      fetchList()
    } else {
      message.error(res.msg || (isEdit.value ? '更新失败' : '创建失败'))
    }
  } catch (error) {
    console.error('保存失败', error)
  } finally {
    modalLoading.value = false
  }
}

// 删除
const handleDelete = async (record: any) => {
  try {
    const res: any = await api.deleteLLMConfig({ id: record.id })
    if (res.code === 200) {
      message.success('删除成功')
      fetchList()
    } else {
      message.error(res.msg || '删除失败')
    }
  } catch (error) {
    message.error('删除失败')
  }
}

// 更新状态
const handleUpdateActive = async (record: any) => {
  record.publishingActive = true
  try {
    const res: any = await api.updateLLMConfig({
      id: record.id,
      is_active: !record.is_active,
    })
    if (res.code === 200) {
      message.success('更新成功')
      record.is_active = !record.is_active
    } else {
      message.error(res.msg || '更新失败')
    }
  } catch (error) {
    message.error('更新失败')
  } finally {
    record.publishingActive = false
  }
}

// 重置表单
const resetModalForm = () => {
  Object.assign(modalForm, {
    name: '',
    model_provider: undefined,
    model_name: '',
    api_key: '',
    api_base: '',
    temperature: 0.7,
    max_tokens: 2048,
    top_p: 1.0,
    is_active: true,
    is_default: false,
    tenant_id: undefined,
    description: '',
  })
}

onMounted(() => {
  fetchList()
  fetchProviders()
})
</script>

<style scoped lang="less">
.llm-config-page {
  padding: 20px;
}
</style>
