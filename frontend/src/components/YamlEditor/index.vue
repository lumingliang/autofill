<template>
  <div class="yaml-editor">
    <!-- 工具栏 -->
    <div class="yaml-toolbar">
      <div class="yaml-toolbar-left">
        <span class="yaml-title">{{ title }}</span>
      </div>
      <div class="yaml-toolbar-right">
        <a-tooltip title="格式化">
          <a-button type="text" size="small" @click="handleFormat">
            <AlignLeftOutlined />
          </a-button>
        </a-tooltip>
        <a-tooltip title="验证">
          <a-button type="text" size="small" @click="handleValidate">
            <CheckCircleOutlined />
          </a-button>
        </a-tooltip>
        <a-tooltip title="切换格式 (JSON/YAML)">
          <a-button type="text" size="small" @click="toggleFormat">
            <FileTextOutlined />
          </a-button>
        </a-tooltip>
      </div>
    </div>

    <!-- YAML内容编辑区 -->
    <div class="yaml-content">
      <textarea
        ref="textareaRef"
        v-model="yamlValue"
        class="yaml-textarea"
        :placeholder="placeholder"
        @input="handleInput"
      ></textarea>
    </div>

    <!-- 验证结果提示 -->
    <div v-if="validationMessage" class="yaml-validation" :class="validationType">
      {{ validationMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { AlignLeftOutlined, CheckCircleOutlined, FileTextOutlined } from '@ant-design/icons-vue'
import { ref, watch, computed } from 'vue'
import * as yaml from 'js-yaml'

interface Props {
  // 数据对象（JSON格式）
  modelValue?: any
  // 标题
  title?: string
  // 占位符
  placeholder?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: 'YAML 配置',
  placeholder: '请输入 YAML 配置...'
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: any): void
  (e: 'change', value: any): void
}>()

const textareaRef = ref<HTMLTextAreaElement>()
const yamlValue = ref('')
const validationMessage = ref('')
const validationType = ref<'success' | 'error' | 'warning'>('success')
const isYamlFormat = ref(true)

// 将JSON对象转换为YAML字符串
const jsonToYaml = (obj: any): string => {
  if (!obj) return ''
  try {
    return yaml.dump(obj, { indent: 2, skipInvalid: true })
  } catch {
    return JSON.stringify(obj, null, 2)
  }
}

// 将YAML字符串转换为JSON对象
const yamlToJson = (yamlStr: string): any => {
  if (!yamlStr.trim()) return null
  try {
    return yaml.load(yamlStr, { json: true })
  } catch {
    try {
      return JSON.parse(yamlStr)
    } catch {
      return null
    }
  }
}

// 格式化
const handleFormat = () => {
  try {
    const obj = yamlToJson(yamlValue.value)
    if (obj) {
      yamlValue.value = isYamlFormat.value ? jsonToYaml(obj) : JSON.stringify(obj, null, 2)
      validationMessage.value = '格式化成功'
      validationType.value = 'success'
    } else {
      validationMessage.value = '无法解析配置内容'
      validationType.value = 'error'
    }
  } catch (e) {
    validationMessage.value = '格式化失败: ' + (e as Error).message
    validationType.value = 'error'
  }
}

// 验证
const handleValidate = () => {
  try {
    const obj = yamlToJson(yamlValue.value)
    if (obj) {
      validationMessage.value = '配置格式有效'
      validationType.value = 'success'
    } else {
      validationMessage.value = '配置格式无效'
      validationType.value = 'error'
    }
  } catch (e) {
    validationMessage.value = '验证失败: ' + (e as Error).message
    validationType.value = 'error'
  }
}

// 切换格式
const toggleFormat = () => {
  try {
    const obj = yamlToJson(yamlValue.value)
    if (obj) {
      isYamlFormat.value = !isYamlFormat.value
      yamlValue.value = isYamlFormat.value ? jsonToYaml(obj) : JSON.stringify(obj, null, 2)
      validationMessage.value = `已切换为${isYamlFormat.value ? 'YAML' : 'JSON'}格式`
      validationType.value = 'success'
    } else {
      isYamlFormat.value = !isYamlFormat.value
      validationMessage.value = `已切换为${isYamlFormat.value ? 'YAML' : 'JSON'}格式`
      validationType.value = 'success'
    }
  } catch (e) {
    isYamlFormat.value = !isYamlFormat.value
    validationMessage.value = `已切换为${isYamlFormat.value ? 'YAML' : 'JSON'}格式`
    validationType.value = 'success'
  }
}

// 输入处理
const handleInput = () => {
  const obj = yamlToJson(yamlValue.value)
  emit('update:modelValue', obj)
  emit('change', obj)
  validationMessage.value = ''
}

// 监听modelValue变化
watch(() => props.modelValue, (newValue) => {
  if (newValue && typeof newValue === 'object') {
    yamlValue.value = isYamlFormat.value ? jsonToYaml(newValue) : JSON.stringify(newValue, null, 2)
  } else if (typeof newValue === 'string') {
    yamlValue.value = newValue
  }
}, { immediate: true, deep: true })
</script>

<style scoped lang="less">
.yaml-editor {
  background: #f6f8fa;
  border-radius: 4px;
  padding: 12px;

  .yaml-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #e1e4e8;

    .yaml-toolbar-left {
      .yaml-title {
        font-size: 14px;
        font-weight: 600;
        color: #24292e;
      }
    }

    .yaml-toolbar-right {
      button {
        margin-left: 8px;
      }
    }
  }

  .yaml-content {
    .yaml-textarea {
      width: 100%;
      min-height: 300px;
      padding: 12px;
      font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
      font-size: 14px;
      line-height: 1.6;
      border: 1px solid #d1d5da;
      border-radius: 4px;
      background: #fff;
      resize: vertical;
      box-sizing: border-box;

      &:focus {
        outline: none;
        border-color: #0366d6;
        box-shadow: inset 0 1px 2px rgba(27, 31, 35, 0.075), 0 0 0 3px rgba(3, 102, 214, 0.3);
      }
    }
  }

  .yaml-validation {
    margin-top: 8px;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 13px;

    &.success {
      background-color: #e6f4ea;
      color: #22863a;
      border: 1px solid #c3e6cb;
    }

    &.error {
      background-color: #fbe5e7;
      color: #d73a49;
      border: 1px solid #fbc0c4;
    }

    &.warning {
      background-color: #fff3cd;
      color: #856404;
      border: 1px solid #ffeeba;
    }
  }
}
</style>
