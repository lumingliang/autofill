<template>
    <div class="options-markdown-editor">
        <div class="editor-hint">
            <a-typography-text type="secondary">
                <InfoCircleOutlined /> 格式说明：
                <code>## 选项标签</code> 定义选项，
                <code>- 选项值: xxx</code> 定义值，
                <code>- 填写说明: xxx</code> 定义说明（支持多行层级缩进）
            </a-typography-text>
        </div>
        <MdEditor v-model="content" :editor-id="editorId" :toolbars="toolbars" :preview="false" :footers="[]"
            :theme="theme" language="zh-CN" :placeholder="placeholder" :style="{ height: height + 'px' }"
            @on-change="handleChange" />
    </div>
</template>

<script setup lang="ts">
import { InfoCircleOutlined } from '@ant-design/icons-vue'
import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { onMounted, ref, watch } from 'vue'

// 导入 md-editor-v3 类型
import type { Themes, ToolbarNames } from 'md-editor-v3'

// 选项项接口
interface OptionItem {
    label: string
    value: string
    fill_instruction: string
    is_deleted?: boolean
}

const props = defineProps<{
    modelValue: string
    placeholder?: string
    height?: number
}>()

const emit = defineEmits<{
    'update:modelValue': [value: string]
    change: [markdown: string, items: OptionItem[]]
}>()

const content = ref('')
const editorId = 'options-markdown-editor-' + Date.now()
const theme = ref<Themes>('light')

// 精简工具栏配置
const toolbars = [
    'bold',
    'italic',
    'strikeThrough',
    '-',
    'unorderedList',
    'orderedList',
    '-',
    'code',
    'quote',
    '-',
    'fullscreen'
] as ToolbarNames[]

// 监听外部值变化
watch(() => props.modelValue, (newVal) => {
    if (newVal !== content.value) {
        content.value = newVal
    }
}, { immediate: true })

// 监听内容变化
watch(content, (newVal) => {
    emit('update:modelValue', newVal)
})

// 处理编辑器变化
const handleChange = (markdown: string) => {
    const items = parseMarkdownToOptions(markdown)
    emit('change', markdown, items)
}

// 解析 Markdown 为选项列表
const parseMarkdownToOptions = (markdown: string): OptionItem[] => {
    if (!markdown.trim()) return []

    const items: OptionItem[] = []
    const lines = markdown.split('\n')
    let currentItem: OptionItem | null = null
    let state: 'lookingForMetadata' | 'readingInstruction' = 'lookingForMetadata'
    let instructionLines: string[] = []

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const trimmedLine = line.trim()

        // 选项标题 ## xxx（严格行首匹配）
        if (line.startsWith('## ')) {
            // 保存上一个选项的填写说明
            if (currentItem && instructionLines.length > 0) {
                currentItem.fill_instruction = instructionLines.join('\n')
            }
            if (currentItem) {
                items.push(currentItem)
            }
            currentItem = {
                label: trimmedLine.substring(3).trim(),
                value: '',
                fill_instruction: '',
                is_deleted: false
            }
            state = 'lookingForMetadata'
            instructionLines = []
            continue
        }

        if (!currentItem) continue

        if (state === 'lookingForMetadata') {
            // 跳过空行
            if (!trimmedLine) continue

            // 严格匹配选项值行：必须是行首的"- 选项值: "（注意空格）
            if (trimmedLine.startsWith('- 选项值:')) {
                currentItem.value = trimmedLine.substring('- 选项值:'.length).trim()
                continue
            }

            // 严格匹配填写说明行：必须是行首的"- 填写说明: "（注意空格）
            if (trimmedLine.startsWith('- 填写说明:')) {
                const firstLine = trimmedLine.substring('- 填写说明:'.length).trim()
                instructionLines = firstLine ? [firstLine] : []
                state = 'readingInstruction'
                continue
            }

            // 在寻找元数据状态时，遇到非元数据行，忽略或报错
            // 这里选择忽略，保持兼容性
            continue
        }

        if (state === 'readingInstruction') {
            // 一旦进入读取填写说明状态，后续所有行都被当作普通文本
            // 保留原始格式（只去掉可能存在的末尾换行符）
            instructionLines.push(line.replace(/\r$/, ''))
        }
    }

    // 保存最后一个选项的填写说明
    if (currentItem) {
        if (instructionLines.length > 0) {
            currentItem.fill_instruction = instructionLines.join('\n')
        }
        items.push(currentItem)
    }

    return items
}

// 将选项列表转换为 Markdown
const convertOptionsToMarkdown = (items: OptionItem[]): string => {
    if (!items?.length) return ''

    return items.map((item, index) => {
        const lines: string[] = []
        lines.push(`## ${item.label || ''}`)

        if (item.value) {
            lines.push(`- 选项值: ${item.value}`)
        }

        if (item.fill_instruction) {
            const instructionLines = item.fill_instruction.split('\n')
            // 第一行作为填写说明标题
            lines.push(`- 填写说明: ${instructionLines[0]}`)

            // 后续行保留原始缩进层级
            for (let i = 1; i < instructionLines.length; i++) {
                const line = instructionLines[i]
                // 检查是否已有缩进
                const indentMatch = line.match(/^(\s*)/)
                const hasIndent = indentMatch && indentMatch[1].length >= 2

                if (hasIndent) {
                    // 保留原始缩进
                    lines.push(line)
                } else {
                    // 添加基础缩进（2个空格）
                    lines.push(`  ${line}`)
                }
            }
        }

        if (index < items.length - 1) lines.push('')
        return lines.join('\n')
    }).join('\n')
}

// 暴露方法给父组件
defineExpose({
    parseMarkdownToOptions,
    convertOptionsToMarkdown
})

onMounted(() => {
    // 初始化时解析一次
    if (content.value) {
        handleChange(content.value)
    }
})
</script>

<style scoped lang="scss">
.options-markdown-editor {
    width: 100%;

    .editor-hint {
        margin-bottom: 8px;
        padding: 8px 12px;
        background-color: #f6ffed;
        border: 1px solid #b7eb8f;
        border-radius: 4px;

        code {
            background-color: #fff;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 12px;
            color: #cf1322;
        }
    }

    :deep(.md-editor) {
        border-radius: 6px;
        border: 1px solid #d9d9d9;

        &:hover {
            border-color: #40a9ff;
        }

        &.focus {
            border-color: #40a9ff;
            box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
        }

        // 工具栏样式
        .md-editor-toolbar {
            background: #fafafa;
            border-bottom: 1px solid #e8e8e8;
        }

        // 编辑区域样式
        .md-editor-content {
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
            font-size: 14px;
            line-height: 1.6;

            // 层级缩进样式
            .cm-line {
                position: relative;

                // 缩进引导线
                &::before {
                    content: '';
                    position: absolute;
                    left: 0;
                    top: 0;
                    bottom: 0;
                    width: 1px;
                    background: transparent;
                }

                // 一级缩进（2空格）
                &[style*="text-indent: 2ch"],
                &:has(.cm-indent-1) {
                    padding-left: 2ch;
                    border-left: 1px dashed #e0e0e0;
                }

                // 二级缩进（4空格）
                &[style*="text-indent: 4ch"],
                &:has(.cm-indent-2) {
                    padding-left: 4ch;
                    border-left: 2px dashed #d0d0d0;
                }

                // 三级缩进（6空格）
                &[style*="text-indent: 6ch"],
                &:has(.cm-indent-3) {
                    padding-left: 6ch;
                    border-left: 2px dashed #c0c0c0;
                }
            }
        }
    }
}
</style>
