<template>
  <div class="excel-csv-editor">
    <!-- 工具栏 -->
    <div class="toolbar">
      <a-space>
        <a-button type="primary" @click="handleSave">
          <SaveOutlined />
          保存版本
        </a-button>
        <a-button @click="handleImport">
          <ImportOutlined />
          导入CSV
        </a-button>
        <a-button @click="handleExport">
          <ExportOutlined />
          导出CSV
        </a-button>
        <a-button @click="showVersionHistory">
          <HistoryOutlined />
          版本历史
        </a-button>
        <a-divider type="vertical" />
        <a-input-search v-model:value="searchQuery" placeholder="搜索表格内容..." style="width: 200px" size="small"
          @search="handleSearch" @change="handleSearch" />
        <a-button v-if="searchQuery" size="small" @click="clearSearch">
          清除搜索
        </a-button>
      </a-space>
      <a-space v-if="currentVersion">
        <a-tag color="blue">版本: v{{ currentVersion.version_no }}</a-tag>
        <span v-if="currentVersion.created_at" class="version-time">
          {{ currentVersion.created_at }}
        </span>
      </a-space>
    </div>

    <!-- Handsontable 表格 -->
    <div class="table-container">
      <hot-table ref="hotTableRef" :data="tableData" :col-headers="headers" :row-headers="true" :height="500"
        :width="'100%'" :license-key="'non-commercial-and-evaluation'" :context-menu="contextMenuItems"
        :manual-column-move="true" :manual-row-move="true" :manual-column-resize="true" :manual-row-resize="true"
        :filters="true" :dropdown-menu="filtersDropdownMenu" :copy-paste="true" :fill-handle="true"
        :multi-column-sorting="true" :auto-wrap-row="true" :auto-wrap-col="true" :enter-moves="{ row: 1, col: 0 }"
        :tab-moves="{ row: 0, col: 1 }" stretch-h="all" class="handsontable-wrapper" :search="true"
        @after-change="onDataChange" @after-column-sort="onColumnSort" @after-on-cell-mouse-down="onCellMouseDown" />
    </div>

    <!-- 快捷操作提示 -->
    <div class="shortcuts">
      <a-alert type="info" show-icon :message="'Excel式操作: 拖拽填充、复制粘贴、右键菜单、列拖拽排序、双击编辑'" />
    </div>

    <!-- 保存版本弹窗 -->
    <a-modal v-model:open="saveModalVisible" title="保存新版本" @ok="confirmSave" @cancel="saveModalVisible = false">
      <a-form :model="saveForm" layout="vertical">
        <a-form-item label="版本备注">
          <a-textarea v-model:value="saveForm.remark" placeholder="请输入本次修改的备注说明" :rows="3" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 版本历史弹窗 -->
    <a-modal v-model:open="versionModalVisible" title="版本历史" width="800px" :footer="null">
      <a-table :columns="versionColumns" :data-source="versionList" :pagination="{ pageSize: 10 }" size="small">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="handleViewVersion(record)">
                查看
              </a-button>
              <a-button type="link" size="small" @click="handleRollback(record)">
                回滚
              </a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-modal>

    <!-- 导入CSV弹窗（新设计） -->
    <a-modal v-model:open="importModalVisible" :title="`导入CSV - ${ruleName || ruleCode}`" width="900px" :footer="null"
      :destroy-on-close="true" @cancel="handleImportModalClose">
      <div class="import-config-modal">
        <!-- 首次导入提示 -->
        <a-alert v-if="isFirstImport" type="info" show-icon class="mb-4" message="首次导入模式：将清空原有数据，全量导入CSV所有有效行" />
        <a-alert v-else type="info" show-icon class="mb-4" message="增量更新模式：按主键匹配进行新增/更新，不删除系统原有旧数据" />

        <!-- 公共配置：主键配置 -->
        <div v-if="allHeaders.length" class="config-section">
          <a-divider>主键配置（用于数据匹配）</a-divider>
          <a-form layout="vertical">
            <a-form-item
              :label="`选择主键字段（联合唯一，可选择1个或多个）${primaryKeys.length > 0 ? '已选: ' + primaryKeys.join(', ') : ''}`" required>
              <a-select v-model:value="primaryKeys" mode="multiple" placeholder="请选择主键字段" style="width: 100%">
                <a-select-option v-for="h in allHeaders" :key="h" :value="h">
                  {{ h }}
                </a-select-option>
              </a-select>
              <div class="form-help">
                规则：配置的全部主键字段同时为空时，该行会被忽略跳过
              </div>
            </a-form-item>
          </a-form>
        </div>

        <!-- 公共配置：同步字段配置（实时从表头获取，不保存） -->
        <div v-if="primaryKeys.length > 0 && allHeaders.length" class="config-section">
          <a-divider>同步字段配置</a-divider>
          <a-form layout="vertical">
            <a-form-item>
              <template #label>
                <span>选择需要同步更新的字段</span>
                <a-checkbox v-model:checked="selectAllSyncFields" @change="handleSelectAllSyncFields"
                  style="margin-left: 16px">
                  全选
                </a-checkbox>
              </template>
              <a-checkbox-group v-model:value="syncFields" style="width: 100%">
                <a-row>
                  <a-col v-for="h in availableSyncFields" :key="h" :span="6">
                    <a-checkbox :value="h">{{ h }}</a-checkbox>
                  </a-col>
                </a-row>
              </a-checkbox-group>
              <div class="form-help">
                仅勾选的字段允许被新CSV覆盖更新，未勾选字段保持系统原有数据不变（配置实时生效，无需保存）
              </div>
            </a-form-item>
            <a-form-item>
              <a-checkbox v-model:checked="allowAddNew">
                允许新增数据（当主键不存在时，是否将CSV数据作为新行导入）
              </a-checkbox>
              <div class="form-help">
                勾选：主键不存在的CSV数据将作为新行导入系统<br>
                不勾选：仅更新主键已存在的数据，忽略主键不存在的数据
              </div>
            </a-form-item>
          </a-form>
        </div>

        <!-- Tab切换：从文件导入 / 从CURL导入 -->
        <a-tabs v-model:activeKey="importActiveTab" type="card" class="import-tabs">
          <!-- 从文件导入 -->
          <a-tab-pane key="file" tab="从文件导入">
            <div class="import-section">
              <!-- 文件上传 -->
              <div @drop.prevent="handleDrop" @dragover.prevent @dragenter.prevent>
                <a-upload-dragger v-model:file-list="importFileList" :custom-request="handleCustomUpload"
                  @change="handleImportFileChange" accept=".csv" :multiple="false" :open-file-dialog-on-click="true">
                  <p class="ant-upload-drag-icon">
                    <UploadOutlined />
                  </p>
                  <p class="ant-upload-text">点击或拖拽CSV文件到此处上传</p>
                  <p class="ant-upload-hint">
                    支持按表头字段名称匹配，不按列顺序匹配
                  </p>
                </a-upload-dragger>
              </div>

              <!-- 数据预览 -->
              <div v-if="filePreviewData.csv_headers?.length" class="preview-section">
                <a-divider>数据预览（前5行）</a-divider>
                <div class="preview-table-wrapper">
                  <a-table :columns="filePreviewColumns" :data-source="filePreviewDataSource" :pagination="false"
                    size="small" bordered :scroll="{ x: 'max-content' }" />
                </div>
                <p class="row-count">共 {{ filePreviewData.row_count }} 行数据</p>
              </div>

              <!-- 字段兼容性说明 -->
              <div v-if="filePreviewData.csv_headers?.length" class="compatibility-section">
                <a-divider>字段兼容性</a-divider>
                <div class="compatibility-info">
                  <p><strong>CSV表头：</strong>{{ filePreviewData.csv_headers.join(', ') }}</p>
                  <p v-if="!isFirstImport"><strong>现有表头：</strong>{{ filePreviewData.existing_headers.join(', ') }}</p>
                  <a-alert type="info" show-icon :message="fileCompatibilityMessage" />
                </div>
              </div>

              <!-- 操作按钮 -->
              <div class="action-buttons">
                <a-space>
                  <a-button @click="importModalVisible = false">取消</a-button>
                  <a-button type="primary" :loading="fileImporting" @click="confirmFileImport"
                    :disabled="!primaryKeys.length || !importFile">
                    执行导入
                  </a-button>
                </a-space>
              </div>
            </div>
          </a-tab-pane>

          <!-- 从CURL导入 -->
          <a-tab-pane key="curl" tab="从CURL导入">
            <CurlImport ref="curlImportRef" :rule-id="ruleId" :rule-code="ruleCode" :rule-name="ruleName"
              :tenant-id="tenantId" :existing-headers="headers" :primary-keys="primaryKeys" :sync-fields="syncFields"
              :allow-add-new="allowAddNew"
              @preview="handleCurlPreview" @imported="handleCurlImportSuccess" />
          </a-tab-pane>
        </a-tabs>
      </div>
    </a-modal>

    <!-- 导入结果弹窗 -->
    <a-modal v-model:open="importResultVisible" title="导入结果" @ok="importResultVisible = false"
      :cancel-button-props="{ style: { display: 'none' } }">
      <a-descriptions :column="1" bordered>
        <a-descriptions-item label="新增行数">{{ importResult.added_count }}</a-descriptions-item>
        <a-descriptions-item label="更新行数">{{ importResult.updated_count }}</a-descriptions-item>
        <a-descriptions-item label="忽略行数">{{ importResult.skipped_count }}</a-descriptions-item>
        <a-descriptions-item label="失败行数" :class="{ 'error-text': importResult.failed_count > 0 }">
          {{ importResult.failed_count }}
        </a-descriptions-item>
        <a-descriptions-item label="总行数">{{ importResult.total_count }}</a-descriptions-item>
        <a-descriptions-item label="新版本号">v{{ importResult.version_no }}</a-descriptions-item>
      </a-descriptions>
      <div v-if="importResult.failed_reasons?.length" class="failed-reasons">
        <a-divider>失败原因</a-divider>
        <a-list size="small" bordered :data-source="importResult.failed_reasons">
          <template #renderItem="{ item }">
            <a-list-item>
              <span>第{{ item.row }}行: {{ item.reason }}</span>
            </a-list-item>
          </template>
        </a-list>
      </div>
    </a-modal>

    <!-- 编辑表头弹窗 -->
    <a-modal v-model:open="headerEditModalVisible" title="编辑表头" @ok="confirmEditHeader"
      @cancel="headerEditModalVisible = false">
      <a-form layout="vertical">
        <a-form-item label="表头名称">
          <a-input v-model:value="headerEditValue" placeholder="请输入表头名称" @pressEnter="confirmEditHeader" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CurlImport from '@/components/CurlImport/index.vue'
