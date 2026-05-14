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
            <template v-if="record.field_type === 'select_single'">
              <a-button type="link" size="small" @click="showCascadeConfig(record)">
                <LinkOutlined />
                级联配置
              </a-button>
            </template>
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

          <!-- API配置 -->
          <a-divider orientation="left">API配置</a-divider>

          <!-- Header配置 -->
          <a-form-item label="请求Header">
            <div v-for="(header, index) in form.options.api_headers" :key="index" class="header-item">
              <a-space>
                <a-input v-model:value="header.key" placeholder="Header键" style="width: 150px" />
                <a-input v-model:value="header.value" placeholder="Header值" style="width: 250px" />
                <a-button type="link" danger @click="removeApiHeader(index)">
                  <DeleteOutlined />
                </a-button>
              </a-space>
            </div>
            <a-button type="dashed" block @click="addApiHeader">
              <PlusOutlined />
              添加Header
            </a-button>
          </a-form-item>

          <!-- Schema配置 -->
          <a-form-item label="OpenAPI Schema">
            <a-textarea v-model:value="form.options.api_schema"
              placeholder="请输入OpenAPI/Swagger配置（YAML格式）&#10;&#10;支持以下扩展字段：&#10;1. x-api-params: 配置静态请求参数&#10;2. x-field-mapping: 配置字段映射（JSONPath语法）&#10;&#10;示例：&#10;paths:&#10;  /api/endpoint:&#10;    post:&#10;      x-api-params:&#10;        parent_id: 0&#10;        app_name: test_app&#10;        class_name: 400电话&#10;      x-field-mapping:&#10;        label_path: '$.data[*].summary'&#10;        value_path: '$.data[*].option_value'&#10;&#10;字段映射语法说明：&#10;  $.data[*].name     -> 从data数组中提取name字段&#10;  $.result[*].title  -> 从result数组中提取title字段&#10;  $.data[0].list[*]  -> 从data[0].list数组中提取元素&#10;&#10;默认映射（标准格式）：&#10;  label_path: '$.data[*].label'&#10;  value_path: '$.data[*].value'"
              :rows="15" />
          </a-form-item>

          <!-- 同步按钮 -->
          <a-form-item>
            <a-space>
              <a-button type="primary" :loading="syncLoading" @click="handleSyncOptions">
                <SyncOutlined />
                同步选项
              </a-button>
              <a-button @click="showCurlModal">
                <CodeOutlined />
                从 curl 导入
              </a-button>
            </a-space>
            <a-typography-text type="secondary" style="margin-left: 8px">
              根据Schema配置从API同步下拉选项
            </a-typography-text>
          </a-form-item>

          <!-- 级联配置 -->
          <a-divider orientation="left">级联配置</a-divider>
          <a-form-item>
            <a-button type="dashed" block @click="showAddCascadeModal">
              <PlusOutlined />
              添加级联子字段
            </a-button>
          </a-form-item>
          <a-form-item v-if="fieldCascadeConfigs.length > 0">
            <a-list :data-source="fieldCascadeConfigs" item-layout="horizontal" size="small">
              <template #renderItem="{ item }">
                <a-list-item :actions="[
                  <a-button type='link' size='small' @click='editCascadeConfig(item)'>编辑</a-button>,
                  <a-button type='link' size='small' :loading='item.syncing' @click='syncCascadeConfig(item)'>同步</a-button>,
                  <a-popconfirm title='确定删除该级联配置吗？' @confirm='deleteCascadeConfig(item)'>
                    <a-button type='link' danger size='small'>删除</a-button>
                  </a-popconfirm>
                ]">
                  <a-list-item-meta>
                    <template #title>{{ item.parent_field_name }}{{ item.field_name_suffix }}</template>
                    <template #description>
                      <a-tag color="blue">后缀: {{ item.field_name_suffix }}</a-tag>
                      <a-tag :color="item.is_active ? 'green' : 'red'">
                        {{ item.is_active ? '启用' : '禁用' }}
                      </a-tag>
                      <br>
                      <span v-if="item.last_sync_at">
                        最后同步: {{ formatDateTime(item.last_sync_at) }}
                      </span>
                    </template>
                  </a-list-item-meta>
                </a-list-item>
              </template>
            </a-list>
          </a-form-item>

          <a-divider orientation="left">选项列表</a-divider>

          <a-form-item label="选项列表">
            <a-typography-text type="secondary" style="margin-bottom: 8px; display: block;">
              使用 Markdown 格式编辑选项，格式示例：<br>
              <code>## 选项标签</code> - 选项标题（人工识别）<br>
              <code>- 选项值:</code> 选项值（ID等）<br>
              <code>- 填写说明:</code> 填写说明内容<br>
              <code>- 批注:</code> 人工标注内容（可多个）
            </a-typography-text>
            <a-textarea v-model:value="optionsMarkdown" :rows="20"
              placeholder="## 智能网联&#10;- 选项值: 1001&#10;- 填写说明: 选择云控相关问题&#10;- 批注: 这是批注内容1&#10;- 批注: 这是批注内容2&#10;&#10;## 产品咨询&#10;- 选项值: 1002&#10;- 填写说明: 选择产品咨询类问题"
              @blur="parseMarkdownToOptions" />
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

    <!-- curl 解析弹窗 -->
    <a-modal v-model:open="curlModalVisible" title="从 curl 命令导入 OpenAPI Schema" :confirm-loading="curlModalLoading"
      @ok="handleParseCurl" @cancel="handleCancelCurlModal" width="900px">
      <a-form layout="vertical">
        <a-form-item label="curl 命令" required>
          <a-textarea v-model:value="curlForm.curl_command"
            placeholder="请输入 curl 命令，例如：&#10;curl -X POST http://localhost:9999/api/autofill/dropdown_options/list \\&#10;  -H 'Authorization: Bearer your_token' \\&#10;  -H 'Content-Type: application/json' \\&#10;  -d '{&quot;parent_id&quot;: 0}'"
            :rows="6" />
        </a-form-item>
        <a-form-item label="标签字段 JSONPath">
          <a-input v-model:value="curlForm.label_path" placeholder="$.data[*].label" />
          <a-typography-text type="secondary">
            用于从响应中提取选项标签的 JSONPath 表达式
          </a-typography-text>
        </a-form-item>
        <a-form-item label="值字段 JSONPath">
          <a-input v-model:value="curlForm.value_path" placeholder="$.data[*].value" />
          <a-typography-text type="secondary">
            用于从响应中提取选项值的 JSONPath 表达式
          </a-typography-text>
        </a-form-item>

        <a-divider orientation="left">展平配置 (可选)</a-divider>
        <a-form-item label="启用展平">
          <a-switch v-model:checked="curlForm.enable_flatten" />
        </a-form-item>
        <template v-if="curlForm.enable_flatten">
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="标签路径1">
                <a-input v-model:value="curlForm.flatten_label_path1" placeholder="$.data[*].label" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="标签路径2">
                <a-input v-model:value="curlForm.flatten_label_path2" placeholder="$.children[*].label" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="标签路径3">
                <a-input v-model:value="curlForm.flatten_label_path3" placeholder="" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="标签分隔符">
                <a-input v-model:value="curlForm.flatten_label_separator" placeholder="-" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="值路径1">
                <a-input v-model:value="curlForm.flatten_value_path1" placeholder="$.data[*].value" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="值路径2">
                <a-input v-model:value="curlForm.flatten_value_path2" placeholder="$.children[*].value" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="值路径3">
                <a-input v-model:value="curlForm.flatten_value_path3" placeholder="" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="值分隔符">
                <a-input v-model:value="curlForm.flatten_value_separator" placeholder="-" />
              </a-form-item>
            </a-col>
          </a-row>
        </template>
      </a-form>
    </a-modal>

    <!-- 级联配置弹窗 -->
    <a-modal v-model:open="cascadeModalVisible" title="级联子字段配置" :confirm-loading="cascadeModalLoading"
      @ok="handleSaveCascadeConfig" @cancel="handleCancelCascadeModal" width="900px">
      <a-form layout="vertical">
        <a-form-item label="字段名后缀">
          <a-input v-model:value="cascadeConfig.field_name_suffix" placeholder="-子字段" />
        </a-form-item>
        <a-form-item label="字段标签前缀">
          <a-input v-model:value="cascadeConfig.field_label_prefix" placeholder="" />
        </a-form-item>
        <a-form-item label="curl命令 (获取子选项)" required>
          <a-textarea v-model:value="cascadeConfig.api_curl"
            placeholder="请输入curl命令，参数使用 {parent_value} 占位符，例如：&#10;curl 'https://api.example.com/getChild?parentId={parent_value}' -H 'Authorization: Bearer xxx'"
            :rows="6" />
        </a-form-item>
        <a-form-item label="API参数映射">
          <a-textarea v-model:value="cascadeParamsMappingJson" placeholder='{"parentEventId": "{parent_value}"}' :rows="3" />
          <a-typography-text type="secondary">
            使用 {parent_value} 表示父字段值的占位符
          </a-typography-text>
        </a-form-item>
        <a-form-item label="字段映射">
          <a-textarea v-model:value="cascadeFieldMappingJson" placeholder='{"label_path": "$.data[*].label", "value_path": "$.data[*].value"}'
            :rows="3" />
        </a-form-item>

        <a-divider orientation="left">展平配置 (可选)</a-divider>
        <a-form-item label="启用展平">
          <a-switch v-model:checked="cascadeConfig.enable_flatten" />
        </a-form-item>
        <template v-if="cascadeConfig.enable_flatten">
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="标签路径1">
                <a-input v-model:value="cascadeFlattenConfig.label_path_level1" placeholder="$.data[*].label" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="标签路径2">
                <a-input v-model:value="cascadeFlattenConfig.label_path_level2" placeholder="$.children[*].label" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="标签路径3">
                <a-input v-model:value="cascadeFlattenConfig.label_path_level3" placeholder="" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="标签分隔符">
                <a-input v-model:value="cascadeFlattenConfig.label_separator" placeholder="-" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="值路径1">
                <a-input v-model:value="cascadeFlattenConfig.value_path_level1" placeholder="$.data[*].value" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="值路径2">
                <a-input v-model:value="cascadeFlattenConfig.value_path_level2" placeholder="$.children[*].value" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="值路径3">
                <a-input v-model:value="cascadeFlattenConfig.value_path_level3" placeholder="" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="值分隔符">
                <a-input v-model:value="cascadeFlattenConfig.value_separator" placeholder="-" />
              </a-form-item>
            </a-col>
          </a-row>
        </template>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { useUserStore } from '@/store'
