<template>
  <div class="json-editor">
    <!-- 工具栏 -->
    <div class="json-toolbar">
      <div class="json-toolbar-left">
        <span class="json-title">{{ title }}</span>
      </div>
      <div class="json-toolbar-right">
        <a-tooltip title="格式化">
          <a-button type="text" size="small" @click="handleFormat">
            <AlignLeftOutlined />
          </a-button>
        </a-tooltip>
      </div>
    </div>

    <!-- JSON内容编辑区 -->
    <div class="json-content">
      <textarea
        ref="textareaRef"
        v-model="jsonValue"
        class="json-textarea"
        :placeholder="placeholder"
        @input="handleInput"
      ></textarea>
    </div>
  </div>
</template>

<script setup lang="ts">
import { AlignLeftOutlined } from '@ant-design/icons-vue'
import { ref, watch } from 'vue'

interface Props {
  // 数据对象（JSON格式）
  modelValue?: any
  // 标题
  title?: string
  // 占位符
  placeholder?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: 'JSON 配置',
  placeholder: '请输入 JSON 配置...'
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: any): void
  (e: 'change', value: any): void
}>()

const textareaRef = ref<HTMLTextAreaElement>()
const jsonValue = ref('')

// 格式化
const handleFormat = () => {
  try {
    const obj = JSON.parse(jsonValue.value)
    jsonValue.value = JSON.stringify(obj, null, 2)
  } catch (e) {
    // 格式化失败，保持原样
    console.warn('格式化失败:', e)
  }
}

// 输入处理 - 直接传递原始值，不做校验
const handleInput = () => {
  try {
    const obj = JSON.parse(jsonValue.value)
    emit('update:modelValue', obj)
    emit('change', obj)
  } catch {
    // 解析失败时，传递原始字符串
    emit('update:modelValue', jsonValue.value)
    emit('change', jsonValue.value)
  }
}

// 监听modelValue变化
watch(() => props.modelValue, (newValue) => {
  if (newValue && typeof newValue === 'object') {
    jsonValue.value = JSON.stringify(newValue, null, 2)
  } else if (typeof newValue === 'string') {
    jsonValue.value = newValue
  } else {
    jsonValue.value = ''
  }
}, { immediate: true, deep: true })
</script>

<style scoped lang="less">
.json-editor {
  background: #f6f8fa;
  border-radius: 4px;
  padding: 12px;

  .json-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #e1e4e8;

    .json-toolbar-left {
      .json-title {
        font-size: 14px;
        font-weight: 600;
        color: #24292e;
      }
    }

    .json-toolbar-right {
      button {
        margin-left: 8px;
      }
    }
  }

  .json-content {
    .json-textarea {
      width: 100%;
      min-height: 400px;
      padding: 12px;
      border: 1px solid #d0d7de;
      border-radius: 6px;
      font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
      font-size: 13px;
      line-height: 1.5;
      resize: vertical;
      background: #ffffff;
      color: #24292e;

      &:focus {
        outline: none;
        border-color: #0969da;
        box-shadow: 0 0 0 3px rgba(9, 105, 218, 0.1);
      }

      &::placeholder {
        color: #8c959f;
      }
    }
  }
}
</style>