import { useUserStore } from '@/store'
import {
  ExportOutlined,
  HistoryOutlined,
  ImportOutlined,
  SaveOutlined,
  UploadOutlined,
} from '@ant-design/icons-vue'
import { HotTable } from '@handsontable/vue3'
import { message, Modal } from 'ant-design-vue'
// 导入完整版 handsontable（包含所有插件，避免 tree-shaking 问题）
import Handsontable from 'handsontable'
import 'handsontable/styles/handsontable.css'
import 'handsontable/styles/ht-theme-main.css'
import { computed, onMounted, reactive, ref, watch } from 'vue'

// 使用完整版 Handsontable，所有模块已自动注册
console.log('Handsontable version:', Handsontable.version)

const userStore = useUserStore()

const props = defineProps<{
  ruleId?: number
  ruleCode?: string
  ruleName?: string
  tenantId?: number
}>()

const emit = defineEmits<{
  saved: []
}>()

// Handsontable 引用
const hotTableRef = ref<InstanceType<typeof HotTable>>()

// 数据状态
const headers = ref<string[]>(['列1', '列2', '列3'])
const tableData = ref<(string | null)[][]>([['', '', '']])
const currentVersion = ref<any>(null)
const currentMd5 = ref('')

// 弹窗状态
const saveModalVisible = ref(false)
const versionModalVisible = ref(false)
const importModalVisible = ref(false)
const importResultVisible = ref(false)
const importFile = ref<File | null>(null)
const importFileList = ref<any[]>([])

