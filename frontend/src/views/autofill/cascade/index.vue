<template>
  <div class="cascade-config-management">
    <a-row :gutter="16">
      <a-col :span="8">
        <a-card title="级联配置列表">
          <template #extra>
            <a-button type="primary" @click="handleAdd">
              <PlusOutlined />
              新建配置
            </a-button>
          </template>
          <a-list :data-source="configList" :loading="listLoading" item-layout="horizontal">
            <template #renderItem="{ item }">
              <a-list-item :actions="[
                <a-button type="link" size="small" @click="handleEdit(item)">编辑</a-button>,
                <a-popconfirm title="确定删除此配置吗？" @confirm="handleDelete(item)">
                  <a-button type="link" danger size="small">删除</a-button>
                </a-popconfirm>,
                <a-button type="link" size="small" @click="handleSync(item)">同步</a-button>
              ]">
                <a-list-item-meta>
                  <template #title>{{ item.parent_field_name }}</template>
                  <template #description>
                    <a-tag color="blue">后缀: {{ item.field_name_suffix }}</a-tag>
                    <a-tag :color="item.is_active ? 'green' : 'red'">
                      {{ item.is_active ? '启用' : '禁用' }}
                    </a-tag>
                    <br />
                    <span v-if="item.last_sync_at">
                      最后同步: {{ formatDateTime(item.last_sync_at) }}
                    </span>
                  </template>
                </a-list-item-meta>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>
      <a-col :span="16">
        <a-card title="配置详情">
          <a-form layout="vertical" :model="formState" :label-col="{ span: 6 }" :wrapper-col="{ span: 18 }">
            <a-form-item label="父字段">
              <a-select v-model:value="formState.parent_field_id" placeholder="请选择父字段" :options="fieldOptions"
                @change="handleParentFieldChange" />
            </a-form-item>
            <a-form-item label="父字段组">
              <a-select v-model:value="formState.parent_field_group_id" placeholder="请选择父字段组"
                :options="fieldGroupOptions" />
            </a-form-item>
            <a-form-item label="字段名后缀">
              <a-input v-model:value="formState.field_name_suffix" placeholder="请输入字段名后缀" />
            </a-form-item>
            <a-form-item label="字段标签前缀">
              <a-input v-model:value="formState.field_label_prefix" placeholder="请输入字段标签前缀" />
            </a-form-item>

            <a-divider />

            <a-form-item label="curl命令">
              <a-textarea v-model:value="formState.api_curl" placeholder="请输入curl命令" :rows="6" />
            </a-form-item>

            <a-form-item :wrapper-col="{ offset: 6 }">
              <a-space>
                <a-button type="primary" @click="handleParseCurl" :loading="parseLoading">
                  <ImportOutlined />
                  解析curl生成Schema
                </a-button>
                <a-button v-if="openapiSchema" type="default" @click="handleSyncFromSchema" :loading="syncSchemaLoading">
                  <SyncOutlined />
                  根据Schema同步
                </a-button>
              </a-space>
            </a-form-item>

            <!-- OpenAPI Schema 显示/编辑区域 -->
            <a-form-item v-if="openapiSchema" label="OpenAPI Schema (YAML)">
              <a-textarea v-model:value="openapiSchema" :rows="10" />
            </a-form-item>

            <a-form-item label="API参数映射">
              <a-textarea v-model:value="apiParamsMappingJson" placeholder='{"parentEventId": "{parent_value}"}'
                :rows="4" />
              <a-typography-text type="secondary">
                使用 {parent_value} 表示父字段值的占位符
              </a-typography-text>
            </a-form-item>

            <a-form-item label="字段映射">
              <a-textarea v-model:value="fieldMappingJson" placeholder='{"label_path": "$.data[*].label", "value_path": "$.data[*].value"}'
                :rows="3" />
            </a-form-item>

            <a-divider />

            <a-form-item label="启用展平">
              <a-switch v-model:checked="formState.enable_flatten" />
            </a-form-item>

            <template v-if="formState.enable_flatten">
              <a-divider orientation="left">展平配置</a-divider>

              <a-row :gutter="16">
                <a-col :span="12">
                  <a-form-item label="标签路径1">
                    <a-input v-model:value="flattenConfig.label_path_level1" placeholder="$.data[*].label" />
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item label="标签路径2">
                    <a-input v-model:value="flattenConfig.label_path_level2" placeholder="$.children[*].label" />
                  </a-form-item>
                </a-col>
              </a-row>

              <a-row :gutter="16">
                <a-col :span="12">
                  <a-form-item label="标签路径3">
                    <a-input v-model:value="flattenConfig.label_path_level3" placeholder="" />
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item label="标签分隔符">
                    <a-input v-model:value="flattenConfig.label_separator" placeholder="-" />
                  </a-form-item>
                </a-col>
              </a-row>

              <a-row :gutter="16">
                <a-col :span="12">
                  <a-form-item label="值路径1">
                    <a-input v-model:value="flattenConfig.value_path_level1" placeholder="$.data[*].value" />
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item label="值路径2">
                    <a-input v-model:value="flattenConfig.value_path_level2" placeholder="$.children[*].value" />
                  </a-form-item>
                </a-col>
              </a-row>

              <a-row :gutter="16">
                <a-col :span="12">
                  <a-form-item label="值路径3">
                    <a-input v-model:value="flattenConfig.value_path_level3" placeholder="" />
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item label="值分隔符">
                    <a-input v-model:value="flattenConfig.value_separator" placeholder="-" />
                  </a-form-item>
                </a-col>
              </a-row>
            </template>

            <a-form-item label="启用状态">
              <a-switch v-model:checked="formState.is_active" />
            </a-form-item>

            <a-form-item :wrapper-col="{ offset: 6 }">
              <a-space>
                <a-button type="primary" :loading="saveLoading" @click="handleSave">
                  保存
                </a-button>
                <a-button @click="handleReset">
                  重置
                </a-button>
              </a-space>
            </a-form-item>
          </a-form>
        </a-card>

        <a-card title="同步数据" style="margin-top: 16px" v-if="selectedConfig">
          <a-button type="primary" :loading="syncLoading" @click="handleSync(selectedConfig)">
            <SyncOutlined />
            同步所有子字段
          </a-button>
          <a-space style="margin-left: 16px">
            <a-tag color="blue">父字段: {{ selectedConfig.parent_field_name }}</a-tag>
          </a-space>

          <a-divider />

          <a-table :columns="dataColumns" :data-source="cascadeDataList" :loading="dataLoading" row-key="id">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'sync_status'">
                <a-tag :color="record.sync_status === 'success' ? 'green' : 'red'">
                  {{ record.sync_status === 'success' ? '成功' : record.sync_status }}
                </a-tag>
              </template>
              <template v-if="column.key === 'child_options'">
                <span>共 {{ record.child_options?.length || 0 }} 个选项</span>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import { PlusOutlined, SyncOutlined, ImportOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { onMounted, reactive, ref } from 'vue'

const listLoading = ref(false)
const saveLoading = ref(false)
const syncLoading = ref(false)
const dataLoading = ref(false)
const parseLoading = ref(false)
const syncSchemaLoading = ref(false)

const openapiSchema = ref('')

const configList = ref<any[]>([])
const selectedConfig = ref<any>(null)

const fieldOptions = ref<any[]>([])
const fieldGroupOptions = ref<any[]>([])

const formState = reactive({
  id: undefined as number | undefined,
  parent_field_id: undefined as number | undefined,
  parent_field_group_id: undefined as number | undefined,
  field_name_suffix: '-子字段',
  field_label_prefix: '',
  api_curl: '',
  api_params_mapping: {} as any,
  field_mapping: {} as any,
  enable_flatten: false,
  flatten_config: {} as any,
  is_active: true,
})

const flattenConfig = reactive({
  label_path_level1: '',
  label_path_level2: '',
  label_path_level3: '',
  label_separator: '-',
  value_path_level1: '',
  value_path_level2: '',
  value_path_level3: '',
  value_separator: '-',
})

const cascadeDataList = ref<any[]>([])

const apiParamsMappingJson = ref('')
const fieldMappingJson = ref('')

const dataColumns = [
  { title: '父字段值', dataIndex: 'parent_value', key: 'parent_value' },
  { title: '子字段名', dataIndex: 'child_field_name', key: 'child_field_name' },
  { title: '子字段ID', dataIndex: 'child_field_id', key: 'child_field_id' },
  { title: '选项数', key: 'child_options', width: 100 },
  { title: '同步状态', key: 'sync_status', width: 120 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
]

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return '-'
  try {
    return new Date(dateStr).toLocaleString()
  } catch {
    return dateStr
  }
}

const fetchConfigList = async () => {
  listLoading.value = true
  try {
    const res: any = await api.getCascadeConfigList({})
    if (res.code === 200) {
      configList.value = res.data?.configs || []
    }
  } finally {
    listLoading.value = false
  }
}

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
    console.error('加载字段组失败', error)
  }
}

