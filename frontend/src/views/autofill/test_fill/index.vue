<template>
    <div class="test-fill-page">
        <a-card title="规则引擎测试" class="test-fill-card">
            <div class="rule-test-section">
                <a-form layout="vertical">
                    <!-- 第一行：应用选择 -->
                    <a-row :gutter="16">
                        <a-col :span="12">
                            <a-form-item label="应用" required>
                                <a-select v-model:value="ruleForm.app_name" placeholder="请选择应用"
                                    :options="ruleAppOptions" :loading="loadingRuleApps"
                                    style="width: 100%"
                                    @change="handleRuleAppChange" />
                            </a-form-item>
                        </a-col>
                        <a-col :span="12">
                            <a-form-item label="用户输入" required>
                                <a-textarea v-model:value="ruleForm.query" :rows="2"
                                    placeholder="请输入用户输入文本，例如：我买的手机屏幕碎了，我要投诉" />
                            </a-form-item>
                        </a-col>
                    </a-row>

                    <a-divider />

                    <!-- 全局配置：系统提示词（多个规则共用） -->
                    <a-row :gutter="16">
                        <a-col :span="8">
                            <a-form-item label="系统提示词">
                                <a-select v-model:value="ruleForm.system_prompt_name"
                                    placeholder="请选择系统提示词（多个规则共用）" :options="systemPromptOptions" allow-clear
                                    style="width: 100%" />
                            </a-form-item>
                        </a-col>
                    </a-row>

                    <a-divider />

                    <!-- 规则参数配置 -->
                    <div class="params-section">
                        <div class="params-header">
                            <h4>规则参数配置</h4>
                            <a-button type="primary" size="small" @click="addRuleParam">
                                <PlusOutlined />
                                添加规则
                            </a-button>
                        </div>

                        <div v-for="(param, index) in ruleForm.params" :key="index" class="param-item">
                            <a-card size="small" :title="`规则 ${index + 1}`">
                                <template #extra>
                                    <a-button v-if="ruleForm.params.length > 1" type="link" danger size="small"
                                        @click="removeRuleParam(index)">
                                        删除
                                    </a-button>
                                </template>

                                <a-row :gutter="16">
                                    <a-col :span="12">
                                        <a-form-item label="规则名称" required>
                                            <a-select v-model:value="param.rule_name" placeholder="请选择规则"
                                                :options="ruleOptions" :loading="loadingRules"
                                                :disabled="!ruleForm.app_name" style="width: 100%"
                                                @change="(val: any) => handleRuleChange(val, index)" />
                                        </a-form-item>
                                    </a-col>
                                    <a-col :span="12">
                                        <a-form-item label="任务类型">
                                            <a-select v-model:value="param.prompt.type" :options="[
                                                { label: '选择题', value: 'choice' },
                                                { label: '填空题', value: 'text' }
                                            ]" />
                                        </a-form-item>
                                    </a-col>
                                </a-row>

                                <!-- Filter条件 - 动态表头选择 -->
                                <a-row :gutter="16">
                                    <a-col :span="24">
                                        <a-form-item label="Filter条件">
                                            <div class="filter-conditions">
                                                <div v-for="(filter, fIndex) in param.filterConditions"
                                                    :key="fIndex" class="filter-row">
                                                    <a-select v-model:value="filter.column" placeholder="选择字段"
                                                        :options="param.columnOptions" style="width: 200px" />
                                                    <a-input v-model:value="filter.value" placeholder="输入值"
                                                        style="width: 300px; margin-left: 8px" />
                                                    <a-button type="link" danger
                                                        @click="removeFilterCondition(index, Number(fIndex))">
                                                        删除
                                                    </a-button>
                                                </div>
                                                <a-button type="dashed" size="small"
                                                    @click="addFilterCondition(index)">
                                                    <PlusOutlined />
                                                    添加条件
                                                </a-button>
                                            </div>
                                        </a-form-item>
                                    </a-col>
                                </a-row>

                                <!-- 字段选择 - 多选下拉 -->
                                <a-row :gutter="16">
                                    <a-col :span="8">
                                        <a-form-item label="Select Fields (返回字段)">
                                            <a-select v-model:value="param.prompt.select_fields" mode="multiple"
                                                placeholder="选择返回字段" :options="param.columnOptions"
                                                style="width: 100%" />
                                        </a-form-item>
                                    </a-col>
                                    <a-col :span="8">
                                        <a-form-item label="Name Fields (名称字段)">
                                            <a-select v-model:value="param.prompt.name_fields" mode="multiple"
                                                placeholder="选择名称字段" :options="param.columnOptions"
                                                style="width: 100%" />
                                        </a-form-item>
                                    </a-col>
                                    <a-col :span="8">
                                        <a-form-item label="Rule Fields (规则字段)">
                                            <a-select v-model:value="param.prompt.rule_fields" mode="multiple"
                                                placeholder="选择规则字段" :options="param.columnOptions"
                                                style="width: 100%" />
                                        </a-form-item>
                                    </a-col>
                                </a-row>

                                <!-- 示例数据展示 -->
                                <a-row v-if="param.sampleData && param.sampleData.length > 0">
                                    <a-col :span="24">
                                        <a-form-item label="CSV示例数据">
                                            <a-table :dataSource="param.sampleData"
                                                :columns="param.sampleColumns" size="small" :pagination="false"
                                                bordered />
                                        </a-form-item>
                                    </a-col>
                                </a-row>
                            </a-card>
                        </div>
                    </div>

                    <a-form-item>
                        <a-space>
                            <a-button type="primary" size="large" :loading="ruleExecuting"
                                @click="handleRuleExecute">
                                <PlayCircleOutlined />
                                执行规则
                            </a-button>
                            <a-button size="large" @click="handleExportCurl">
                                <CopyOutlined />
                                导出 Curl
                            </a-button>
                        </a-space>
                    </a-form-item>
                </a-form>

                <a-divider v-if="ruleExecuteResult" />

                <!-- 执行结果 -->
                <div v-if="ruleExecuteResult" class="execute-result">
                    <a-card title="执行结果" size="small">
                        <a-descriptions :column="3" bordered size="small">
                            <a-descriptions-item label="Session ID">
                                {{ ruleExecuteResult.data?.session_id }}
                            </a-descriptions-item>
                            <a-descriptions-item label="步骤">
                                {{ ruleExecuteResult.data?.step }}
                            </a-descriptions-item>
                            <a-descriptions-item label="状态">
                                <a-tag
                                    :color="ruleExecuteResult.data?.status === 'completed' ? 'green' : 'blue'">
                                    {{ ruleExecuteResult.data?.status }}
                                </a-tag>
                            </a-descriptions-item>
                            <a-descriptions-item label="执行时间" :span="2">
                                {{ ruleExecuteResult.data?.elapsed_time?.toFixed(3) }}s
                            </a-descriptions-item>
                        </a-descriptions>

                        <a-divider />

                        <h4>规则执行详情：</h4>
                        <div v-for="(param, index) in ruleForm.params" :key="index" class="rule-result">
                            <h5>规则: {{ param.rule_name }}</h5>
                            <div v-if="ruleExecuteResult.data?.results?.[param.rule_name]"
                                class="result-content">
                                <p><strong>LLM返回:</strong> {{
                                    ruleExecuteResult.data.results[param.rule_name].llm_res }}</p>
                                <div
                                    v-if="Object.keys(ruleExecuteResult.data.results[param.rule_name]).length > 1">
                                    <p><strong>提取字段:</strong></p>
                                    <a-descriptions :column="2" bordered size="small">
                                        <template
                                            v-for="(value, itemKey) in ruleExecuteResult.data.results[param.rule_name]"
                                            :key="itemKey">
                                            <a-descriptions-item
                                                v-if="itemKey !== 'llm_res' && itemKey !== 'error'"
                                                :label="String(itemKey)">
                                                {{ value }}
                                            </a-descriptions-item>
                                        </template>
                                    </a-descriptions>
                                </div>
                                <a-alert v-if="ruleExecuteResult.data.results[param.rule_name].error"
                                    type="error"
                                    :message="ruleExecuteResult.data.results[param.rule_name].error"
                                    show-icon />
                            </div>
                        </div>

                        <a-divider />

                        <h4>完整响应（JSON）：</h4>
                        <JsonViewer :data="ruleExecuteResult" title="结果详情" :max-height="400" />
                    </a-card>
                </div>
            </div>
        </a-card>
    </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { message } from 'ant-design-vue'