// 公共配置状态
const importActiveTab = ref('file')
const primaryKeys = ref<string[]>([])
const syncFields = ref<string[]>([])
const selectAllSyncFields = ref(false)
const isFirstImport = ref(false)
const allHeaders = ref<string[]>([])
const allowAddNew = ref(true)  // 是否允许新增数据

// 文件导入状态
const csvContent = ref('')
const filePreviewData = ref<any>({
  csv_headers: [],
  existing_headers: [],
  row_count: 0,
  preview_data: [],
  is_first_import: false,
  config: {}
})
const fileImporting = ref(false)

// CURL导入引用
const curlImportRef = ref<InstanceType<typeof CurlImport>>()

// 导入结果
const importResult = ref<any>({
  version_no: 0,
  added_count: 0,
  updated_count: 0,
  skipped_count: 0,
  failed_count: 0,
  failed_reasons: [],
  total_count: 0,
  new_md5: ''
})

// 搜索相关状态
const searchQuery = ref('')

const saveForm = reactive({
  remark: '',
})

const versionList = ref<any[]>([])

// 计算属性
const columns = computed(() => [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '规则编码', dataIndex: 'rule_code', key: 'rule_code', width: 200 },
  { title: '规则名称', dataIndex: 'rule_name', key: 'rule_name' },
  { title: '描述', dataIndex: 'desc', key: 'desc', ellipsis: true },
  { title: '最新版本', key: 'latest_version_no', width: 100, align: 'center' },
  { title: '状态', key: 'status', width: 100, align: 'center' },
  { title: '更新时间', key: 'updated_at', width: 180 },
  { title: '操作', key: 'action', width: 250, fixed: 'right' },
])

