<template>
  <div class="curl-import">
    <!-- CURL配置区域 -->
    <div class="config-section">
      <div class="config-toolbar">
        <a-space>
          <a-button type="primary" @click="handlePreview">
            <EyeOutlined />
            预览数据
          </a-button>
          <a-button @click="loadDefaultConfig">
            <ReloadOutlined />
            加载示例配置
          </a-button>
        </a-space>
      </div>

      <!-- JSON编辑器 -->
      <div class="editor-wrapper">
        <JsonEditor
          v-model="curlConfig"
          title="CURL导入配置 (JSON格式)"
          placeholder="请输入CURL导入配置..."
          @change="handleConfigChange"
        />
      </div>

      <!-- 配置说明 -->
      <a-collapse class="config-help">
        <a-collapse-panel key="1" header="配置说明">
          <div class="help-content">
            <h4>配置结构说明：</h4>
            <ul>
              <li><code>global_vars</code>: 全局变量，用于替换CURL命令中的占位符</li>
              <li><code>data_root_path</code>: 数据根路径，如 $.data</li>
              <li><code>curl_commands</code>: CURL命令列表（支持多个级联请求）</li>
              <li><code>level_config</code>: 层级配置，定义每个层级的字段映射</li>
            </ul>
            <h4>层级配置说明：</h4>
            <ul>
              <li><code>source</code>: 数据源配置 (type: request/children)</li>
              <li><code>fields</code>: 字段映射列表 (csv_header, jsonpath)</li>
              <li><code>children_jsonpath</code>: 子节点JSONPath</li>
              <li><code>params</code>: 请求参数映射</li>
            </ul>
          </div>
        </a-collapse-panel>
      </a-collapse>
    </div>

    <!-- 预览数据区域 -->
    <div v-if="previewData.headers?.length" class="preview-section">
      <a-divider>数据预览（前5行）</a-divider>
      <div class="preview-table-wrapper">
        <a-table
          :columns="previewColumns"
          :data-source="previewDataSource"
          :pagination="false"
          size="small"
          bordered
          :scroll="{ x: 'max-content' }"
        />
      </div>
      <p class="row-count">共 {{ previewData.row_count }} 行数据</p>
    </div>

    <!-- 字段兼容性说明 -->
    <div v-if="previewData.headers?.length" class="compatibility-section">
      <a-divider>字段兼容性</a-divider>
      <div class="compatibility-info">
        <p><strong>CURL获取表头：</strong>{{ previewData.headers.join(', ') }}</p>
        <p v-if="!isFirstImport && existingHeaders?.length"><strong>现有表头：</strong>{{ existingHeaders?.join(', ') }}</p>
        <a-alert type="info" show-icon :message="compatibilityMessage" />
      </div>
    </div>

    <!-- 操作按钮 -->
    <div v-if="previewData.headers?.length" class="action-buttons">
      <a-space>
        <a-button type="primary" :loading="importing" @click="handleImport" :disabled="!primaryKeys?.length">
          执行导入
        </a-button>
      </a-space>
    </div>

    <!-- 导入结果弹窗 -->
    <a-modal v-model:open="importResultVisible" title="导入结果" @ok="importResultVisible = false"
      :cancel-button-props="{ style: { display: 'none' } }">
      <a-descriptions :column="1" bordered>
        <a-descriptions-item label="新增行数">{{ importResult.added_count }}</a-descriptions-item>
        <a-descriptions-item label="更新行数">{{ importResult.updated_count }}</a-descriptions-item>
        <a-descriptions-item label="忽略行数">{{ importResult.skipped_count }}</a-descriptions-item>
        <a-descriptions-item label="失败行数">{{ importResult.failed_count }}</a-descriptions-item>
        <a-descriptions-item label="总行数">{{ importResult.total_count }}</a-descriptions-item>
        <a-descriptions-item label="新版本号">v{{ importResult.version_no }}</a-descriptions-item>
      </a-descriptions>
      <div v-if="importResult.failed_reasons?.length" class="failed-reasons">
        <a-divider>失败原因</a-divider>
        <a-list size="small" :data-source="importResult.failed_reasons">
          <template #renderItem="{ item }">
            <a-list-item>
              <span style="color: #ff4d4f;">第{{ item.row }}行: {{ item.reason }}</span>
            </a-list-item>
          </template>
        </a-list>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import JsonEditor from '@/components/JsonEditor/index.vue'