import { formatDateTime } from '@/utils'
import { CodeOutlined, DeleteOutlined, ExportOutlined, ImportOutlined, PlusOutlined, SyncOutlined, LinkOutlined } from '@ant-design/icons-vue'
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
const syncLoading = ref(false)

// curl 解析弹窗数据
const curlModalVisible = ref(false)
const curlModalLoading = ref(false)
const curlForm = reactive({
  curl_command: '',
  label_path: '$.data[*].label',
  value_path: '$.data[*].value',
  enable_flatten: false,
  flatten_label_path1: '',
  flatten_label_path2: '',
  flatten_label_path3: '',
  flatten_label_separator: '-',
  flatten_value_path1: '',
  flatten_value_path2: '',
  flatten_value_path3: '',
  flatten_value_separator: '-',
})

// 级联配置弹窗数据
const cascadeModalVisible = ref(false)
const cascadeModalLoading = ref(false)
const cascadeConfig = reactive({
  parent_field_id: undefined as number | undefined,
  parent_field_group_id: undefined as number | undefined,
  field_name_suffix: '-子字段',
  field_label_prefix: '',
  api_curl: '',
  api_params_mapping: {} as any,
  field_mapping: {} as any,
  enable_flatten: false,
  flatten_config: {} as any,
})
const cascadeParamsMappingJson = ref('')
const cascadeFieldMappingJson = ref('')
const cascadeFlattenConfig = reactive({
  label_path_level1: '',
  label_path_level2: '',
  label_path_level3: '',
  label_separator: '-',
  value_path_level1: '',
  value_path_level2: '',
  value_path_level3: '',
  value_separator: '-',
})

