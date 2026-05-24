<template>
  <div class="vxe-csv-editor">
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
        <a-button @click="insertRow">
          <PlusOutlined />
          插入行
        </a-button>
        <a-button @click="insertColumn">
          <PlusOutlined />
          插入列
        </a-button>
        <a-button @click="deleteSelectedRow">
          <DeleteOutlined />
          删除行
        </a-button>
        <a-button @click="deleteSelectedColumn">
          <DeleteOutlined />
          删除列
        </a-button>
      </a-space>
      <a-space v-if="currentVersion">
        <a-tag color="blue">版本: v{{ currentVersion.version_no }}</a-tag>
        <span v-if="currentVersion.created_at" class="version-time">
          {{ currentVersion.created_at }}
        </span>
      </a-space>
    </div>

    <!-- 表头编辑区域 -->
    <div class="header-edit-area">
      <a-space>
        <span class="label">编辑表头:</span>
        <a-input
          v-for="(header, index) in headers"
          :key="index"
          v-model:value="headers[index]"
          size="small"
          style="width: 120px"
          :placeholder="`列${index + 1}`"
          @change="onHeaderChange"
        />
      </a-space>
    </div>

    <!-- vxe-table 表格 -->
    <div class="table-container">
      <vxe-table
        ref="tableRef"
        :data="tableData"
        :height="450"
        :edit-config="{ trigger: 'click', mode: 'cell' }"
        :keyboard-config="{ isArrow: true, isEnter: true, isTab: true, isEdit: true }"
        :mouse-config="{ selected: true }"
        :clipboard-config="{ copy: true, cut: true, paste: true }"
        :row-config="{ isCurrent: true, isHover: true }"
        :column-config="{ resizable: true }"
        border
        round
        highlight-current-row
        highlight-hover-row
        show-overflow
        class="mytable-style"
        @cell-selected="onCellSelected"
      >
        <vxe-column type="seq" width="60" title="序号" fixed="left" />
        <vxe-column
          v-for="(header, index) in headers"
          :key="index"
          :field="`col${index}`"
          :title="header || `列${index + 1}`"
          min-width="120"
          :edit-render="{ name: 'input', attrs: { type: 'text' } }"
        />
        <vxe-column title="操作" width="100" fixed="right">
          <template #default="{ rowIndex }">
            <a-button type="link" danger size="small" @click="deleteRow(rowIndex)">
              <DeleteOutlined />
            </a-button>
          </template>
        </vxe-column>
      </vxe-table>
    </div>

    <!-- 快捷操作提示 -->
    <div class="shortcuts">
      <a-alert type="info" show-icon :message="'快捷键: Enter-编辑/确认 | Tab-下一单元格 | Ctrl+C/V-复制粘贴 | Delete-清空单元格'" />
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

    <!-- 导入CSV弹窗 -->
    <a-modal v-model:open="importModalVisible" title="导入CSV" @ok="confirmImport" @cancel="importModalVisible = false">
      <div @drop.prevent="handleDrop" @dragover.prevent @dragenter.prevent>
        <a-upload-dragger accept=".csv" :custom-request="handleCustomUpload" :file-list="importFileList"
          @change="handleImportFileChange" :show-upload-list="false">
          <p class="ant-upload-drag-icon">
            <UploadOutlined />
          </p>
          <p class="ant-upload-text">点击或拖拽CSV文件到此处上传</p>
          <p class="ant-upload-hint">
            支持上传CSV文件，系统将自动解析并预览数据
          </p>
        </a-upload-dragger>
      </div>
      <div v-if="importPreview" class="import-preview">
        <a-divider>预览（前10行）</a-divider>
        <div class="preview-table-wrapper">
          <a-table :columns="importPreview.headers.map((h: string) => ({ title: h, dataIndex: h, key: h, ellipsis: true }))"
            :data-source="importPreview.data.map((row: string[], index: number) => {
              const obj: any = { key: index }
              importPreview.headers.forEach((h: string, i: number) => {
                obj[h] = row[i] || ''
              })
              return obj
            })" :pagination="false" size="small" bordered :scroll="{ x: 'max-content' }" />
        </div>
        <p class="import-info">共 {{ importPreview.row_count }} 行数据</p>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import {
  DeleteOutlined,
  ExportOutlined,
  HistoryOutlined,
  ImportOutlined,
  PlusOutlined,
  SaveOutlined,
  UploadOutlined,
} from '@ant-design/icons-vue'
import type { VxeTableInstance } from 'vxe-table'
import api from '@/api'
import { useUserStore } from '@/store'

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

// 表格引用
const tableRef = ref<VxeTableInstance>()