const versionColumns = [
  { title: '版本号', dataIndex: 'version_no', key: 'version_no', width: 100 },
  { title: '备注', dataIndex: 'remark', key: 'remark', ellipsis: true },
  { title: '文件大小', dataIndex: 'file_size', key: 'file_size', width: 120 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 150, fixed: 'right' },
]

// 筛选下拉菜单配置
const filtersDropdownMenu = {
  items: {
    filter_by_condition: {
      name: '按条件筛选'
    },
    filter_by_value: {
      name: '按值筛选'
    },
    filter_action_bar: {
      name: '筛选操作'
    }
  }
}

// 文件预览表格列
const filePreviewColumns = computed(() => {
  return filePreviewData.value.csv_headers?.map((h: string) => ({
    title: h,
    dataIndex: h,
    key: h,
    width: 150,
    ellipsis: true
  })) || []
})

// 文件预览数据源
const filePreviewDataSource = computed(() => {
  return filePreviewData.value.preview_data?.map((row: any, index: number) => ({
    key: index,
    ...row
  })) || []
})

// 可用于同步的字段（排除主键）
const availableSyncFields = computed(() => {
  const pkSet = new Set(primaryKeys.value)
  return allHeaders.value.filter((h: string) => !pkSet.has(h))
})

// 文件导入兼容性信息
const fileCompatibilityMessage = computed(() => {
  if (isFirstImport.value) {
    return '首次导入：将使用CSV表头作为系统表头'
  }

  const csvHeaders = filePreviewData.value.csv_headers || []
  const existingHeaders = filePreviewData.value.existing_headers || []

  const newFields = csvHeaders.filter((h: string) => !existingHeaders.includes(h))
  const missingFields = existingHeaders.filter((h: string) => !csvHeaders.includes(h))

  if (newFields.length === 0 && missingFields.length === 0) {
    return '表头完全匹配'
  }

  let msg = ''
  if (newFields.length > 0) {
    msg += `新增字段：${newFields.join(', ')}；`
  }
  if (missingFields.length > 0) {
    msg += `保留字段：${missingFields.join(', ')}（CSV中不存在，系统数据保留）`
  }
  return msg
})

// 全选同步字段
const handleSelectAllSyncFields = (e: any) => {
  if (e.target.checked) {
    syncFields.value = [...availableSyncFields.value]
  } else {
    syncFields.value = []
  }
}