// 当前字段关联的级联配置
const fieldCascadeConfigs = ref<any[]>([])

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
    api_headers: [] as { key: string; value: string }[],
    api_schema: '',
  },
  corrections: [] as any[],
  is_active: true,
})

// Markdown 格式的选项列表
const optionsMarkdown = ref('')

// 将选项数据转换为 Markdown 格式
const convertOptionsToMarkdown = (items: any[]): string => {
  if (!items || items.length === 0) return ''

  return items.map((item, index) => {
    const lines: string[] = []

    // 选项标签作为二级标题（人工识别）
    lines.push(`## ${item.label || ''}`)

    // 选项值
    if (item.value) {
      lines.push(`- 选项值: ${item.value}`)
    }

    // 填写说明
    if (item.fill_instruction) {
      lines.push(`- 填写说明: ${item.fill_instruction}`)
    }

    // 人工标注（可能有多个）
    if (item.corrections && item.corrections.length > 0) {
      item.corrections.forEach((corr: any) => {
        if (corr.text) {
          lines.push(`- 批注: ${corr.text}`)
        }
      })
    }

    // 选项之间添加空行（最后一个除外）
    if (index < items.length - 1) {
      lines.push('')
    }

    return lines.join('\n')
  }).join('\n')
}

// 将 Markdown 格式解析为选项数据
const parseMarkdownToOptions = () => {
  const markdown = optionsMarkdown.value.trim()
  if (!markdown) {
    modalForm.options.items = []
    return
  }

  const items: any[] = []
  const lines = markdown.split('\n')
  let currentItem: any = null

  for (const line of lines) {
    const trimmedLine = line.trim()
    if (!trimmedLine) continue

    // 匹配二级标题 ## 选项标签
    const headerMatch = trimmedLine.match(/^##\s*(.+)$/)
    if (headerMatch) {
      // 保存上一个选项
      if (currentItem) {
        items.push(currentItem)
      }
      // 创建新选项
      currentItem = {
        label: headerMatch[1].trim(),
        value: '',
        fill_instruction: '',
        corrections: [],
        is_deleted: false,
      }
      continue
    }

    // 如果没有当前选项，跳过
    if (!currentItem) continue

    // 匹配 - 选项值: xxx
    const valueMatch = trimmedLine.match(/^-\s*选项值[:：]\s*(.*)$/i)
    if (valueMatch) {
      currentItem.value = valueMatch[1].trim()
      continue
    }

    // 匹配 - 填写说明: xxx
    const instructionMatch = trimmedLine.match(/^-\s*填写说明[:：]\s*(.*)$/i)
    if (instructionMatch) {
      currentItem.fill_instruction = instructionMatch[1].trim()
      continue
    }

    // 匹配 - 批注: xxx
    const correctionMatch = trimmedLine.match(/^-\s*批注[:：]\s*(.*)$/i)
    if (correctionMatch) {
      currentItem.corrections.push({
        text: correctionMatch[1].trim(),
      })
      continue
    }
  }

  // 保存最后一个选项
  if (currentItem) {
    items.push(currentItem)
  }

  modalForm.options.items = items
}

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
    { max: 50, message: '字段名最多50个字符', trigger: 'blur' },
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
    api_headers: [],
    api_schema: '',
  }
  modalForm.corrections = []
  modalForm.is_active = true
  optionsMarkdown.value = ''
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
    api_headers: record.options?.api_headers || [],
    api_schema: record.options?.api_schema || '',
  }
  modalForm.is_active = record.is_active
  // 将选项数据转换为 Markdown 格式
  optionsMarkdown.value = convertOptionsToMarkdown(record.options?.items || [])
  crudTableRef.value?.openEditModal(record)
  // 确保 corrections 是数组，避免 null 导致的问题（必须在 openEditModal 之后执行，因为 openEditModal 内部会 Object.assign 覆盖值）
  // 由于 Object.assign 会将 null 直接赋值给 corrections，我们需要重新赋值为数组
  const corrections = Array.isArray(record.corrections) ? record.corrections : []
  ; (modalForm as any).corrections = [...corrections]
  
  // 加载级联配置
  if (record.field_type === 'select_single' && record.id) {
    fetchFieldCascadeConfigs(record.id)
  } else {
    fieldCascadeConfigs.value = []
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

// API Header 相关方法
const addApiHeader = () => {
  if (!modalForm.options.api_headers) {
    modalForm.options.api_headers = []
  }
  modalForm.options.api_headers.push({ key: '', value: '' })
}

const removeApiHeader = (index: number) => {
  if (modalForm.options.api_headers) {
    modalForm.options.api_headers.splice(index, 1)
  }
}

// 同步选项方法
const handleSyncOptions = async () => {
  if (!modalForm.options.api_schema) {
    message.warning('请先配置OpenAPI Schema')
    return
  }

  // 验证必填字段
  if (!modalForm.field_name) {
    message.warning('请先填写字段名称')
    return
  }
  if (!modalForm.field_label) {
    message.warning('请先填写字段标签')
    return
  }
  if (!modalForm.field_group_ids || modalForm.field_group_ids.length === 0) {
    message.warning('请至少选择一个关联字段组')
    return
  }

  syncLoading.value = true
  try {
    const res: any = await api.syncFieldSpecOptions({
      field_id: modalForm.id,
      field_name: modalForm.field_name,
      field_label: modalForm.field_label,
      field_type: modalForm.field_type,
      field_group_ids: modalForm.field_group_ids,
      fill_instruction: modalForm.fill_instruction || '',
      options: modalForm.options,
    })
    if (res.code === 200) {
      // 更新选项列表
      modalForm.options.items = res.data.items || []
      // 同步成功后，将选项数据转换为 Markdown 格式
      optionsMarkdown.value = convertOptionsToMarkdown(res.data.items || [])
      // 更新字段ID（如果是新建）
      if (res.data.field_id && !modalForm.id) {
        modalForm.id = res.data.field_id
      }
      message.success(`同步成功，共更新 ${res.data.updated_count || 0} 个选项`)
    } else {
      message.error(res.msg || '同步失败')
    }
  } catch (error: any) {
    message.error(error.message || '同步失败')
  } finally {
    syncLoading.value = false
  }
}

// curl 解析相关方法
const showCurlModal = () => {
  curlForm.curl_command = ''
  curlForm.label_path = '$.data[*].label'
  curlForm.value_path = '$.data[*].value'
  curlModalVisible.value = true
}

const handleParseCurl = async () => {
  if (!curlForm.curl_command.trim()) {
    message.warning('请输入 curl 命令')
    return
  }

  curlModalLoading.value = true
  try {
    const res: any = await api.parseCurlCommand({
      curl_command: curlForm.curl_command,
      label_path: curlForm.label_path,
      value_path: curlForm.value_path,
    })
    if (res.code === 200) {
      // 将生成的 Schema 填入表单
      modalForm.options.api_schema = res.data.openapi_schema
      message.success(res.data.message || 'curl 解析成功，已生成 OpenAPI Schema')
      curlModalVisible.value = false
    } else {
      message.error(res.msg || '解析失败')
    }
  } catch (error: any) {
    message.error(error.message || '解析失败')
  } finally {
    curlModalLoading.value = false
  }
}

const handleCancelCurlModal = () => {
  curlModalVisible.value = false
}

const handleSave = async () => {
  modalLoading.value = true
  try {
    // 先将 Markdown 解析为选项数据
    parseMarkdownToOptions()

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
      base_file: file
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

// 级联配置相关方法
const showCascadeConfig = async (record: any) => {
  modalForm.id = record.id
  modalForm.field_name = record.field_name
  await fetchFieldCascadeConfigs(record.id)
  crudTableRef.value?.openEditModal(record)
}

const fetchFieldCascadeConfigs = async (fieldId: number) => {
  try {
    const res: any = await api.getCascadeConfigList({ parent_field_id: fieldId })
    if (res.code === 200) {
      fieldCascadeConfigs.value = res.data?.configs || []
    }
  } catch (error) {
    console.error('获取级联配置失败', error)
    fieldCascadeConfigs.value = []
  }
}

const showAddCascadeModal = () => {
  if (!modalForm.id) {
    message.warning('请先保存字段后再添加级联配置')
    return
  }
  resetCascadeConfig()
  cascadeConfig.parent_field_id = modalForm.id
  cascadeConfig.parent_field_group_id = modalForm.field_group_ids?.[0]
  cascadeModalVisible.value = true
}

const editCascadeConfig = (item: any) => {
  cascadeConfig.parent_field_id = item.parent_field_id
  cascadeConfig.parent_field_group_id = item.parent_field_group_id
  cascadeConfig.field_name_suffix = item.field_name_suffix
  cascadeConfig.field_label_prefix = item.field_label_prefix || ''
  cascadeConfig.api_curl = item.api_curl || ''
  cascadeConfig.api_params_mapping = item.api_params_mapping || {}
  cascadeConfig.field_mapping = item.field_mapping || {}
  cascadeConfig.enable_flatten = item.enable_flatten || false
  cascadeConfig.flatten_config = item.flatten_config || {}
  cascadeConfig.id = item.id

  cascadeParamsMappingJson.value = JSON.stringify(cascadeConfig.api_params_mapping, null, 2)
  cascadeFieldMappingJson.value = JSON.stringify(cascadeConfig.field_mapping, null, 2)

  Object.assign(cascadeFlattenConfig, item.flatten_config || {})
  cascadeModalVisible.value = true
}

const resetCascadeConfig = () => {
  cascadeConfig.parent_field_id = undefined
  cascadeConfig.parent_field_group_id = undefined
  cascadeConfig.field_name_suffix = '-子字段'
  cascadeConfig.field_label_prefix = ''
  cascadeConfig.api_curl = ''
  cascadeConfig.api_params_mapping = {}
  cascadeConfig.field_mapping = {}
  cascadeConfig.enable_flatten = false
  cascadeConfig.flatten_config = {}
  cascadeConfig.id = undefined

  cascadeParamsMappingJson.value = ''
  cascadeFieldMappingJson.value = ''

  Object.assign(cascadeFlattenConfig, {
    label_path_level1: '',
    label_path_level2: '',
    label_path_level3: '',
    label_separator: '-',
    value_path_level1: '',
    value_path_level2: '',
    value_path_level3: '',
    value_separator: '-',
  })
}

const handleSaveCascadeConfig = async () => {
  if (!cascadeConfig.api_curl) {
    message.warning('请输入curl命令')
    return
  }

  try {
    cascadeConfig.api_params_mapping = JSON.parse(cascadeParamsMappingJson.value || '{}')
  } catch {
    message.error('API参数映射JSON格式错误')
    return
  }

  try {
    cascadeConfig.field_mapping = JSON.parse(cascadeFieldMappingJson.value || '{}')
  } catch {
    message.error('字段映射JSON格式错误')
    return
  }

  cascadeConfig.flatten_config = { ...cascadeFlattenConfig }

  cascadeModalLoading.value = true
  try {
    const apiFunc = cascadeConfig.id ? api.updateCascadeConfig : api.createCascadeConfig
    const res: any = await apiFunc({ ...cascadeConfig })
    if (res.code === 200) {
      message.success('保存成功')
      cascadeModalVisible.value = false
      if (cascadeConfig.parent_field_id) {
        await fetchFieldCascadeConfigs(cascadeConfig.parent_field_id)
      }
    } else {
      message.error(res.msg || '保存失败')
    }
  } catch (error: any) {
    message.error(error.message || '保存失败')
  } finally {
    cascadeModalLoading.value = false
  }
}

const handleCancelCascadeModal = () => {
  cascadeModalVisible.value = false
}

const syncCascadeConfig = async (item: any) => {
  item.syncing = true
  try {
    const res: any = await api.syncCascadeFields({ config_id: item.id })
    if (res.code === 200) {
      message.success(`同步成功: ${res.data?.synced_count || 0}/${res.data?.total_count || 0}`)
      if (cascadeConfig.parent_field_id) {
        await fetchFieldCascadeConfigs(cascadeConfig.parent_field_id)
      }
    } else {
      message.error(res.msg || '同步失败')
    }
  } catch (error: any) {
    message.error(error.message || '同步失败')
  } finally {
    item.syncing = false
  }
}

const deleteCascadeConfig = async (item: any) => {
  try {
    const res: any = await api.deleteCascadeConfig({ config_id: item.id })
    if (res.code === 200) {
      message.success('删除成功')
      if (cascadeConfig.parent_field_id) {
        await fetchFieldCascadeConfigs(cascadeConfig.parent_field_id)
      }
    } else {
      message.error(res.msg || '删除失败')
    }
  } catch (error: any) {
    message.error(error.message || '删除失败')
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
  .correction-item,
  .header-item {
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
