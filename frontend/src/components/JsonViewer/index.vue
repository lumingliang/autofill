<template>
  <div class="json-viewer" :class="{ 'is-dark': darkMode, 'has-border': showBorder }">
    <!-- 工具栏 -->
    <div v-if="showToolbar" class="json-toolbar">
      <div class="json-toolbar-left">
        <span class="json-title">{{ title }}</span>
        <span v-if="showSize" class="json-size">{{ formattedSize }}</span>
      </div>
      <div class="json-toolbar-right">
        <a-tooltip title="复制">
          <a-button type="text" size="small" @click="handleCopy">
            <CopyOutlined />
          </a-button>
        </a-tooltip>
        <a-tooltip :title="isExpanded ? '收起' : '展开'">
          <a-button type="text" size="small" @click="toggleExpand">
            <component :is="isExpanded ? CompressOutlined : ExpandOutlined" />
          </a-button>
        </a-tooltip>
      </div>
    </div>

    <!-- JSON内容 -->
    <div
      ref="contentRef"
      class="json-content"
      :class="{
        'is-scrollable': scrollable,
        'is-wrap': wrapText && !isExpanded,
        'is-expanded': isExpanded
      }"
      :style="contentStyle"
    >
      <pre v-if="formattedJson" class="json-pre">{{ formattedJson }}</pre>
      <div v-else class="json-empty">{{ emptyText }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { CopyOutlined, ExpandOutlined, CompressOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, ref, watch } from 'vue'

interface Props {
  // 数据
  data: any
  // 标题
  title?: string
  // 是否深模式
  darkMode?: boolean
  // 是否显示边框
  showBorder?: boolean
  // 是否显示工具栏
  showToolbar?: boolean
  // 是否显示大小
  showSize?: boolean
  // 是否可滚动
  scrollable?: boolean
  // 最大高度（滚动模式下）
  maxHeight?: string | number
  // 是否自动换行（非展开模式下）
  wrapText?: boolean
  // 缩进空格数
  indent?: number
  // 空数据提示
  emptyText?: string
  // 默认展开状态
  defaultExpanded?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: 'JSON',
  darkMode: false,
  showBorder: true,
  showToolbar: true,
  showSize: true,
  scrollable: true,
  maxHeight: '400px',
  wrapText: false,
  indent: 2,
  emptyText: '暂无数据',
  defaultExpanded: false
})

const contentRef = ref<HTMLElement>()
const isExpanded = ref(props.defaultExpanded)

// 格式化JSON
const formattedJson = computed(() => {
  if (!props.data) return ''
  try {
    const data = typeof props.data === 'string' ? JSON.parse(props.data) : props.data
    return JSON.stringify(data, null, props.indent)
  } catch (e) {
    return String(props.data)
  }
})

// 计算大小
const formattedSize = computed(() => {
  const json = formattedJson.value
  if (!json) return '0 B'
  const bytes = new Blob([json]).size
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
})

// 内容样式
const contentStyle = computed(() => {
  const style: Record<string, string> = {}
  if (props.scrollable && !isExpanded.value) {
    style.maxHeight = typeof props.maxHeight === 'number' ? `${props.maxHeight}px` : props.maxHeight
  }
  return style
})

// 切换展开
const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
}

// 复制
const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(formattedJson.value)
    message.success('已复制到剪贴板')
  } catch (e) {
    message.error('复制失败')
  }
}

// 监听数据变化，重置展开状态
watch(() => props.data, () => {
  if (!props.defaultExpanded) {
    isExpanded.value = false
  }
})
</script>

<style scoped lang="less">
.json-viewer {
  background: #f6f8fa;
  border-radius: 6px;
  overflow: hidden;

  &.is-dark {
    background: #1e1e1e;

    .json-toolbar {
      background: #2d2d2d;
      border-bottom-color: #3d3d3d;

      .json-title {
        color: #e0e0e0;
      }

      .json-size {
        color: #888;
      }
    }

    .json-content {
      .json-pre {
        color: #d4d4d4;
      }
    }
  }

  &.has-border {
    border: 1px solid #e1e4e8;
  }

  .json-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: #fff;
    border-bottom: 1px solid #e1e4e8;

    .json-toolbar-left {
      display: flex;
      align-items: center;
      gap: 8px;

      .json-title {
        font-size: 13px;
        font-weight: 500;
        color: #333;
      }

      .json-size {
        font-size: 11px;
        color: #888;
        background: #f0f0f0;
        padding: 2px 6px;
        border-radius: 3px;
      }
    }

    .json-toolbar-right {
      display: flex;
      gap: 4px;
    }
  }

  .json-content {
    padding: 12px;
    overflow: auto;

    &.is-scrollable {
      overflow: auto;
    }

    &.is-wrap {
      .json-pre {
        white-space: pre-wrap;
        word-wrap: break-word;
      }
    }

    &.is-expanded {
      max-height: none !important;
    }

    .json-pre {
      margin: 0;
      font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
      font-size: 12px;
      line-height: 1.6;
      color: #333;
      white-space: pre;
      word-wrap: normal;
    }

    .json-empty {
      text-align: center;
      color: #888;
      padding: 24px;
      font-size: 13px;
    }
  }
}

// 滚动条样式
.json-content::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.json-content::-webkit-scrollbar-track {
  background: transparent;
}

.json-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.json-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

// 暗色模式滚动条
.is-dark .json-content::-webkit-scrollbar-thumb {
  background: #555;
}

.is-dark .json-content::-webkit-scrollbar-thumb:hover {
  background: #666;
}
</style>