// 右键菜单配置
const contextMenuItems = {
  items: {
    row_above: { name: '上方插入行' },
    row_below: { name: '下方插入行' },
    col_left: { name: '左侧插入列' },
    col_right: { name: '右侧插入列' },
    remove_row: { name: '删除行' },
    remove_col: { name: '删除列' },
    undo: { name: '撤销' },
    redo: { name: '重做' },
    make_read_only: { name: '只读' },
    alignment: { name: '对齐方式' },
    cut: { name: '剪切' },
    copy: { name: '复制' },
    paste: { name: '粘贴' },
    edit_header: {
      name: '编辑表头',
      callback: (key: any, selection: any, clickEvent: any) => {
        const colIndex = selection?.[0]?.start?.col
        if (colIndex !== undefined && colIndex >= 0) {
          editHeader(colIndex)
        }
      }
    }
  }
}

// 表头编辑弹窗状态
const headerEditModalVisible = ref(false)
const headerEditIndex = ref(-1)
const headerEditValue = ref('')

// 编辑表头
const editHeader = (colIndex: number) => {
  headerEditIndex.value = colIndex
  headerEditValue.value = headers.value[colIndex] || ''
  headerEditModalVisible.value = true
}

// 确认编辑表头
const confirmEditHeader = () => {
  if (headerEditIndex.value >= 0) {
    const newValue = headerEditValue.value.trim()
    if (newValue) {
      headers.value[headerEditIndex.value] = newValue
      refreshTable()
      message.success('表头已更新')
    } else {
      message.warning('表头名称不能为空')
      return
    }
  }
  headerEditModalVisible.value = false
}

// 处理表头点击
const onCellMouseDown = (event: any, coords: any) => {
  if (coords.row === -1 && coords.col >= 0) {
    const now = Date.now()
    const lastClickTime = (event.target as any)?._lastClickTime || 0
    if (now - lastClickTime < 300) {
      editHeader(coords.col)
    }
    if (event.target) {
      (event.target as any)._lastClickTime = now
    }
  }
}

// 加载规则详情
const loadRuleDetail = async () => {
  if (!props.ruleId) return
  try {
    const params: any = { id: props.ruleId }
    if (props.tenantId) {
      params.tenant_id = props.tenantId
    }
    const res: any = await api.getRuleDetail(params)
    if (res.code === 200 && res.data) {
      const { current_version } = res.data
      if (current_version && current_version.content_json) {
        headers.value = current_version.content_json.headers || ['列1', '列2', '列3']
        const data = current_version.content_json.data || []

        if (data.length > 0) {
          tableData.value = data.map((row: string[]) =>
            headers.value.map((_, index) => row[index] || '')
          )
        } else {
          tableData.value = [headers.value.map(() => '')]
        }

        currentVersion.value = current_version
        currentMd5.value = current_version.content_md5
      } else {
        headers.value = ['列1', '列2', '列3']
        tableData.value = [['', '', '']]
        currentMd5.value = ''
      }

      refreshTable()
    }
  } catch (error) {
    console.error('加载规则详情失败', error)
    headers.value = ['列1', '列2', '列3']
    tableData.value = [['', '', '']]
    currentMd5.value = ''
  }
}

// 刷新表格
const refreshTable = () => {
  if (hotTableRef.value) {
    const hotInstance = hotTableRef.value.hotInstance
    if (hotInstance) {
      hotInstance.loadData(tableData.value)
      hotInstance.updateSettings({
        colHeaders: headers.value
      })
    }
  }
}

// 数据变化回调
const onDataChange = (changes: any, source: string) => {
  if (source === 'loadData') return
  console.log('数据变化:', changes, source)
}

// 列排序回调
const onColumnSort = (currentSortConfig: any, destinationSortConfigs: any) => {
  console.log('列排序:', currentSortConfig, destinationSortConfigs)
}

// 搜索功能
const handleSearch = () => {
  if (!hotTableRef.value?.hotInstance) return

  const hot = hotTableRef.value.hotInstance
  const searchPlugin = hot.getPlugin('search')

  if (!searchQuery.value.trim()) {
    searchPlugin.query('')
    hot.render()
    return
  }

  const results = searchPlugin.query(searchQuery.value)
  hot.render()

  if (results && results.length > 0) {
    const firstResult = results[0]
    hot.selectCell(firstResult.row, firstResult.col)
  }
}