import {
    PlusOutlined,
    PlayCircleOutlined,
    CopyOutlined,
} from '@ant-design/icons-vue'
import { useUserStore } from '@/store'
import api from '@/api'
import JsonViewer from '@/components/JsonViewer/index.vue'

const userStore = useUserStore()
const isSuperUser = computed(() => userStore.isSuperUser)

// ==================== 规则执行测试 ====================
const ruleForm = reactive({
    app_name: '',
    query: '',
    system_prompt_name: undefined as string | undefined,
    params: [] as any[]
})

const loadingRuleApps = ref(false)
const ruleAppOptions = ref<{ label: string; value: string }[]>([])
const loadingRules = ref(false)
const ruleOptions = ref<{ label: string; value: string }[]>([])
const ruleExecuting = ref(false)
const ruleExecuteResult = ref<any>(null)
const systemPromptOptions = ref<{ label: string; value: string }[]>([])

// 初始化规则参数
const initRuleParams = () => {
    ruleForm.params = [{
        rule_name: '',
        prompt: {
            type: 'choice',
            filter: {},
            select_fields: [],
            name_fields: [],
            rule_fields: []
        },
        filterConditions: [],
        columnOptions: [],
        sampleData: [],
        sampleColumns: []
    }]
}

initRuleParams()