const fetchFields = async () => {
  try {
    const res: any = await api.getFieldSpecList({ page_size: 1000, field_type: 'select_single' })
    if (res.code === 200) {
      fieldOptions.value = (res.data || []).map((item: any) => ({
        label: `${item.field_label} (${item.field_name})`,
        value: item.id,
      }))
    }
  } catch (error) {
    console.error('加载字段失败', error)
  }
}

const handleParentFieldChange = async () => {
  if (formState.parent_field_id) {
    const res: any = await api.getFieldSpecById({ id: formState.parent_field_id })
    if (res.code === 200 && res.data) {
      if (res.data.field_groups && res.data.field_groups.length > 0) {
        formState.parent_field_group_id = res.data.field_groups[0].id
      }
    }
  }
}

const handleAdd = () => {
  selectedConfig.value = null
  resetForm()
}

const handleEdit = (item: any) => {
  selectedConfig.value = item
  formState.id = item.id
  formState.parent_field_id = item.parent_field_id
  formState.parent_field_group_id = item.parent_field_group_id
  formState.field_name_suffix = item.field_name_suffix
  formState.field_label_prefix = item.field_label_prefix || ''
  formState.api_curl = item.api_curl || ''
  formState.api_params_mapping = item.api_params_mapping || {}
  formState.field_mapping = item.field_mapping || {}
  formState.enable_flatten = item.enable_flatten || false
  formState.flatten_config = item.flatten_config || {}
  formState.is_active = item.is_active ?? true

  apiParamsMappingJson.value = JSON.stringify(formState.api_params_mapping, null, 2)
  fieldMappingJson.value = JSON.stringify(formState.field_mapping, null, 2)
  openapiSchema.value = item.api_schema || ''

  Object.assign(flattenConfig, formState.flatten_config)

  fetchCascadeData(item.id)
}