// 清除搜索
const clearSearch = () => {
  searchQuery.value = ''
  if (!hotTableRef.value?.hotInstance) return

  const hot = hotTableRef.value.hotInstance
  const searchPlugin = hot.getPlugin('search')
  searchPlugin.query('')
  hot.render()
}

// 保存
const handleSave = () => {
  const nonEmptyRows = tableData.value.filter(row =>
    row.some(cell => cell && cell.trim() !== '')
  )

  if (nonEmptyRows.length === 0) {
    message.warning('请至少添加一行数据')
    return
  }

  saveForm.remark = ''
  saveModalVisible.value = true
}

// 确认保存
const confirmSave = async () => {
  try {
    const filteredData = tableData.value.filter(row =>
      row.some(cell => cell && cell.trim() !== '')
    )

    const contentJson = {
      headers: headers.value,
      data: filteredData,
    }

    const requestData: any = {
      rule_id: props.ruleId,
      content_json: contentJson,
      current_md5: currentMd5.value,
      remark: saveForm.remark,
    }
    if (props.tenantId) {
      requestData.tenant_id = props.tenantId
    }

    const res: any = await api.saveRuleVersion(requestData)

    if (res.code === 200) {
      message.success('保存成功')
      saveModalVisible.value = false
      currentMd5.value = res.data.new_md5
      currentVersion.value = {
        ...currentVersion.value,
        version_no: res.data.version_no,
        content_md5: res.data.new_md5,
      }
      emit('saved')
    } else if (res.code === 409) {
      message.error(res.msg || '版本冲突，请刷新后重试')
      Modal.confirm({
        title: '版本冲突',
        content: '规则已被他人修改，是否刷新查看最新版本？',
        onOk: () => {
          loadRuleDetail()
        },
      })
    } else if (res.code === 400 && res.msg?.includes('内容未发生变化')) {
      message.info('当前内容没有变化，无需保存新版本')
      saveModalVisible.value = false
    } else {
      message.error(res.msg || '保存失败')
    }
  } catch (error) {
    console.error('保存失败', error)
    message.error('保存失败')
  }
}

// 导入CSV
const handleImport = async () => {
  // 重置导入状态
  csvContent.value = ''
  filePreviewData.value = {
    csv_headers: [],
    existing_headers: [],
    row_count: 0,
    preview_data: [],
    is_first_import: false,
    config: {}
  }
  primaryKeys.value = []
  syncFields.value = []
  selectAllSyncFields.value = false
  fileImporting.value = false
  importFile.value = null
  importFileList.value = []
  allHeaders.value = []
  importActiveTab.value = 'file'
  allowAddNew.value = true

  // 先加载已保存的主键配置（只加载主键，同步字段实时计算）
  if (props.ruleId) {
    try {
      const configRes: any = await api.getImportConfig({
        rule_id: props.ruleId,
        tenant_id: props.tenantId
      })
      if (configRes.code === 200 && configRes.data) {
        primaryKeys.value = configRes.data.primary_keys || []
        // 同步字段不加载，将在预览时根据表头实时计算
      }
    } catch (error) {
      console.warn('加载导入配置失败', error)
    }
  }

  importModalVisible.value = true
}

// 处理导入弹窗关闭
const handleImportModalClose = () => {
  importModalVisible.value = false
  csvContent.value = ''
  filePreviewData.value = {
    csv_headers: [],
    existing_headers: [],
    row_count: 0,
    preview_data: [],
    is_first_import: false,
    config: {}
  }
  primaryKeys.value = []
  syncFields.value = []
  selectAllSyncFields.value = false
  fileImporting.value = false
  importFile.value = null
  importFileList.value = []
  allHeaders.value = []
  allowAddNew.value = true
}