// 数据状态
const headers = ref<string[]>(['列1', '列2', '列3'])
const tableData = ref<Record<string, string>[]>([])
const currentVersion = ref<any>(null)
const currentMd5 = ref('')

// 弹窗状态
const saveModalVisible = ref(false)
const versionModalVisible = ref(false)
const importModalVisible = ref(false)
const importPreview = ref<any>(null)
const importFile = ref<File | null>(null)
const importFileList = ref<any[]>([])

const saveForm = reactive({
  remark: '',
})

const versionList = ref<any[]>([])

// 版本历史列
const versionColumns = [
  { title: '版本号', dataIndex: 'version_no', key: 'version_no', width: 100 },
  { title: '备注', dataIndex: 'remark', key: 'remark', ellipsis: true },
  { title: '文件大小', dataIndex: 'file_size', key: 'file_size', width: 120 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 150, fixed: 'right' },
]

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
        tableData.value = data.map((row: string[]) => {
          const obj: Record<string, string> = {}
          headers.value.forEach((_, index) => {
            obj[`col${index}`] = row[index] || ''
          })
          return obj
        })
        currentVersion.value = current_version
        currentMd5.value = current_version.content_md5
      } else {
        headers.value = ['列1', '列2', '列3']
        tableData.value = []
        currentMd5.value = ''
      }
    }
  } catch (error) {
    console.error('加载规则详情失败', error)
    headers.value = ['列1', '列2', '列3']
    tableData.value = []
    currentMd5.value = ''
  }
}

// 表头变化
const onHeaderChange = () => {
  // 表头变化时刷新表格
  tableRef.value?.refreshColumn()
}

// 单元格选中
const onCellSelected = () => {
  // 可以在这里处理单元格选中逻辑
}

// 插入行
const insertRow = () => {
  const obj: Record<string, string> = {}
  headers.value.forEach((_, index) => {
    obj[`col${index}`] = ''
  })
  const $table = tableRef.value
  if ($table) {
    const currentRow = $table.getCurrentRecord()
    if (currentRow) {
      const rowIndex = tableData.value.indexOf(currentRow)
      tableData.value.splice(rowIndex + 1, 0, obj)
    } else {
      tableData.value.push(obj)
    }
  } else {
    tableData.value.push(obj)
  }
}

// 删除行
const deleteRow = (index: number) => {
  tableData.value.splice(index, 1)
}

// 删除选中行
const deleteSelectedRow = () => {
  const $table = tableRef.value
  if (!$table) return
  const currentRow = $table.getCurrentRecord()
  if (currentRow) {
    const rowIndex = tableData.value.indexOf(currentRow)
    if (rowIndex >= 0) {
      tableData.value.splice(rowIndex, 1)
    }
  } else {
    message.warning('请先选中一行')
  }
}

// 插入列
const insertColumn = () => {
  const newIndex = headers.value.length
  headers.value.push(`列${newIndex + 1}`)
  tableData.value.forEach((row) => {
    row[`col${newIndex}`] = ''
  })
}

// 删除选中列
const deleteSelectedColumn = () => {
  const $table = tableRef.value
  if (!$table) return
  
  // 获取当前选中的列
  const selectedColumn = $table.getCurrentColumn()
  if (selectedColumn && selectedColumn.field) {
    const fieldMatch = selectedColumn.field.match(/col(\d+)/)
    if (fieldMatch) {
      const actualIndex = parseInt(fieldMatch[1])
      if (actualIndex >= 0 && actualIndex < headers.value.length) {
        headers.value.splice(actualIndex, 1)
        // 重新整理数据列
        const newData: Record<string, string>[] = []
        tableData.value.forEach((row) => {
          const newRow: Record<string, string> = {}
          headers.value.forEach((_, newIndex) => {
            const oldKey = `col${newIndex < actualIndex ? newIndex : newIndex + 1}`
            newRow[`col${newIndex}`] = row[oldKey] || ''
          })
          newData.push(newRow)
        })
        tableData.value = newData
        return
      }
    }
  }
  message.warning('请先选中一个数据列')
}

// 保存
const handleSave = () => {
  if (tableData.value.length === 0) {
    message.warning('请至少添加一行数据')
    return
  }
  saveForm.remark = ''
  saveModalVisible.value = true
}

