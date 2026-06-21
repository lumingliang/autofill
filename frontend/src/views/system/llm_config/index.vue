<template>
  <div class="llm-config-page">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
      :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
      @search="handleSearch" @reset="handleReset" @table-change="handleTableChange" @modal-ok="handleSave">
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="Model ID" class="filter-item">
            <a-input v-model:value="queryParams.model_id" placeholder="请输入Model ID" allow-clear @pressEnter="handleSearch" />
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
          <a-dropdown>
            <a-button>
              <SyncOutlined />
              同步操作
              <DownOutlined />
            </a-button>
            <template #overlay>
              <a-menu>
                <a-menu-item @click="handleSyncToGateway">
                  <CloudUploadOutlined />
                  同步到网关
                </a-menu-item>
                <a-menu-item @click="handleSyncFromGateway">
                  <CloudDownloadOutlined />
                  从网关同步
                </a-menu-item>
                <a-menu-item @click="handleViewGatewayModels">
                  <EyeOutlined />
                  查看网关模型
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
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
          {{ record.model || '-' }}
        </template>
        <template v-if="column.key === 'created_at'">
          {{ formatDateTime(record.created_at) }}
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button type="link" size="small" @click="handleTest(record)">测试</a-button>
            <a-button v-permission="'post/api/v1/ai/llm_config/update'" type="link" size="small"
              @click="handleEdit(record)">编辑</a-button>
            <a-popconfirm title="确定删除该配置吗？" @confirm="handleDelete(record)">
              <a-button v-permission="'delete/api/v1/ai/llm_config/delete'" type="link" danger
                size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>

      <!-- 弹窗表单 -->
      <template #modal-form="{ form }">
        <a-form-item label="Model ID" name="model_id">
          <a-input v-model:value="form.model_id" placeholder="请输入Model ID，如：gpt-4" />
        </a-form-item>
        <a-form-item label="模型提供商" name="model_provider">
          <a-select v-model:value="form.model_provider" placeholder="请选择模型提供商">
            <a-select-option v-for="provider in providers" :key="provider.value" :value="provider.value">
              {{ provider.label }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="API Key" name="api_key">
          <a-input-password v-model:value="form.api_key" placeholder="请输入 API Key" />
        </a-form-item>
        <a-form-item label="API Base URL" name="api_base">
          <a-input v-model:value="form.api_base" placeholder="可选，如：https://api.openai.com/v1" />
        </a-form-item>
        <a-form-item label="超时时间(秒)" name="timeout">
          <a-input-number v-model:value="form.timeout" :min="10" :max="300" style="width: 100%" />
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

    <!-- 同步到网关弹窗 -->
    <a-modal v-model:open="syncToGatewayModalVisible" title="同步配置到 LiteLLM 网关" :footer="null" width="500px">
      <a-spin :spinning="syncToGatewayLoading">
        <div class="sync-actions">
          <a-space direction="vertical" style="width: 100%">
            <a-alert message="同步说明" description="将本地数据库中的模型配置同步到 LiteLLM 网关。可以选择同步单个配置或同步所有活跃配置。" type="info"
              show-icon />
            <a-divider />
            <a-space>
              <a-button type="primary" :loading="syncToGatewayLoading" @click="handleSyncAllToGateway">
                同步所有活跃配置
              </a-button>
              <a-button @click="syncToGatewayModalVisible = false">关闭</a-button>
            </a-space>
          </a-space>
        </div>
        <div v-if="syncToGatewayResult" class="sync-result">
          <a-divider />
          <a-result :status="syncToGatewayResult.success ? 'success' : 'error'"
            :title="syncToGatewayResult.success ? '同步成功' : '同步失败'" :sub-title="syncToGatewayResult.message" />
        </div>
      </a-spin>
    </a-modal>

    <!-- 从网关同步弹窗 -->
    <a-modal v-model:open="syncFromGatewayModalVisible" title="从 LiteLLM 网关同步配置" :footer="null" width="600px">
      <a-spin :spinning="syncFromGatewayLoading">
        <div class="sync-actions">
          <a-space direction="vertical" style="width: 100%">
            <a-alert message="同步说明" description="从 LiteLLM 网关获取模型配置并导入到本地数据库。已存在的配置将被更新，不存在的配置将被创建。" type="info"
              show-icon />
            <a-divider />
            <a-space>
              <a-button type="primary" :loading="syncFromGatewayLoading" @click="handleConfirmSyncFromGateway">
                开始同步
              </a-button>
              <a-button @click="syncFromGatewayModalVisible = false">关闭</a-button>
            </a-space>
          </a-space>
        </div>
        <div v-if="syncFromGatewayResult" class="sync-result">
          <a-divider />
          <a-descriptions title="同步结果" :column="2" bordered>
            <a-descriptions-item label="总计">{{ syncFromGatewayResult.total }}</a-descriptions-item>
            <a-descriptions-item label="新建">{{ syncFromGatewayResult.created }}</a-descriptions-item>
            <a-descriptions-item label="更新">{{ syncFromGatewayResult.updated }}</a-descriptions-item>
            <a-descriptions-item label="跳过">{{ syncFromGatewayResult.skipped }}</a-descriptions-item>
            <a-descriptions-item label="失败">{{ syncFromGatewayResult.failed }}</a-descriptions-item>
          </a-descriptions>
          <div v-if="syncFromGatewayResult.errors && syncFromGatewayResult.errors.length > 0" class="sync-errors">
            <a-divider />
            <a-alert message="错误信息" type="error" show-icon />
            <a-list size="small" :data-source="syncFromGatewayResult.errors"
              style="margin-top: 8px; max-height: 200px; overflow-y: auto;">
              <template #renderItem="{ item }">
                <a-list-item>
                  <span style="color: #ff4d4f">{{ item }}</span>
                </a-list-item>
              </template>
            </a-list>
          </div>
        </div>
      </a-spin>
    </a-modal>

    <!-- 网关模型列表弹窗 -->
    <a-modal v-model:open="gatewayModelsModalVisible" title="LiteLLM 网关模型列表" :footer="null" width="800px">
      <a-spin :spinning="gatewayModelsLoading">
        <div v-if="gatewayModelsData" class="gateway-models">
          <a-alert :message="`共 ${gatewayModelsData.total} 个模型`" type="info" show-icon style="margin-bottom: 16px" />
          <a-table :columns="gatewayModelsColumns" :data-source="gatewayModelsData.models" :pagination="false"
            size="small" bordered>
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'model_name'">
                <strong>{{ record.model_name }}</strong>
              </template>
              <template v-if="column.key === 'model'">
                {{ record.litellm_params?.model || '-' }}
              </template>
              <template v-if="column.key === 'api_base'">
                <span class="ellipsis-text">{{ record.litellm_params?.api_base || '-' }}</span>
              </template>
              <template v-if="column.key === 'actions'">
                <a-button type="link" size="small" @click="handleImportGatewayModel(record)">
                  导入
                </a-button>
              </template>
            </template>
          </a-table>
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


  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { formatDateTime } from '@/utils'
import { ApiOutlined, CloudDownloadOutlined, CloudUploadOutlined, DownOutlined, EyeOutlined, PlusOutlined, SyncOutlined } from '@ant-design/icons-vue'
import { computed, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'LLMConfigPage' })