const addRuleParam = () => {
    ruleForm.params.push({
        rule_name: '',
        prompt: {
            type: 'choice',
            filter: {},
            select_fields: [],
            name_fields: [],
            rule_fields: []
        },
        filterConditions: [],
        columnOptions: [],
        sampleData: [],
        sampleColumns: []
    })
}

const removeRuleParam = (index: number) => {
    ruleForm.params.splice(index, 1)
}

const addFilterCondition = (paramIndex: number) => {
    ruleForm.params[paramIndex].filterConditions.push({
        column: '',
        value: ''
    })
}

const removeFilterCondition = (paramIndex: number, filterIndex: number) => {
    ruleForm.params[paramIndex].filterConditions.splice(filterIndex, 1)
}

// 加载规则测试应用列表
const loadRuleApps = async () => {
    loadingRuleApps.value = true
    try {
        const res: any = await api.getRuleTestApps()
        const items = res?.data || []
        ruleAppOptions.value = items.map((a: any) => ({
            label: a.app_name,
            value: a.app_name
        }))
    } catch (error) {
        console.error('加载应用列表失败:', error)
    } finally {
        loadingRuleApps.value = false
    }
}



// 规则测试应用变更处理
const handleRuleAppChange = async (appName: string) => {
    if (!appName) {
        ruleOptions.value = []
        return
    }

    loadingRules.value = true
    try {
        const res: any = await api.getRuleTestRules({ app_name: appName })
        const items = res?.data || []
        ruleOptions.value = items.map((r: any) => ({
            label: `${r.rule_name} (${r.rule_code})`,
            value: r.rule_code
        }))
    } catch (error) {
        console.error('加载规则列表失败:', error)
    } finally {
        loadingRules.value = false
    }
}

// 规则选择变化时加载CSV表头
const handleRuleChange = async (ruleCode: string, paramIndex: number) => {
    const param = ruleForm.params[paramIndex]
    param.columnOptions = []
    param.sampleData = []
    param.sampleColumns = []
    param.prompt.select_fields = []
    param.prompt.name_fields = []
    param.prompt.rule_fields = []
    param.filterConditions = []

    if (!ruleCode || !ruleForm.app_name) return

    try {
        const res: any = await api.getRuleTestColumns({
            rule_code: ruleCode,
            app_name: ruleForm.app_name
        })

        const columns = res?.data?.columns || []
        const sampleData = res?.data?.sample_data || []
        const sampleCount = res?.data?.sample_count || 0

        param.columnOptions = columns.map((c: string) => ({
            label: c,
            value: c
        }))

        param.sampleColumns = columns.map((c: string) => ({
            title: c,
            dataIndex: c,
            key: c
        }))

        // 将二维数组转换为对象数组，以便表格正确显示
        param.sampleData = sampleData.map((row: any, idx: number) => {
            if (Array.isArray(row)) {
                // 如果是数组，将列名作为 key，数组值作为 value
                const rowObj: any = { key: idx }
                columns.forEach((col: string, colIdx: number) => {
                    rowObj[col] = row[colIdx] ?? ''
                })
                return rowObj
            } else {
                // 如果已经是对象，直接返回
                return { key: idx, ...row }
            }
        })
    } catch (error) {
        console.error('加载规则列失败:', error)
    }
}

