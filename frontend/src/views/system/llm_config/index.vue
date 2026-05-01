<template>
  <div class="llm-config-page">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
      :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
      @search="handleSearch" @reset="handleReset" @table-change="handleTableChange" @modal-ok="handleSave">
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="配置名称" class="filter-item">
            <a-input v-model:value="queryParams.name" placeholder="请输入配置名称" allow-clear @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="模型提供商" class="filter-item">
            <a-select v-model:value="queryParams.model_provider" placeholder="请选择模型提供商" allow-clear
              @change="handleSearch">
              <a-select-option v-for="provider in providers" :key="provider.value" :value="provider.value">
                {{ provider.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="启用状态" class="filter-item">
            <a-select v-model:value="queryParams.is_active" placeholder="请选择启用状态" allow-clear @change="handleSearch">
              <a-select-option :value="true">启用</a-select-option>
              <a-select-option :value="false">禁用</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </template>

      <!-- 操作按钮 -->
      <template #actions>
        <a-space>
          <a-button v-permission="'post/api/v1/ai/llm_config/create'" type="primary" @click="handleAdd">
            <PlusOutlined />
            新建配置
          </a-button>
          <a-button @click="handleGatewayStatus">
            <ApiOutlined />
            网关状态
          </a-button>
        </a-space>
      </template>

      <!-- 表格列自定义 -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'is_active'">
          <a-tag :color="record.is_active ? 'success' : 'error'">
            {{ record.is_active ? '启用' : '禁用' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'is_default'">
          <a-tag v-if="record.is_default" color="blue">默认</a-tag>
          <span v-else>-</span>
        </template>
        <template v-if="column.key === 'model_provider'">
          {{ getProviderLabel(record.model_provider) }}
        </template>
        <template v-if="column.key === 'model'">
          {{ record.litellm_params?.model || '-' }}
        </template>
        <template v-if="column.key === 'created_at'">
          {{ formatDateTime(record.created_at) }}
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button type="link" size="small" @click="handleTest(record)">测试</a-button>
            <a-button v-permission="'post/api/v1/ai/llm_config/update'" type="link" size="small"
              @click="handleEdit(record)">编辑</a-button>
            <a-button type="link" size="small" @click="handleMethods(record)">方法</a-button>
            <a-popconfirm title="确定删除该配置吗？" @confirm="handleDelete(record)">
              <a-button v-permission="'delete/api/v1/ai/llm_config/delete'" type="link" danger
                size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>

      <!-- 弹窗表单 -->
      <template #modal-form="{ form }">
        <a-tabs v-model:activeKey="activeTab">
          <a-tab-pane key="basic" tab="基本信息">
            <a-form-item label="配置名称" name="name">
              <a-input v-model:value="form.name" placeholder="请输入配置名称，如：GPT-4" />
            </a-form-item>
            <a-form-item label="模型提供商" name="model_provider">
              <a-select v-model:value="form.model_provider" placeholder="请选择模型提供商">
                <a-select-option v-for="provider in providers" :key="provider.value" :value="provider.value">
                  {{ provider.label }}
                </a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="模型名称" name="litellm_params.model">
              <a-input v-model:value="form.litellm_params.model"
                placeholder="请输入模型名称，如：openai/gpt-4 或 gpt-4" />
            </a-form-item>
            <a-form-item label="API Key" name="litellm_params.api_key">
              <a-input-password v-model:value="form.litellm_params.api_key" placeholder="请输入 API Key" />
            </a-form-item>
            <a-form-item label="API Base URL" name="litellm_params.api_base">
              <a-input v-model:value="form.litellm_params.api_base"
                placeholder="可选，如：https://api.openai.com/v1" />
            </a-form-item>
            <a-form-item label="超时时间(秒)" name="litellm_params.timeout">
              <a-input-number v-model:value="form.litellm_params.timeout" :min="10" :max="300" style="width: 100%" />
            </a-form-item>
            <a-form-item label="描述" name="description">
              <a-textarea v-model:value="form.description" placeholder="请输入配置描述" :rows="2" />
            </a-form-item>
            <a-form-item label="默认配置" name="is_default">
              <a-switch v-model:checked="form.is_default" />
            </a-form-item>
            <a-form-item label="启用" name="is_active">
              <a-switch v-model:checked="form.is_active" />
            </a-form-item>
          </a-tab-pane>
          <a-tab-pane key="advanced" tab="高级配置">
            <a-form-item label="最大重试次数" name="litellm_params.max_retries">
              <a-input-number v-model:value="form.litellm_params.max_retries" :min="0" :max="5" style="width: 100%" />
            </a-form-item>
            <a-form-item label="RPM 限制" name="litellm_params.rpm_limit">
              <a-input-number v-model:value="form.litellm_params.rpm_limit" :min="0" style="width: 100%"
                placeholder="每分钟请求限制" />
            </a-form-item>
            <a-form-item label="TPM 限制" name="litellm_params.tpm_limit">
              <a-input-number v-model:value="form.litellm_params.tpm_limit" :min="0" style="width: 100%"
                placeholder="每分钟 Token 限制" />
            </a-form-item>
            <a-form-item label="冷却时间(秒)" name="litellm_params.cooldown_time">
              <a-input-number v-model:value="form.litellm_params.cooldown_time" :min="0" style="width: 100%"
                placeholder="失败后冷却时间" />
            </a-form-item>
          </a-tab-pane>
          <a-tab-pane key="model_info" tab="模型信息">
            <a-form-item label="模式" name="model_info.mode">
              <a-select v-model:value="form.model_info.mode" placeholder="请选择模式">
                <a-select-option value="chat">Chat</a-select-option>
                <a-select-option value="completion">Completion</a-select-option>
                <a-select-option value="embedding">Embedding</a-select-option>
                <a-select-option value="image">Image</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="最大 Token" name="model_info.max_tokens">
              <a-input-number v-model:value="form.model_info.max_tokens" :min="1" style="width: 100%" />
            </a-form-item>
            <a-form-item label="支持 Function Calling">
              <a-switch v-model:checked="form.model_info.supports_function_calling" />
            </a-form-item>
            <a-form-item label="支持 Vision">
              <a-switch v-model:checked="form.model_info.supports_vision" />
            </a-form-item>
            <a-form-item label="输入 Token 单价" name="model_info.input_cost_per_token">
              <a-input-number v-model:value="form.model_info.input_cost_per_token" :min="0" :step="0.000001"
                style="width: 100%" />
            </a-form-item>
            <a-form-item label="输出 Token 单价" name="model_info.output_cost_per_token">
              <a-input-number v-model:value="form.model_info.output_cost_per_token" :min="0" :step="0.000001"
                style="width: 100%" />
            </a-form-item>
          </a-tab-pane>
        </a-tabs>
      </template>
    </CrudTable>

    <!-- 测试结果显示弹窗 -->
    <a-modal v-model:open="testModalVisible" title="测试结果" :footer="null" width="600px">
      <a-spin :spinning="testLoading">
        <div v-if="testResult" class="test-result">
          <a-descriptions :column="1" bordered>
            <a-descriptions-item label="状态">
              <a-tag :color="testResult.status === 'success' ? 'success' : 'error'">
                {{ testResult.status === 'success' ? '成功' : '失败' }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="延迟">{{ testResult.latency_ms }} ms</a-descriptions-item>
            <a-descriptions-item label="模型响应">{{ testResult.model_response }}</a-descriptions-item>
          </a-descriptions>
        </div>
        <div v-if="testError" class="test-error">
          <a-alert type="error" :message="testError" />
        </div>
      </a-spin>
    </a-modal>

    <!-- 网关状态弹窗 -->
    <a-modal v-model:open="gatewayModalVisible" title="LiteLLM 网关状态" :footer="null" width="500px">
      <a-spin :spinning="gatewayLoading">
        <div v-if="gatewayStatus" class="gateway-status">
          <a-descriptions :column="1" bordered>
            <a-descriptions-item label="状态">
              <a-tag :color="gatewayStatus.status === 'healthy' ? 'success' : 'error'">
                {{ gatewayStatus.status === 'healthy' ? '健康' : '异常' }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="版本">{{ gatewayStatus.version || '-' }}</a-descriptions-item>
            <a-descriptions-item label="已加载模型">{{ gatewayStatus.models_loaded || 0 }}</a-descriptions-item>
            <a-descriptions-item label="网关地址">{{ gatewayStatus.gateway_url || '-' }}</a-descriptions-item>
            <a-descriptions-item v-if="gatewayStatus.error" label="错误信息">
              <span style="color: red">{{ gatewayStatus.error }}</span>
            </a-descriptions-item>
          </a-descriptions>
        </div>
      </a-spin>
    </a-modal>

    <!-- 方法状态弹窗 -->
    <a-modal v-model:open="methodsModalVisible" title="结构化输出方法状态" :footer="null" width="700px">
      <a-spin :spinning="methodsLoading">
        <div v-if="methodsData" class="methods-status">
          <a-table :columns="methodsColumns" :data-source="methodsList" :pagination="false" size="small">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'supported'">
                <a-tag :color="record.supported ? 'success' : 'error'">
                  {{ record.supported ? '支持' : '不支持' }}
                </a-tag>
              </template>
              <template v-if="column.key === 'failed_count'">
                <a-badge :count="record.failed_count" :number-style="{ backgroundColor: record.failed_count > 0 ? '#ff4d4f' : '#52c41a' }" />
              </template>
              <template v-if="column.key === 'last_error'">
                <a-tooltip v-if="record.last_error" :title="record.last_error">
                  <span class="error-text">{{ record.last_error.slice(0, 20) }}...</span>
                </a-tooltip>
                <span v-else>-</span>
              </template>
            </template>
          </a-table>
          <div class="methods-actions">
            <a-button type="primary" @click="handleResetMethods">重置所有方法</a-button>
          </div>
        </div>
      </a-spin>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { formatDateTime } from '@/utils'
import { PlusOutlined, ApiOutlined } from '@ant-design/icons-vue'
import { computed, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'LLMConfigPage' })

const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  name: '',
  model_provider: undefined as string | undefined,
  is_active: undefined as boolean | undefined,
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
const activeTab = ref('basic')
const modalForm = reactive({
  id: undefined as number | undefined,
  name: '',
  model_provider: '',
  litellm_params: {
    model: '',
    api_key: '',
    api_base: '',
    timeout: 60,
    max_retries: 2,
    rpm_limit: undefined as number | undefined,
    tpm_limit: undefined as number | undefined,
    cooldown_time: undefined as number | undefined,
  },
  model_info: {
    mode: 'chat',
    max_tokens: 8192,
    supports_function_calling: true,
    supports_vision: false,
    input_cost_per_token: undefined as number | undefined,
    output_cost_per_token: undefined as number | undefined,
  },
  is_active: true,
  is_default: false,
  description: '',
})

// 提供商列表
const providers = ref([
  { value: 'openai', label: 'OpenAI' },
  { value: 'azure', label: 'Azure OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'vertex_ai', label: 'Google Vertex AI' },
  { value: 'bedrock', label: 'AWS Bedrock' },
  { value: 'ollama', label: 'Ollama' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'qwen', label: '通义千问' },
  { value: 'moonshot', label: 'Moonshot' },
  { value: 'zhipuai', label: '智谱 AI' },
])

// 计算属性
const columns = computed(() => [
  { title: '配置名称', dataIndex: 'name', key: 'name', width: 150, ellipsis: true },
  { title: '提供商', key: 'model_provider', width: 120 },
  { title: '模型', key: 'model', width: 180, ellipsis: true },
  { title: '默认', key: 'is_default', width: 80, align: 'center' },
  { title: '状态', key: 'is_active', width: 80, align: 'center' },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 220, fixed: 'right' },
])

const methodsColumns = [
  { title: '方法名称', dataIndex: 'name', key: 'name', width: 180 },
  { title: '支持状态', key: 'supported', width: 100, align: 'center' },
  { title: '失败次数', key: 'failed_count', width: 100, align: 'center' },
  { title: '最后错误', key: 'last_error', ellipsis: true },
  { title: '最后尝试', dataIndex: 'last_attempt', key: 'last_attempt', width: 180 },
]

const filterItemCount = computed(() => 3)

const modalRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: ['input', 'blur'] }],
  model_provider: [{ required: true, message: '请选择模型提供商', trigger: 'change' }],
}

// 测试弹窗
const testModalVisible = ref(false)
const testLoading = ref(false)
const testResult = ref<any>(null)
const testError = ref('')

// 网关状态弹窗
const gatewayModalVisible = ref(false)
const gatewayLoading = ref(false)
const gatewayStatus = ref<any>(null)

// 方法状态弹窗
const methodsModalVisible = ref(false)
const methodsLoading = ref(false)
const methodsData = ref<any>(null)
const currentConfigId = ref<number | null>(null)

const methodsList = computed(() => {
  if (!methodsData.value?.capabilities?.structured_output_methods) return []
  const methods = methodsData.value.capabilities.structured_output_methods
  return Object.entries(methods).map(([key, value]: [string, any]) => ({
    key,
    name: getMethodName(key),
    ...value,
  }))
})

function getMethodName(key: string): string {
  const names: Record<string, string> = {
    with_structured_output: 'with_structured_output (官方FC)',
    bind_tools_stream: 'bind_tools_stream (流式FC)',
    custom_fc_non_stream: 'custom_fc_non_stream (自定义FC非流式)',
    custom_fc_stream: 'custom_fc_stream (自定义FC流式)',
    pydantic_parser: 'pydantic_parser (Pydantic解析)',
    json_parser: 'json_parser (JSON解析)',
  }
  return names[key] || key
}

function getProviderLabel(value: string): string {
  const provider = providers.value.find(p => p.value === value)
  return provider?.label || value
}

// 加载数据
async function loadData() {
  loading.value = true
  try {
    const params = {
      ...queryParams,
      page: pagination.current,
      page_size: pagination.pageSize,
    }
    const res: any = await api.getLLMConfigList(params)
    tableData.value = res.data || []
    pagination.total = res.total || 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.current = 1
  loadData()
}

function handleReset() {
  queryParams.name = ''
  queryParams.model_provider = undefined
  queryParams.is_active = undefined
  handleSearch()
}

function handleTableChange(p: any) {
  pagination.current = p.current
  pagination.pageSize = p.pageSize
  loadData()
}

function handleAdd() {
  modalTitle.value = '新增 LLM 配置'
  activeTab.value = 'basic'
  Object.assign(modalForm, {
    id: undefined,
    name: '',
    model_provider: '',
    litellm_params: {
      model: '',
      api_key: '',
      api_base: '',
      timeout: 60,
      max_retries: 2,
      rpm_limit: undefined,
      tpm_limit: undefined,
      cooldown_time: undefined,
    },
    model_info: {
      mode: 'chat',
      max_tokens: 8192,
      supports_function_calling: true,
      supports_vision: false,
      input_cost_per_token: undefined,
      output_cost_per_token: undefined,
    },
    is_active: true,
    is_default: false,
    description: '',
  })
  crudTableRef.value?.openAddModal()
}

function handleEdit(record: any) {
  modalTitle.value = '编辑 LLM 配置'
  activeTab.value = 'basic'
  Object.assign(modalForm, {
    ...record,
    litellm_params: {
      ...modalForm.litellm_params,
      ...record.litellm_params,
    },
    model_info: {
      ...modalForm.model_info,
      ...record.model_info,
    },
  })
  crudTableRef.value?.openEditModal(record)
}

async function handleSave(form: Record<string, any>, action: 'add' | 'edit') {
  modalLoading.value = true
  try {
    const apiFn = action === 'add' ? api.createLLMConfig : api.updateLLMConfig
    const res: any = await apiFn({ ...form })
    if (res.code === 200) {
      window.$message?.success(action === 'add' ? '新增成功' : '编辑成功')
      crudTableRef.value?.closeModal()
      loadData()
    }
  } finally {
    modalLoading.value = false
  }
}

async function handleDelete(record: any) {
  try {
    const res: any = await api.deleteLLMConfig({ id: record.id })
    if (res.code === 200) {
      window.$message?.success('删除成功')
      loadData()
    }
  } catch (error) {
    console.error('删除失败', error)
  }
}

async function handleTest(record: any) {
  testModalVisible.value = true
  testLoading.value = true
  testResult.value = null
  testError.value = ''
  try {
    const res: any = await api.testLLMConfig({ id: record.id })
    if (res.code === 200) {
      testResult.value = res.data
    } else {
      testError.value = res.msg || '测试失败'
    }
  } catch (error: any) {
    testError.value = error.response?.data?.msg || error.message || '测试失败'
  } finally {
    testLoading.value = false
  }
}

async function handleGatewayStatus() {
  gatewayModalVisible.value = true
  gatewayLoading.value = true
  gatewayStatus.value = null
  try {
    const res: any = await api.getLLMGatewayStatus()
    if (res.code === 200) {
      gatewayStatus.value = res.data
    } else {
      gatewayStatus.value = { status: 'error', error: res.msg }
    }
  } catch (error: any) {
    gatewayStatus.value = { status: 'error', error: error.message }
  } finally {
    gatewayLoading.value = false
  }
}

async function handleMethods(record: any) {
  currentConfigId.value = record.id
  methodsModalVisible.value = true
  methodsLoading.value = true
  methodsData.value = null
  try {
    const res: any = await api.getLLMMethods({ id: record.id })
    if (res.code === 200) {
      methodsData.value = res.data
    }
  } finally {
    methodsLoading.value = false
  }
}

async function handleResetMethods() {
  if (!currentConfigId.value) return
  try {
    const res: any = await api.resetLLMMethods({ id: currentConfigId.value })
    if (res.code === 200) {
      window.$message?.success('重置成功')
      methodsData.value = res.data
    }
  } catch (error) {
    console.error('重置失败', error)
  }
}

onMounted(loadData)
</script>

<style scoped lang="less">
.llm-config-page {
  padding: 16px;
}

.test-result,
.gateway-status,
.methods-status {
  padding: 16px;
}

.test-error {
  padding: 16px;
}

.methods-actions {
  margin-top: 16px;
  text-align: right;
}

.error-text {
  color: #ff4d4f;
}
</style>