const handleDelete = async (item: any) => {
  try {
    const res: any = await api.deleteCascadeConfig({ config_id: item.id })
    if (res.code === 200) {
      message.success('删除成功')
      fetchConfigList()
      if (selectedConfig.value?.id === item.id) {
        selectedConfig.value = null
        resetForm()
      }
    } else {
      message.error(res.msg || '删除失败')
    }
  } catch (error: any) {
    message.error(error.message || '删除失败')
  }
}

const handleSave = async () => {
  if (!formState.parent_field_id) {
    message.warning('请选择父字段')
    return
  }
  if (!formState.parent_field_group_id) {
    message.warning('请选择父字段组')
    return
  }

  try {
    formState.api_params_mapping = JSON.parse(apiParamsMappingJson.value || '{}')
  } catch {
    message.error('API参数映射JSON格式错误')
    return
  }

  try {
    formState.field_mapping = JSON.parse(fieldMappingJson.value || '{}')
  } catch {
    message.error('字段映射JSON格式错误')
    return
  }

  formState.flatten_config = { ...flattenConfig }

  saveLoading.value = true
  try {
    const apiFunc = formState.id ? api.updateCascadeConfig : api.createCascadeConfig
    const payload: any = { ...formState }
    if (payload.id === undefined) delete payload.id

    // 添加 api_schema 到 payload
    if (openapiSchema.value) {
      payload.api_schema = openapiSchema.value
    }

    const res: any = await apiFunc(payload)
    if (res.code === 200) {
      message.success(formState.id ? '更新成功' : '创建成功')
      fetchConfigList()
    } else {
      message.error(res.msg || '保存失败')
    }
  } catch (error: any) {
    message.error(error.message || '保存失败')
  } finally {
    saveLoading.value = false
  }
}

