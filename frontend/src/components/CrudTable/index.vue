<template>
  <div class="crud-page">
    <a-card>
      <!-- 筛选表单 -->
      <a-form v-if="showFilter" :model="filterModel" class="crud-filter-form smart-filter-form">
        <a-row :gutter="16" class="filter-row">
          <slot name="filter-items" />
          <a-col v-bind="actionColProps" class="filter-actions-col"
            :class="filterItemCount <= 2 ? 'single-line' : 'multi-line'">
            <a-form-item class="filter-actions">
              <a-space>
                <a-button type="primary" @click="handleSearch">
                  <SearchOutlined />
                  查询
                </a-button>
                <a-button @click="handleReset">
                  <ReloadOutlined />
                  重置
                </a-button>
              </a-space>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>

      <!-- 操作按钮区 -->
      <div v-if="showActions" class="table-actions">
        <slot name="actions" />
      </div>

      <!-- 数据表格 -->
      <div class="table-wrapper">
        <a-table :columns="resizableColumns" :data-source="dataSource" :loading="loading" :pagination="paginationConfig"
          :row-key="rowKey" :scroll="tableScroll" :row-selection="rowSelection" @change="handleTableChange" @resizeColumn="handleResizeColumn">
          <template v-for="slotName in Object.keys($slots)" :key="slotName" #[slotName]="slotProps">
            <slot :name="slotName" v-bind="slotProps" />
          </template>
        </a-table>
      </div>
    </a-card>

    <!-- 新增/编辑 弹窗 -->
    <a-modal v-if="showModal" v-model:open="modalVisible" :title="modalTitle" :confirm-loading="modalLoading"
      @ok="handleModalOk" @cancel="modalVisible = false" :width="modalWidth">
      <a-form ref="modalFormRef" :model="modalForm" :rules="modalRules" :label-col="modalLabelCol"
        :wrapper-col="modalWrapperCol">
        <slot name="modal-form" :form="modalForm" :action="modalAction" />
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons-vue'
import type { FormInstance } from 'ant-design-vue'
import { computed, reactive, ref } from 'vue'

// 表格列类型定义 - 使用宽松类型允许自动推断
export interface ColumnType {
  title: string
  dataIndex?: string
  key: string
  width?: number
  minWidth?: number
  maxWidth?: number
  fixed?: 'left' | 'right'
  ellipsis?: boolean
  resizable?: boolean
  // 允许其他任意属性
  [key: string]: any
}

// 宽松的列类型，用于接受用户传入的列配置（无需显式声明类型）
// 使用 any 类型来完全避免类型推断问题，让用户可以传入任意列配置
export type LooseColumnType = {
  title: string
  key: string
  dataIndex?: string
  width?: number
  minWidth?: number
  maxWidth?: number
  fixed?: string
  ellipsis?: boolean
  resizable?: boolean
  // 允许其他任意属性
  [key: string]: any
}

export interface PaginationConfig {
  current: number
  pageSize: number
  total: number
  showSizeChanger?: boolean
  showTotal?: (total: number) => string
  [key: string]: any
}

const props = withDefaults(defineProps<{
  // 表格列配置 - 使用宽松类型，允许自动推断
  columns: LooseColumnType[]
  // 数据源
  dataSource: any[]
  // 加载状态
  loading?: boolean
  // 分页配置
  pagination?: PaginationConfig | false
  // 行唯一标识字段
  rowKey?: string | ((record: any) => string)
  // 是否显示筛选表单
  showFilter?: boolean
  // 筛选表单模型
  filterModel?: Record<string, any>
  // 是否显示操作按钮区
  showActions?: boolean
  // 表格滚动配置
  scroll?: { x?: number | string; y?: number | string }
  // 操作列宽度
  actionColumnWidth?: number
  // 操作列是否固定右侧
  actionColumnFixed?: boolean
  // 筛选表单项数量（用于控制按钮布局）
  filterItemCount?: number
  // 是否显示弹窗
  showModal?: boolean
  // 弹窗标题
  modalTitle?: string
  // 弹窗加载状态
  modalLoading?: boolean
  // 弹窗表单数据
  modalForm?: Record<string, any>
  // 弹窗表单校验规则
  modalRules?: Record<string, any>
  // 弹窗宽度
  modalWidth?: string | number
  // 弹窗标签布局
  modalLabelCol?: { span: number }
  // 弹窗内容布局
  modalWrapperCol?: { span: number }
  // 是否启用列宽调整
  resizable?: boolean
  // 列宽调整最小宽度
  minWidth?: number
  // 列宽调整最大宽度
  maxWidth?: number
  // 行选择配置
  rowSelection?: any
}>(), {
  loading: false,
  rowKey: 'id',
  showFilter: true,
  filterModel: () => ({}),
  showActions: true,
  scroll: () => ({ x: 'max-content' }),
  actionColumnWidth: 200,
  actionColumnFixed: true,
  filterItemCount: 1,
  showModal: false,
  modalTitle: '',
  modalLoading: false,
  modalForm: () => ({}),
  modalRules: () => ({}),
  modalWidth: 520,
  modalLabelCol: () => ({ span: 6 }),
  modalWrapperCol: () => ({ span: 16 }),
  resizable: true,
  minWidth: 80,
  maxWidth: 600,
})