// 执行规则测试
const handleRuleExecute = async () => {
    if (!ruleForm.app_name) {
        message.warning('请选择应用')
        return
    }
    if (!ruleForm.query.trim()) {
        message.warning('请输入用户输入')
        return
    }
    if (ruleForm.params.length === 0) {
        message.warning('请至少配置一个规则参数')
        return
    }
    for (let i = 0; i < ruleForm.params.length; i++) {
        if (!ruleForm.params[i].rule_name) {
            message.warning(`请选择规则 ${i + 1} 的规则名称`)
            return
        }
    }

    ruleExecuting.value = true
    ruleExecuteResult.value = null

    try {
        const requestData: any = {
            app_name: ruleForm.app_name,
            query: ruleForm.query,
            params: ruleForm.params.map(p => ({
                rule_name: p.rule_name,
                prompt: {
                    type: p.prompt.type,
                    filter: p.filterConditions.reduce((acc: any, f: any) => {
                        if (f.column && f.value) {
                            acc[f.column] = f.value
                        }
                        return acc
                    }, {}),
                    select_fields: p.prompt.select_fields,
                    name_fields: p.prompt.name_fields,
                    rule_fields: p.prompt.rule_fields
                }
            })),
            system_prompt_name: ruleForm.system_prompt_name
        }

        const res: any = await api.executeRuleTest(requestData)
        ruleExecuteResult.value = res
        message.success('规则执行成功')
    } catch (error: any) {
        message.error(error.message || '规则执行失败')
    } finally {
        ruleExecuting.value = false
    }
}

// 导出Curl命令
const handleExportCurl = async () => {
    if (!ruleForm.app_name) {
        message.warning('请选择应用')
        return
    }
    if (!ruleForm.query.trim()) {
        message.warning('请输入用户输入')
        return
    }

    try {
        const requestData: any = {
            app_name: ruleForm.app_name,
            query: ruleForm.query,
            params: ruleForm.params.map(p => ({
                rule_name: p.rule_name,
                prompt: {
                    type: p.prompt.type,
                    filter: p.filterConditions.reduce((acc: any, f: any) => {
                        if (f.column && f.value) {
                            acc[f.column] = f.value
                        }
                        return acc
                    }, {}),
                    select_fields: p.prompt.select_fields,
                    name_fields: p.prompt.name_fields,
                    rule_fields: p.prompt.rule_fields
                }
            })),
            system_prompt_name: ruleForm.system_prompt_name
        }

        const res: any = await api.exportRuleTestCurl(requestData)
        const curlCommand = res?.data?.curl_command

        if (curlCommand) {
            await navigator.clipboard.writeText(curlCommand)
            message.success('Curl命令已复制到剪贴板')
        } else {
            message.error('导出失败：未返回Curl命令')
        }
    } catch (error: any) {
        message.error(error.message || '导出Curl失败')
    }
}

// 加载系统提示词列表
const loadSystemPrompts = async () => {
    try {
        const res: any = await api.getSystemPromptList({ page: 1, page_size: 100 })
        const items = res?.data || []
        systemPromptOptions.value = items.map((s: any) => ({
            label: s.name,
            value: s.name
        }))
    } catch (error) {
        console.error('加载系统提示词失败:', error)
    }
}

onMounted(() => {
    loadRuleApps()
    loadSystemPrompts()
})
</script>

<style scoped lang="less">
.test-fill-page {
    padding: 20px;

    .test-fill-card {
        min-height: calc(100vh - 140px);
    }

    // 规则测试样式
    .rule-test-section {
        padding: 16px 0;
    }

    .params-section {
        margin-bottom: 24px;
    }

    .params-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;

        h4 {
            margin: 0;
        }
    }

    .param-item {
        margin-bottom: 16px;
    }

    .filter-conditions {
        .filter-row {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }
    }

    .rule-result {
        margin-bottom: 16px;
        padding: 12px;
        background-color: #f6ffed;
        border: 1px solid #b7eb8f;
        border-radius: 4px;

        h5 {
            margin: 0 0 8px 0;
            color: #52c41a;
        }
    }

    .result-content {
        p {
            margin: 4px 0;
        }
    }

    .execute-result {
        margin-top: 24px;
    }
}
</style>