const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  model_id: '',
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
const modalForm = reactive({
  id: undefined as number | undefined,
  model_id: '',
  model_provider: '',
  api_key: '',
  api_base: '',
  timeout: 60,
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
  { title: 'Model ID', dataIndex: 'model_id', key: 'model_id', width: 180, ellipsis: true },
  { title: '提供商', key: 'model_provider', width: 120 },
  { title: '默认', key: 'is_default', width: 80, align: 'center' },
  { title: '状态', key: 'is_active', width: 80, align: 'center' },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 180, fixed: 'right' },
])

const filterItemCount = computed(() => 3)

const modalRules = {
  model_id: [{ required: true, message: '请输入Model ID', trigger: ['input', 'blur'] }],
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

// 网关模型列表弹窗
const gatewayModelsModalVisible = ref(false)
const gatewayModelsLoading = ref(false)
const gatewayModelsData = ref<any>(null)

const gatewayModelsColumns = [
  { title: '模型名称', key: 'model_name', width: 180 },
  { title: '模型标识', key: 'model', width: 200, ellipsis: true },
  { title: 'API Base', key: 'api_base', ellipsis: true },
  { title: '操作', key: 'actions', width: 80, align: 'center' },
]

// 同步到网关弹窗
const syncToGatewayModalVisible = ref(false)
const syncToGatewayLoading = ref(false)
const syncToGatewayResult = ref<any>(null)

// 从网关同步弹窗
const syncFromGatewayModalVisible = ref(false)
const syncFromGatewayLoading = ref(false)
const syncFromGatewayResult = ref<any>(null)

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
  queryParams.model_id = ''
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
  Object.assign(modalForm, {
    id: undefined,
    model_id: '',
    model_provider: '',
    api_key: '',
    api_base: '',
    timeout: 60,
    is_active: true,
    is_default: false,
    description: '',
  })
  crudTableRef.value?.openAddModal()
}

