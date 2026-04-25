<template>
  <div class="crud-table">
    <a-card>
      <!-- 筛选表单 -->
      <a-form v-if="showFilter" :model="filterModel" class="crud-filter-form">
        <a-row :gutter="16">
          <slot name="filter-items" />
          <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6">
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
      <a-table
        :columns="processedColumns"
        :data-source="dataSource"
        :loading="loading"
        :pagination="paginationConfig"
        :row-key="rowKey"
        :scroll="tableScroll"
        @change="handleTableChange"
      >
        <template v-for="slotName in Object.keys($slots)" :key="slotName" #[slotName]="slotProps">
          <slot :name="slotName" v-bind="slotProps" />
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons-vue'

export interface ColumnType {
  title: string
  dataIndex?: string
  key: string
  width?: number
  fixed?: 'left' | 'right'
  ellipsis?: boolean
  resizable?: boolean
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
  // 表格列配置
  columns: ColumnType[]
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
}>(), {
  loading: false,
  rowKey: 'id',
  showFilter: true,
  filterModel: () => ({}),
  showActions: true,
  actionColumnWidth: 200,
  actionColumnFixed: true,
})

const emit = defineEmits<{
  search: []
  reset: []
  'table-change': [pagination: any, filters: any, sorter: any]
}>()

// 处理列配置 - 添加resizable和fixed
const processedColumns = computed(() => {
  return props.columns.map(col => ({
    ...col,
    resizable: col.resizable !== false,
  }))
})

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
</script>

<style scoped lang="less">
.crud-table {
  .crud-filter-form {
    margin-bottom: 16px;

    :deep(.filter-item) {
      display: flex;
      align-items: center;
      margin-bottom: 16px;

      .ant-form-item-label {
        flex-shrink: 0;
        min-width: 70px;
        text-align: right;
        padding-right: 8px;
        margin-right: 0;
      }

      .ant-form-item-control {
        flex: 1;
        min-width: 0;
      }
    }

    :deep(.filter-actions) {
      display: flex;
      justify-content: flex-end;
      align-items: center;
      margin-bottom: 16px;
      padding-top: 0;
    }
  }

  .table-actions {
    margin-bottom: 16px;
  }

  :deep(.ant-table) {
    .ant-table-cell {
      // 可调整列宽样式
      .ant-table-column-sorters {
        display: flex;
        align-items: center;
      }
    }

    // 固定列样式优化
    .ant-table-cell-fix-right {
      background: #fff;
    }

    .ant-table-cell-fix-left {
      background: #fff;
    }
  }
}
</style>