const handleSync = async (item: any) => {
  syncLoading.value = true
  try {
    const res: any = await api.syncCascadeFields({ config_id: item.id })
    if (res.code === 200) {
      message.success(`同步成功: ${res.data?.synced_count || 0}/${res.data?.total_count || 0}`)
      fetchConfigList()
      if (selectedConfig.value?.id === item.id) {
        fetchCascadeData(item.id)
      }
    } else {
      message.error(res.msg || '同步失败')
    }
  } catch (error: any) {
    message.error(error.message || '同步失败')
  } finally {
    syncLoading.value = false
  }
}

const handleParseCurl = async () => {
  if (!formState.api_curl || !formState.api_curl.trim()) {
    message.warning('请输入curl命令')
    return
  }

  parseLoading.value = true
  try {
    const res: any = await api.parseCurlForCascade({
      curl_command: formState.api_curl,
      label_path: formState.field_mapping?.label_path || '$.data[*].label',
      value_path: formState.field_mapping?.value_path || '$.data[*].value',
      enable_flatten: formState.enable_flatten,
      flatten_config: formState.enable_flatten ? { ...flattenConfig } : undefined
    })

    if (res.code === 200) {
      openapiSchema.value = res.data?.openapi_schema || ''
      message.success('curl解析成功，已生成OpenAPI Schema')
    } else {
      message.error(res.msg || '解析失败')
    }
  } catch (error: any) {
    message.error(error.message || '解析失败')
  } finally {
    parseLoading.value = false
  }
}

const handleSyncFromSchema = async () => {
  if (!formState.id) {
    message.warning('请先保存配置')
    return
  }

  if (!openapiSchema.value) {
    message.warning('请先生成OpenAPI Schema')
    return
  }

  syncSchemaLoading.value = true
  try {
    const res: any = await api.syncCascadeFromSchema({
      config_id: formState.id,
      openapi_schema: openapiSchema.value,
      label_path: formState.field_mapping?.label_path || '$.data[*].label',
      value_path: formState.field_mapping?.value_path || '$.data[*].value',
      enable_flatten: formState.enable_flatten,
      flatten_config: formState.enable_flatten ? { ...flattenConfig } : undefined
    })

    if (res.code === 200) {
      message.success(`同步成功: ${res.data?.synced_count || 0}/${res.data?.total_count || 0}`)
      fetchConfigList()
      fetchCascadeData(formState.id)
    } else {
      message.error(res.msg || '同步失败')
    }
  } catch (error: any) {
    message.error(error.message || '同步失败')
  } finally {
    syncSchemaLoading.value = false
  }
}

const fetchCascadeData = async (configId: number) => {
  dataLoading.value = true
  try {
    const res: any = await api.getCascadeData({ config_id: configId })
    if (res.code === 200) {
      cascadeDataList.value = res.data?.cascade_data || []
    }
  } finally {
    dataLoading.value = false
  }
}

const resetForm = () => {
  formState.id = undefined
  formState.parent_field_id = undefined
  formState.parent_field_group_id = undefined
  formState.field_name_suffix = '-子字段'
  formState.field_label_prefix = ''
  formState.api_curl = ''
  formState.api_params_mapping = {}
  formState.field_mapping = {}
  formState.enable_flatten = false
  formState.flatten_config = {}
  formState.is_active = true

  apiParamsMappingJson.value = ''
  fieldMappingJson.value = ''
  openapiSchema.value = ''

  Object.assign(flattenConfig, {
    label_path_level1: '',
    label_path_level2: '',
    label_path_level3: '',
    label_separator: '-',
    value_path_level1: '',
    value_path_level2: '',
    value_path_level3: '',
    value_separator: '-',
  })

  cascadeDataList.value = []
}

const handleReset = () => {
  if (selectedConfig.value) {
    handleEdit(selectedConfig.value)
  } else {
    resetForm()
  }
}

onMounted(() => {
  fetchConfigList()
  fetchFieldGroups()
  fetchFields()
})
</script>

<style scoped lang="less">
.cascade-config-management {
  padding: 16px;
}
</style>
