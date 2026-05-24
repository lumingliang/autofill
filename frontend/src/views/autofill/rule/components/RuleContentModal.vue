<template>
    <a-modal v-model:open="visible" :title="`编辑规则内容 - ${ruleName || ruleCode}`" width="90%" :footer="null"
        :destroy-on-close="true" @cancel="handleCancel">
        <ExcelCsvEditor ref="editorRef" :rule-id="ruleId" :rule-code="ruleCode" :rule-name="ruleName"
            :tenant-id="tenantId" @saved="handleSaved" />
    </a-modal>
</template>

<script setup lang="ts">
import ExcelCsvEditor from '@/components/ExcelCsvEditor/index.vue';
import { computed, ref, watch } from 'vue';

const props = defineProps<{
    open?: boolean
    ruleId?: number
    ruleCode?: string
    ruleName?: string
    tenantId?: number
}>()

const emit = defineEmits<{
    'update:open': [value: boolean]
    saved: []
}>()

const visible = computed({
    get: () => props.open ?? false,
    set: (value) => emit('update:open', value),
})

const editorRef = ref<InstanceType<typeof ExcelCsvEditor>>()

// 保存成功回调
const handleSaved = () => {
    emit('saved')
}

// 取消
const handleCancel = () => {
    visible.value = false
}

// 监听 open 和 ruleId 变化
watch(() => [props.open, props.ruleId], ([newOpen, newRuleId]) => {
    if (newOpen && newRuleId) {
        // 组件内部会处理加载逻辑
    }
})
</script>