// 处理CSV内容变化（预览时自动保存主键配置）
const handleCsvContentChange = async () => {
  if (!csvContent.value.trim()) {
    filePreviewData.value = {
      csv_headers: [],
      existing_headers: [],
      row_count: 0,
      preview_data: [],
      is_first_import: false,
      config: {}
    }
    allHeaders.value = []
    return
  }

  if (!props.ruleId) {
    message.warning('规则ID不存在')
    return
  }

  try {
    // 预览时传入当前主键配置，后端会自动保存
    const res: any = await api.previewFileImport({
      rule_id: props.ruleId,
      tenant_id: props.tenantId,
      content: csvContent.value,
      primary_keys: primaryKeys.value  // 传入当前主键配置，后端自动保存
    })

    if (res.code === 200) {
      filePreviewData.value = res.data
      isFirstImport.value = res.data.is_first_import
      allHeaders.value = res.data.csv_headers || []

      // 使用后端返回的主键配置（可能已经更新）
      if (res.data.primary_keys) {
        primaryKeys.value = res.data.primary_keys
      }

      // 使用后端返回的同步字段（实时计算的，排除主键）
      if (res.data.sync_fields) {
        syncFields.value = res.data.sync_fields
        selectAllSyncFields.value = syncFields.value.length === availableSyncFields.value.length
      }
    } else {
      message.error(res.msg || '预览失败')
    }
  } catch (error) {
    console.error('预览失败', error)
    message.error('预览失败')
  }
}

// 自定义上传请求（阻止默认上传行为）
const handleCustomUpload = () => {
  // 不做任何操作，阻止默认上传
}

// 处理文件变化
const handleImportFileChange = async (info: any) => {
  const fileList = info.fileList || []

  if (fileList.length > 1) {
    importFileList.value = [fileList[fileList.length - 1]]
  }

  const file = info.file?.originFileObj || info.file
  if (!file) return

  if (!file.name || !file.name.endsWith('.csv')) {
    message.error('请选择CSV文件')
    importFileList.value = []
    importFile.value = null
    return
  }

  importFile.value = file

  const reader = new FileReader()
  reader.onload = async (e) => {
    csvContent.value = e.target?.result as string
    await handleCsvContentChange()
  }
  reader.readAsText(file)
}

// 处理拖拽事件
const handleDrop = (e: DragEvent) => {
  e.preventDefault()
  e.stopPropagation()

  const files = e.dataTransfer?.files
  if (!files || files.length === 0) return

  const file = files[0]
  if (!file.name.endsWith('.csv')) {
    message.error('请选择CSV文件')
    return
  }

  importFile.value = file

  const fileInfo = {
    file: {
      originFileObj: file,
      name: file.name,
      status: 'done'
    },
    fileList: [{ originFileObj: file, name: file.name, status: 'done' }]
  }
  handleImportFileChange(fileInfo)
}

// 确认文件导入
const confirmFileImport = async () => {
  if (!props.ruleId) {
    message.warning('规则ID不存在')
    return
  }

  if (!importFile.value) {
    message.warning('请上传CSV文件')
    return
  }

  if (primaryKeys.value.length === 0) {
    message.warning('请至少选择一个主键字段')
    return
  }

  fileImporting.value = true

  try {
    const importData = {
      rule_id: props.ruleId,
      tenant_id: props.tenantId,
      content: csvContent.value,
      current_md5: currentMd5.value,
      allow_add_new: allowAddNew.value,
      config: {
        primary_keys: primaryKeys.value,
        sync_fields: syncFields.value
      }
    }

    const res: any = await api.applyImport(importData)

    if (res.code === 200) {
      importResult.value = res.data
      importResultVisible.value = true

      // 检查是否无变化
      if (res.data.no_change) {
        message.info(res.data.message || '当前内容没有变化，无需保存新版本')
      } else {
        // 刷新表格数据
        loadRuleDetail()
        emit('saved')
      }
      importModalVisible.value = false
    } else {
      message.error(res.msg || '导入失败')
    }
  } catch (error) {
    console.error('导入失败', error)
    message.error('导入失败')
  } finally {
    fileImporting.value = false
  }
}

// 处理CURL预览
const handleCurlPreview = (data: any) => {
  allHeaders.value = data.headers || []
  isFirstImport.value = data.is_first_import || false
}

// 处理CURL导入成功
const handleCurlImportSuccess = (data: any) => {
  importResult.value = data
  importResultVisible.value = true
  loadRuleDetail()
  importModalVisible.value = false
  emit('saved')
}