function handleEdit(record: any) {
  modalTitle.value = '编辑 LLM 配置'
  Object.assign(modalForm, {
    ...record,
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

// 同步到网关
function handleSyncToGateway() {
  syncToGatewayModalVisible.value = true
  syncToGatewayResult.value = null
}

async function handleSyncAllToGateway() {
  syncToGatewayLoading.value = true
  syncToGatewayResult.value = null
  try {
    const res: any = await api.syncToGateway({})
    if (res.code === 200) {
      syncToGatewayResult.value = res.data
      window.$message?.success(res.msg || '同步成功')
    } else {
      syncToGatewayResult.value = { success: false, message: res.msg || '同步失败' }
      window.$message?.error(res.msg || '同步失败')
    }
  } catch (error: any) {
    syncToGatewayResult.value = { success: false, message: error.response?.data?.msg || error.message || '同步失败' }
    window.$message?.error(error.response?.data?.msg || error.message || '同步失败')
  } finally {
    syncToGatewayLoading.value = false
  }
}

// 从网关同步
function handleSyncFromGateway() {
  syncFromGatewayModalVisible.value = true
  syncFromGatewayResult.value = null
}

async function handleConfirmSyncFromGateway() {
  syncFromGatewayLoading.value = true
  syncFromGatewayResult.value = null
  try {
    const res: any = await api.syncFromGateway({})
    if (res.code === 200) {
      syncFromGatewayResult.value = res.data
      window.$message?.success(res.msg || '同步成功')
      // 刷新列表
      loadData()
    } else {
      syncFromGatewayResult.value = { total: 0, created: 0, updated: 0, skipped: 0, failed: 1, errors: [res.msg || '同步失败'] }
      window.$message?.error(res.msg || '同步失败')
    }
  } catch (error: any) {
    syncFromGatewayResult.value = { total: 0, created: 0, updated: 0, skipped: 0, failed: 1, errors: [error.response?.data?.msg || error.message || '同步失败'] }
    window.$message?.error(error.response?.data?.msg || error.message || '同步失败')
  } finally {
    syncFromGatewayLoading.value = false
  }
}

// 查看网关模型
async function handleViewGatewayModels() {
  gatewayModelsModalVisible.value = true
  gatewayModelsLoading.value = true
  gatewayModelsData.value = null
  try {
    const res: any = await api.getGatewayModels()
    if (res.code === 200) {
      gatewayModelsData.value = res.data
    } else {
      window.$message?.error(res.msg || '获取失败')
    }
  } catch (error: any) {
    window.$message?.error(error.response?.data?.msg || error.message || '获取失败')
  } finally {
    gatewayModelsLoading.value = false
  }
}

// 导入单个网关模型
async function handleImportGatewayModel(record: any) {
  try {
    // 先检查是否已存在
    const existing = tableData.value.find((item: any) => item.model_id === record.model_name)
    if (existing) {
      window.$message?.warning(`模型 "${record.model_name}" 已存在，将更新配置`)
    }
    // 触发从网关同步
    const res: any = await api.syncFromGateway({})
    if (res.code === 200) {
      window.$message?.success(`模型 "${record.model_name}" 导入成功`)
      loadData()
      // 关闭弹窗
      gatewayModelsModalVisible.value = false
    } else {
      window.$message?.error(res.msg || '导入失败')
    }
  } catch (error: any) {
    window.$message?.error(error.response?.data?.msg || error.message || '导入失败')
  }
}

onMounted(loadData)
</script>

<style scoped lang="less">
.llm-config-page {}

.sync-actions {
  padding: 16px 0;
}

.sync-result {
  margin-top: 16px;
}

.sync-errors {
  margin-top: 16px;
}

.ellipsis-text {
  display: inline-block;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gateway-models {
  max-height: 500px;
  overflow-y: auto;
}
</style>