const emit = defineEmits<{
  search: []
  reset: []
  'table-change': [pagination: any, filters: any, sorter: any]
  'modal-ok': [form: Record<string, any>, action: 'add' | 'edit']
}>()

// 弹窗相关
const modalVisible = ref(false)
const modalAction = ref<'add' | 'edit'>('add')
const modalFormRef = ref<FormInstance>()
const modalForm = reactive(props.modalForm)

// 列宽状态管理
const columnWidths = ref<Record<string, number>>({})

// 智能默认宽度计算
function getDefaultWidth(col: LooseColumnType): number {
  const titleLen = (col.title || '').toString().length
  return Math.max(props.minWidth, titleLen * 15 + 20)
}

// 处理列配置 - 添加默认宽度和 resizable 属性
const resizableColumns = computed<ColumnType[]>(() => {
  return props.columns.map(col => {
    const width = columnWidths.value[col.key] || col.width || getDefaultWidth(col)
    return {
      ...col,
      width,
      minWidth: col.minWidth || props.minWidth,
      maxWidth: col.maxWidth || props.maxWidth,
      ellipsis: col.ellipsis !== false,
      resizable: props.resizable && col.resizable !== false,
      // 确保 fixed 符合 ColumnType 的要求
      fixed: (col.fixed === 'left' || col.fixed === 'right') ? col.fixed : undefined,
    } as ColumnType
  })
})

// 处理列宽调整
function handleResizeColumn(width: number, col: ColumnType) {
  // 限制最小和最大宽度
  const minWidth = col.minWidth || props.minWidth
  const maxWidth = col.maxWidth || props.maxWidth
  const finalWidth = Math.max(minWidth, Math.min(width, maxWidth))

  columnWidths.value[col.key] = finalWidth

  // 更新列配置中的宽度
  const column = resizableColumns.value.find(c => c.key === col.key)
  if (column) {
    column.width = finalWidth
  }
}

// 分页配置
const paginationConfig = computed(() => {
  if (props.pagination === false) return false
  return {
    showSizeChanger: true,
    showTotal: (total: number) => `共 ${total} 条`,
    ...props.pagination,
  }
})

// 表格滚动配置
const tableScroll = computed(() => {
  return props.scroll || { x: 'max-content' }
})

// 操作按钮列的栅格配置 - 与表单项使用相同的栅格配置，保持对齐
const actionColProps = computed(() => {
  // 按钮区域作为一个普通格子，使用与其他筛选项相同的栅格配置
  return {
    xs: 24,
    sm: 12,
    md: 8,
    lg: 6,
    xl: 6
  }
})

// 查询
function handleSearch() {
  emit('search')
}

// 重置
function handleReset() {
  emit('reset')
}

// 表格变化
function handleTableChange(pagination: any, filters: any, sorter: any) {
  emit('table-change', pagination, filters, sorter)
}

// 打开新增弹窗
function openAddModal() {
  modalAction.value = 'add'
  // 同步父组件的 modalForm 数据
  Object.assign(modalForm, props.modalForm)
  modalVisible.value = true
}

// 打开编辑弹窗
function openEditModal(record: any) {
  modalAction.value = 'edit'
  // 先同步父组件的 modalForm，再合并编辑的记录
  Object.assign(modalForm, props.modalForm, record)
  modalVisible.value = true
}

// 关闭弹窗
function closeModal() {
  modalVisible.value = false
}

// 弹窗确认
async function handleModalOk() {
  try {
    await modalFormRef.value?.validate()
    // 使用内部的 modalForm 确保获取最新的表单数据
    emit('modal-ok', { ...modalForm }, modalAction.value)
  } catch (error) {
    // 校验失败
  }
}

// 重置弹窗表单
function resetModalForm() {
  modalFormRef.value?.resetFields()
}

// 暴露方法
defineExpose({
  openAddModal,
  openEditModal,
  closeModal,
  resetModalForm,
  modalForm,
  modalAction,
})
</script>

<style scoped lang="less">
.crud-page {
  .table-wrapper {
    :deep(.ant-table) {
      th {
        position: relative;

        // 列宽调整手柄样式
        .ant-table-column-resizer {
          position: absolute;
          right: 0;
          top: 0;
          bottom: 0;
          width: 5px;
          cursor: col-resize;
          z-index: 10;
          background: transparent;
          transition: background 0.2s;

          &:hover,
          &.active {
            background: #1890ff;
          }
        }
      }
    }
  }
}
</style>