import { useUserStore } from '@/store'
import { EyeOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { message, Modal } from 'ant-design-vue'
import { computed, onMounted, ref, watch } from 'vue'

const userStore = useUserStore()

const props = defineProps<{
  ruleId?: number
  ruleCode?: string
  ruleName?: string
  tenantId?: number
  existingHeaders?: string[]
  primaryKeys?: string[]
  syncFields?: string[]
}>()

const emit = defineEmits<{
  preview: [data: any]
  imported: [data: any]
}>()

// 默认配置示例
const defaultConfig = {
  description: '事件类型单请求树形结构导入',
  global_vars: {
    API_KEY: 'your_api_key',
    BASE_URL: 'http://localhost:9999',
    CLASS_NAME: '事件类型',
    TOKEN: 'your_token'
  },
  data_root_path: '$.data',
  level_config: {
    level1: {
      source: { type: 'request', index: 0 },
      fields: [
        { csv_header: 'level1', jsonpath: '$.option_value' },
        { csv_header: 'level1_summary', jsonpath: '$.summary' },
        { csv_header: 'level1_id', jsonpath: '$.id' },
        { csv_header: 'level1_code', jsonpath: '$.code' }
      ],
      children_jsonpath: '$.children',
      params: {}
    },
    level2: {
      source: { type: 'children', from_level: 'level1' },
      fields: [
        { csv_header: 'level2', jsonpath: '$.option_value' },
        { csv_header: 'level2_summary', jsonpath: '$.summary' },
        { csv_header: 'level2_id', jsonpath: '$.id' }
      ],
      children_jsonpath: '$.children',
      params: {}
    },
    level3: {
      source: { type: 'children', from_level: 'level2' },
      fields: [
        { csv_header: 'level3', jsonpath: '$.option_value' },
        { csv_header: 'level3_summary', jsonpath: '$.summary' }
      ],
      children_jsonpath: null,
      params: {}
    }
  },
  curl_commands: [
    "curl 'http://localhost:3200/api/v1/autofill/dropdown/tree?app_name=test_app&class_name=%E4%BA%8B%E4%BB%B6%E7%B1%BB%E5%9E%8B' \\n   -H 'Accept: application/json, text/plain, */*' \\n   -H 'token: {TOKEN}'"
  ]
}

// 状态
const curlConfig = ref<any>(null)
const previewData = ref<any>({
  headers: [],
  data: [],
  row_count: 0,
  mode: 'single',
  preview_data: []
})
const importing = ref(false)
const currentMd5 = ref('')
const isFirstImport = ref(true)
const importResultVisible = ref(false)
const importResult = ref<any>({})

// 预览表格列
const previewColumns = computed(() => {
  return previewData.value.headers?.map((h: string) => ({
    title: h,
    dataIndex: h,
    key: h,
    width: 150,
    ellipsis: true
  })) || []
})

// 预览数据源
const previewDataSource = computed(() => {
  return previewData.value.preview_data?.map((row: any, index: number) => {
    const obj: any = { key: index }
    previewData.value.headers?.forEach((h: string, i: number) => {
      obj[h] = row[i] || ''
    })
    return obj
  }) || []
})

// 兼容性提示信息
const compatibilityMessage = computed(() => {
  if (isFirstImport.value) {
    return '首次导入：将使用CURL获取的表头作为新表头'
  }
  const curlHeaders = previewData.value.headers || []
  const existing = props.existingHeaders || []
  const newFields = curlHeaders.filter((h: string) => !existing.includes(h))
  const commonFields = curlHeaders.filter((h: string) => existing.includes(h))

  if (newFields.length > 0) {
    return `字段兼容性：${commonFields.length}个共有字段，${newFields.length}个新字段(${newFields.join(', ')})将被自动添加`
  }
  return `字段兼容性：${commonFields.length}个字段完全匹配`
})

// 加载默认配置
const loadDefaultConfig = () => {
  curlConfig.value = JSON.parse(JSON.stringify(defaultConfig))
  message.success('已加载示例配置')
}

// 配置变化
const handleConfigChange = (value: any) => {
  curlConfig.value = value
}

// 预览数据
const handlePreview = async () => {
  if (!props.ruleId) {
    message.error('规则ID不能为空')
    return
  }

  const config = curlConfig.value || {}

  try {
    const res: any = await api.previewCurlImport({
      rule_id: props.ruleId,
      tenant_id: props.tenantId,
      curl_config: config
    })

    if (res.code === 200) {
      previewData.value = res.data
      isFirstImport.value = res.data.is_first_import || false
      message.success(`预览成功，共 ${res.data.row_count} 行数据`)

      // 自动保存CURL配置到config字段
      await autoSaveCurlConfig()

      // 触发预览事件，通知父组件更新表头
      emit('preview', {
        headers: res.data.headers || [],
        is_first_import: res.data.is_first_import || false
      })
    } else {
      message.error(res.msg || '预览失败')
    }
  } catch (error) {
    console.error('预览失败', error)
    message.error('预览失败')
  }
}

// 自动保存CURL配置
const autoSaveCurlConfig = async () => {
  if (!props.ruleId) return

  try {
    const config = curlConfig.value || {}
    await api.saveCurlImportConfig({
      rule_id: props.ruleId,
      tenant_id: props.tenantId,
      curl_config: config
    })
    // 不显示成功消息，静默保存
  } catch (error) {
    console.error('自动保存CURL配置失败', error)
  }
}

// 执行导入
const handleImport = async () => {
  if (!props.ruleId) {
    message.error('规则ID不能为空')
    return
  }

  if (!props.primaryKeys || props.primaryKeys.length === 0) {
    message.error('请先在上方配置主键字段')
    return
  }

  Modal.confirm({
    title: '确认导入',
    content: isFirstImport.value
      ? '首次导入将清空原有数据并全量导入新数据，确定继续吗？'
      : '将根据主键配置进行增量更新，确定继续吗？',
    onOk: async () => {
      importing.value = true
      try {
        // 执行CURL导入，后端会生成临时文件并走文件导入流程
        const res: any = await api.applyCurlImport({
          rule_id: props.ruleId,
          tenant_id: props.tenantId,
          current_md5: currentMd5.value,
          primary_keys: props.primaryKeys,
          sync_fields: props.syncFields || [],
          curl_config: curlConfig.value
        })

        if (res.code === 200) {
          importResult.value = res.data
          importResultVisible.value = true
          message.success('导入成功！')
          emit('imported', res.data)
        } else {
          message.error(res.msg || '导入失败')
        }
      } catch (error) {
        console.error('导入失败', error)
        message.error('导入失败')
      } finally {
        importing.value = false
      }
    }
  })
}

// 获取当前规则版本的 MD5
const loadCurrentVersion = async () => {
  if (!props.ruleId) return

  try {
    const res: any = await api.getRuleVersions({
      rule_id: props.ruleId,
      tenant_id: props.tenantId,
      page: 1,
      page_size: 1
    })

    if (res.code === 200 && res.data && res.data.length > 0) {
      currentMd5.value = res.data[0].content_md5 || ''
      isFirstImport.value = false
    } else {
      isFirstImport.value = true
    }
  } catch (error) {
    console.error('加载当前版本失败', error)
    isFirstImport.value = true
  }
}

// 获取已保存的CURL配置
const loadSavedConfig = async () => {
  if (!props.ruleId) return

  try {
    const res: any = await api.getCurlImportConfig({
      rule_id: props.ruleId,
      tenant_id: props.tenantId
    })

    if (res.code === 200 && res.data) {
      if (res.data.curl_config && Object.keys(res.data.curl_config).length > 0) {
        curlConfig.value = res.data.curl_config
      }
    }
  } catch (error) {
    console.error('加载配置失败', error)
  }
}

// 组件挂载时加载配置和当前版本
onMounted(() => {
  loadSavedConfig()
  loadCurrentVersion()
})
</script>

<style scoped lang="less">
.curl-import {
  .config-section {
    .config-toolbar {
      margin-bottom: 16px;
    }

    .editor-wrapper {
      margin-bottom: 16px;
    }

    .config-help {
      margin-top: 16px;

      .help-content {
        h4 {
          margin-top: 12px;
          margin-bottom: 8px;
        }

        ul {
          padding-left: 20px;

          li {
            margin-bottom: 4px;
          }
        }

        code {
          background: #f6f8fa;
          padding: 2px 6px;
          border-radius: 3px;
          font-family: monospace;
        }
      }
    }
  }

  .preview-section {
    margin-top: 16px;
    margin-bottom: 16px;

    .preview-table-wrapper {
      max-width: 100%;
      overflow-x: auto;
    }

    .row-count {
      color: #666;
      margin-top: 8px;
    }
  }

  .compatibility-section {
    margin-bottom: 16px;

    .compatibility-info {
      p {
        margin-bottom: 8px;
      }
    }
  }

  .action-buttons {
    margin-top: 24px;
    text-align: right;
    border-top: 1px solid #f0f0f0;
    padding-top: 16px;
  }

  .failed-reasons {
    margin-top: 16px;
  }
}
</style>