// 导出CSV
const handleExport = async () => {
  try {
    const params: any = { rule_id: props.ruleId }
    if (currentVersion.value?.version_no) {
      params.version_no = currentVersion.value.version_no
    }
    if (props.tenantId) {
      params.tenant_id = props.tenantId
    }
    const res = await api.exportRuleCsv(params)
    const blob = new Blob([res.data], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${props.ruleCode}_v${currentVersion.value?.version_no || 'latest'}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    message.success('导出成功')
  } catch (error) {
    console.error('导出失败', error)
    message.error('导出失败')
  }
}

// 显示版本历史
const showVersionHistory = async () => {
  try {
    const params: any = { rule_id: props.ruleId }
    if (props.tenantId) {
      params.tenant_id = props.tenantId
    }
    const res: any = await api.getRuleVersions(params)
    if (res.code === 200) {
      versionList.value = res.data || []
      versionModalVisible.value = true
    } else {
      message.error(res.msg || '获取版本历史失败')
    }
  } catch (error) {
    console.error('获取版本历史失败', error)
    message.error('获取版本历史失败')
  }
}

// 查看版本
const handleViewVersion = async (record: any) => {
  try {
    const params: any = { rule_id: props.ruleId, version_no: record.version_no }
    if (props.tenantId) {
      params.tenant_id = props.tenantId
    }
    const res: any = await api.getRuleVersionByNo(params)
    if (res.code === 200 && res.data) {
      const version = res.data
      if (version.content_json) {
        headers.value = version.content_json.headers || []
        const data = version.content_json.data || []

        if (data.length > 0) {
          tableData.value = data.map((row: string[]) =>
            headers.value.map((_, index) => row[index] || '')
          )
        } else {
          tableData.value = [headers.value.map(() => '')]
        }

        currentVersion.value = {
          ...currentVersion.value,
          version_no: version.version_no,
        }

        refreshTable()
        versionModalVisible.value = false
        message.success(`已加载版本 v${record.version_no} 的内容，保存时将创建新版本`)
      }
    }
  } catch (error) {
    console.error('获取版本详情失败', error)
    message.error('获取版本详情失败')
  }
}

// 回滚版本
const handleRollback = async (record: any) => {
  Modal.confirm({
    title: '确认回滚',
    content: `确定要回滚到版本 v${record.version_no} 吗？`,
    onOk: async () => {
      try {
        const data: any = {
          rule_id: props.ruleId,
          version_no: record.version_no,
        }
        if (props.tenantId) {
          data.tenant_id = props.tenantId
        }
        const res: any = await api.rollbackRuleVersion(data)
        if (res.code === 200) {
          message.success('回滚成功')
          loadRuleDetail()
          versionModalVisible.value = false
          emit('saved')
        } else {
          message.error(res.msg || '回滚失败')
        }
      } catch (error) {
        console.error('回滚失败', error)
        message.error('回滚失败')
      }
    },
  })
}

// 监听 open 和 ruleId 变化
watch(() => [props.ruleId], () => {
  if (props.ruleId) {
    loadRuleDetail()
  }
})

onMounted(() => {
  if (props.ruleId) {
    loadRuleDetail()
  }
})
</script>

<style scoped lang="less">
.excel-csv-editor {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f5f5f5;
  border-radius: 8px;
}

.table-container {
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  overflow: hidden;
}

.handsontable-wrapper {
  :deep(.handsontable) {
    font-size: 14px;

    .htCore td {
      height: 32px;
    }
  }
}

.shortcuts {
  margin-top: 8px;
}

.version-time {
  color: #999;
  font-size: 12px;
}

.import-config-modal {
  padding: 16px;
}

.config-section {
  margin-bottom: 24px;

  .form-help {
    margin-top: 8px;
    color: #666;
    font-size: 12px;
  }
}

.config-save-section {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.import-tabs {
  margin-top: 16px;
}

.import-section {
  margin-top: 16px;
}

.preview-section {
  margin-bottom: 24px;

  .preview-table-wrapper {
    max-height: 300px;
    overflow: auto;
  }

  .row-count {
    margin-top: 8px;
    color: #666;
    font-size: 14px;
  }
}

.compatibility-section {
  margin-bottom: 24px;

  .compatibility-info {
    p {
      margin-bottom: 8px;
    }
  }
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.failed-reasons {
  margin-top: 16px;
}

.error-text {
  color: #ff4d4f;
}

.mb-4 {
  margin-bottom: 16px;
}
</style>