// 确认保存
const confirmSave = async () => {
  try {
    const contentJson = {
      headers: headers.value,
      data: tableData.value.map((row) =>
        headers.value.map((_, index) => row[`col${index}`] || '')
      ),
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
const handleImport = () => {
  importPreview.value = null
  importFile.value = null
  importModalVisible.value = true
}

// 处理文件预览
const previewFile = async (file: File) => {
  importFile.value = file
  const reader = new FileReader()
  reader.onload = async (e) => {
    const content = e.target?.result as string
    try {
      const res: any = await api.previewRuleCsv({ content })
      if (res.code === 200) {
        importPreview.value = res.data
      } else {
        message.error(res.msg || '预览失败')
      }
    } catch (error) {
      message.error('预览失败')
    }
  }
  reader.readAsText(file)
}

// 自定义上传处理
const handleCustomUpload = () => {
  return false
}

// 处理导入文件变化
const handleImportFileChange = (info: any) => {
  const file = info.file
  if (file && file.originFileObj) {
    previewFile(file.originFileObj)
  } else if (file) {
    previewFile(file)
  }
}

// 处理拖放上传
const handleDrop = (e: DragEvent) => {
  e.preventDefault()
  const files = e.dataTransfer?.files
  if (files && files.length > 0) {
    const file = files[0]
    if (file.name.endsWith('.csv')) {
      importFileList.value = [{
        uid: Date.now().toString(),
        name: file.name,
        status: 'done',
        originFileObj: file
      }]
      previewFile(file)
    } else {
      message.error('请上传CSV文件')
    }
  }
}

// 确认导入
const confirmImport = async () => {
  if (!importFile.value) {
    message.warning('请选择文件')
    return
  }
  if (!props.ruleId) {
    message.warning('规则ID不存在')
    return
  }

  try {
    const tenantId = userStore.isSuperUser ? props.tenantId : undefined
    const res: any = await api.importRuleCsv(props.ruleId, importFile.value, currentMd5.value, tenantId)
    if (res.code === 200) {
      const { headers: newHeaders, data } = res.data.full_content || res.data
      headers.value = newHeaders || []
      tableData.value = (data || []).map((row: string[]) => {
        const obj: Record<string, string> = {}
        headers.value.forEach((_, index) => {
          obj[`col${index}`] = row[index] || ''
        })
        return obj
      })
      importModalVisible.value = false
      message.success('导入成功')
    } else {
      message.error(res.msg || '导入失败')
    }
  } catch (error) {
    console.error('导入失败', error)
    message.error('导入失败')
  }
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
        tableData.value = data.map((row: string[]) => {
          const obj: Record<string, string> = {}
          headers.value.forEach((_, index) => {
            obj[`col${index}`] = row[index] || ''
          })
          return obj
        })
        currentVersion.value = {
          ...currentVersion.value,
          version_no: version.version_no,
        }
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
const handleRollback = (record: any) => {
  Modal.confirm({
    title: '确认回滚',
    content: `确定要回滚到版本 v${record.version_no} 吗？这将创建一个新版本。`,
    onOk: async () => {
      try {
        const res: any = await api.rollbackRuleVersion({ rule_id: props.ruleId, version_no: record.version_no })
        if (res.code === 200) {
          message.success('回滚成功')
          versionModalVisible.value = false
          loadRuleDetail()
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

// 暴露方法给父组件
defineExpose({
  loadRuleDetail,
  getData: () => ({
    headers: headers.value,
    data: tableData.value.map((row) =>
      headers.value.map((_, index) => row[`col${index}`] || '')
    ),
  }),
})

// 监听 ruleId 变化
watch(() => props.ruleId, (newRuleId) => {
  if (newRuleId) {
    loadRuleDetail()
  }
})
</script>

<style scoped lang="less">
.vxe-csv-editor {
  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding-bottom: 16px;
    border-bottom: 1px solid #f0f0f0;

    .version-time {
      color: #999;
      font-size: 12px;
    }
  }

  .header-edit-area {
    margin-bottom: 16px;
    padding: 12px;
    background: #fafafa;
    border-radius: 6px;

    .label {
      font-weight: 500;
      color: #666;
    }
  }

  .table-container {
    margin-bottom: 16px;

    .mytable-style {
      :deep(.vxe-body--row) {
        &.row--current {
          background-color: #e6f7ff;
        }
      }

      :deep(.vxe-cell) {
        padding: 4px 8px;
      }

      :deep(.vxe-header--column) {
        background-color: #fafafa;
        font-weight: 600;
      }
    }
  }

  .shortcuts {
    margin-top: 16px;
  }
}

.import-preview {
  margin-top: 16px;

  .preview-table-wrapper {
    max-width: 100%;
    overflow-x: auto;

    :deep(.ant-table) {
      min-width: 100%;
    }
  }

  .import-info {
    margin-top: 8px;
    color: #666;
    text-align: center;
  }
}
</style>
