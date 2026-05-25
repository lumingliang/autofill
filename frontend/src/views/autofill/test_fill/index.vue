<template>
    <div class="test-fill-page">
        <a-card title="智能填单测试" class="test-fill-card">
            <a-tabs v-model:activeKey="activeTab" type="card">
                <!-- Tab 1: 规则执行测试 -->
                <a-tab-pane key="rule" tab="规则执行测试">
                    <div class="rule-test-section">
                        <a-form layout="vertical">
                            <!-- 第一行：租户选择（仅超级用户显示，必填）、应用选择 -->
                            <a-row :gutter="16">
                                <a-col :span="8" v-if="isSuperUser">
                                    <a-form-item label="租户" required>
                                        <a-select v-model:value="ruleForm.tenant_id" placeholder="请选择租户"
                                            :options="tenantOptions" @change="handleRuleTenantChange"
                                            style="width: 100%" allow-clear />
                                    </a-form-item>
                                </a-col>
                                <a-col :span="isSuperUser ? 8 : 12">
                                    <a-form-item label="应用" required>
                                        <a-select v-model:value="ruleForm.app_name" placeholder="请选择应用"
                                            :options="ruleAppOptions" :loading="loadingRuleApps"
                                            :disabled="isSuperUser && !ruleForm.tenant_id" style="width: 100%"
                                            @change="handleRuleAppChange" />
                                    </a-form-item>
                                </a-col>
                                <a-col :span="isSuperUser ? 8 : 12">
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
                </a-tab-pane>

                <!-- Tab 2: 聊天记录生成 -->
                <a-tab-pane key="chat" tab="聊天记录生成">
                    <div class="chat-section">
                        <!-- 系统提示词设置 -->
                        <a-card size="small" class="system-prompt-card">
                            <template #title>
                                <span>系统提示词设置</span>
                                <a-button type="link" size="small" @click="resetSystemPrompt">恢复默认</a-button>
                            </template>
                            <a-textarea v-model:value="chatSystemPrompt" :rows="4"
                                placeholder="请输入系统提示词，用于指导模型生成聊天记录" />
                        </a-card>

                        <!-- 聊天窗口 -->
                        <div class="chat-window">
                            <div class="chat-messages" ref="chatMessagesRef">
                                <div v-if="chatMessages.length === 0" class="chat-empty">
                                    <a-empty description="开始新对话，生成客服与用户的聊天记录" />
                                </div>
                                <div v-for="(msg, index) in chatMessages" :key="index" class="chat-message"
                                    :class="msg.role">
                                    <div class="message-avatar">
                                        <a-avatar
                                            :style="{ backgroundColor: msg.role === 'user' ? '#1890ff' : '#52c41a' }">
                                            {{ msg.role === 'user' ? '用' : '助' }}
                                        </a-avatar>
                                    </div>
                                    <div class="message-content">
                                        <div class="message-text">{{ msg.content }}</div>
                                        <div class="message-time" v-if="msg.timestamp">{{ formatTime(msg.timestamp) }}
                                        </div>
                                    </div>
                                </div>
                                <div v-if="chatLoading" class="chat-message assistant">
                                    <div class="message-avatar">
                                        <a-avatar style="background-color: #52c41a">助</a-avatar>
                                    </div>
                                    <div class="message-content">
                                        <a-spin size="small" />
                                    </div>
                                </div>
                            </div>

                            <!-- 聊天输入框 -->
                            <div class="chat-input-area">
                                <a-row :gutter="8">
                                    <a-col :span="20">
                                        <a-textarea v-model:value="chatInput" :rows="3"
                                            placeholder="输入消息，例如：帮我生成10轮道路救援的客服对话" @pressEnter="handleChatSend" />
                                    </a-col>
                                    <a-col :span="4">
                                        <a-space direction="vertical" style="width: 100%">
                                            <a-button type="primary" :loading="chatLoading" @click="handleChatSend"
                                                style="width: 100%">
                                                <SendOutlined />
                                                发送
                                            </a-button>
                                            <a-button @click="startNewChat" style="width: 100%">
                                                <PlusOutlined />
                                                新对话
                                            </a-button>
                                        </a-space>
                                    </a-col>
                                </a-row>
                            </div>
                        </div>

                        <!-- 操作按钮 -->
                        <a-divider />
                        <a-space>
                            <a-button type="primary" @click="copyChatToFillTab" :disabled="chatMessages.length === 0">
                                <CopyOutlined />
                                复制对话到填单测试
                            </a-button>
                            <a-button @click="exportChat" :disabled="chatMessages.length === 0">
                                <DownloadOutlined />
                                导出对话
                            </a-button>
                        </a-space>
                    </div>
                </a-tab-pane>

                <!-- Tab 3: 测试填单 -->
                <a-tab-pane key="fill" tab="测试填单">
                    <div class="test-fill-section">
                        <a-form layout="vertical">
                            <!-- 第一行：租户选择（仅超级用户显示）、应用名称 -->
                            <a-row :gutter="16">
                                <a-col :span="8" v-if="isSuperUser">
                                    <a-form-item label="租户">
                                        <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户"
                                            :options="tenantOptions" @change="handleTenantChange" style="width: 100%"
                                            allow-clear />
                                    </a-form-item>
                                </a-col>
                                <a-col :span="isSuperUser ? 8 : 12">
                                    <a-form-item label="应用名称" required>
                                        <a-select v-model:value="queryParams.app_name" placeholder="请选择应用"
                                            :options="appOptions" @change="handleAppChange" style="width: 100%" />
                                    </a-form-item>
                                </a-col>
                                <a-col :span="isSuperUser ? 8 : 12">
                                    <a-form-item label="指定System Prompt字段组">
                                        <a-select v-model:value="queryParams.system_prompt_group"
                                            placeholder="可选：指定使用哪个字段组的system_prompt" :options="groupOptions"
                                            style="width: 100%" allow-clear />
                                    </a-form-item>
                                </a-col>
                            </a-row>

                            <!-- 第二行：字段组名称（多选） -->
                            <a-row :gutter="16">
                                <a-col :span="24">
                                    <a-form-item label="字段组名称" required>
                                        <a-select v-model:value="fillForm.group_names" mode="multiple"
                                            placeholder="请选择字段组" :options="groupOptions" style="width: 100%"
                                            @change="handleGroupChange" />
                                    </a-form-item>
                                </a-col>
                            </a-row>

                            <!-- 第三行：字段名称（多选） -->
                            <a-row :gutter="16">
                                <a-col :span="24">
                                    <a-form-item label="字段名称">
                                        <a-select v-model:value="fillForm.field_names" mode="multiple"
                                            placeholder="请选择字段（不选则使用全部）" :options="fieldOptions" style="width: 100%" />
                                    </a-form-item>
                                </a-col>
                            </a-row>

                            <!-- 第四行：方法选择 -->
                            <a-row :gutter="16">
                                <a-col :span="24">
                                    <a-form-item label="方法">
                                        <a-select v-model:value="fillForm.method" placeholder="请选择方法（不选则使用默认）"
                                            :options="methodOptions" style="width: 100%" allow-clear />
                                    </a-form-item>
                                </a-col>
                            </a-row>

                            <a-form-item label="聊天记录" required>
                                <a-textarea v-model:value="fillForm.chat_record" :rows="12" placeholder="请输入客服与用户的对话记录，格式：
客服：您好，欢迎咨询...
用户：你好，我的车..." />
                            </a-form-item>

                            <a-form-item>
                                <a-button type="primary" size="large" :loading="filling" @click="handleTestFill">
                                    <ExperimentOutlined />
                                    执行填单测试
                                </a-button>
                            </a-form-item>
                        </a-form>

                        <a-divider v-if="fillResult" />

                        <!-- 填单结果 -->
                        <div v-if="fillResult" class="fill-result">
                            <a-card title="填单结果" size="small">
                                <a-descriptions :column="2" bordered size="small">
                                    <a-descriptions-item label="Session ID">{{ fillResult.data?.session_id
                                        }}</a-descriptions-item>
                                    <a-descriptions-item label="应用">{{ fillResult.data?.app_name
                                        }}</a-descriptions-item>
                                    <a-descriptions-item label="状态">
                                        <a-tag color="green">{{ fillResult.data?.status }}</a-tag>
                                    </a-descriptions-item>
                                    <a-descriptions-item label="用时">{{ fillResult.data?.elapsed_time?.toFixed(2)
                                        }}s</a-descriptions-item>
                                </a-descriptions>

                                <a-divider />

                                <h4>提取的字段值：</h4>
                                <a-table :dataSource="resultTableData" :columns="resultColumns" size="small"
                                    :pagination="false" />

                                <a-divider />

                                <h4>完整结果（JSON）：</h4>
                                <JsonViewer :data="fillResult" title="结果详情" :max-height="400" />
                            </a-card>
                        </div>
                    </div>
                </a-tab-pane>
            </a-tabs>
        </a-card>
    </div>
</template>

<script setup lang="ts">
import api from '@/api'
import JsonViewer from '@/components/JsonViewer/index.vue'
import { useUserStore } from '@/store/modules/user'
import { CopyOutlined, DownloadOutlined, ExperimentOutlined, PlayCircleOutlined, PlusOutlined, SendOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, nextTick, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'TestFillPage' })

// 当前激活的Tab
const activeTab = ref('rule')

// ==================== 用户相关 ====================
const userStore = useUserStore()
const isSuperUser = computed(() => userStore.isSuperUser)

// 租户选项
const tenantOptions = ref<{ label: string; value: number }[]>([])

// 加载租户列表
const loadTenants = async () => {
    if (!isSuperUser.value && !userStore.isTenantAdmin) return
    try {
        const res: any = await api.getTenantSelect()
        tenantOptions.value = (res.data || []).map((item: any) => ({ label: item.name, value: item.id }))
    } catch (error) {
        console.error('加载租户失败:', error)
    }
}

// ==================== Tab 1: 规则执行测试 ====================
const ruleForm = reactive({
    tenant_id: undefined as number | undefined,
    app_name: '',
    query: '',
    system_prompt_name: undefined as string | undefined,  // 全局系统提示词（多个规则共用）
    params: [
        {
            rule_name: '',
            prompt: {
                type: 'choice',
                filter: {} as Record<string, string>,
                select_fields: [] as string[],
                name_fields: [] as string[],
                rule_fields: [] as string[]
            },
            columnOptions: [] as { label: string; value: string }[],
            sampleData: [] as any[],
            sampleColumns: [] as any[],
            filterConditions: [] as { column: string; value: string }[]
        }
    ] as any[]
})

const ruleAppOptions = ref<{ label: string; value: string }[]>([])
const loadingRuleApps = ref(false)
const ruleOptions = ref<{ label: string; value: string }[]>([])
const loadingRules = ref(false)
const ruleExecuting = ref(false)
const ruleExecuteResult = ref<any>(null)

// 系统提示词选项
const systemPromptOptions = ref<{ label: string; value: string }[]>([])

// 加载系统提示词列表
const loadSystemPrompts = async () => {
    try {
        const tenantId = isSuperUser.value ? ruleForm.tenant_id : undefined
        const params: any = { page: 1, page_size: 100 }
        if (tenantId) {
            params.tenant_id = tenantId
        }
        const res: any = await api.getSystemPromptList(params)
        if (res.code === 200) {
            // API返回的数据格式：{ data: [...], total: n } 或 { data: { items: [...] } }
            const items = res.data?.items || res.data || []
            systemPromptOptions.value = items.map((item: any) => ({
                label: item.name,
                value: item.name
            }))
        }
    } catch (error) {
        console.error('加载系统提示词失败:', error)
    }
}

// 加载规则测试应用列表
const loadRuleApps = async () => {
    loadingRuleApps.value = true
    try {
        const res: any = await api.getRuleTestApps()
        if (res.code === 200) {
            ruleAppOptions.value = res.data.map((app: any) => ({
                label: app.app_name_cn || app.app_name,
                value: app.app_name
            }))
        }
    } catch (error: any) {
        message.error(error.message || '加载应用列表失败')
    } finally {
        loadingRuleApps.value = false
    }
}

// 规则测试租户变更处理
const handleRuleTenantChange = async (tenantId: number) => {
    ruleForm.app_name = ''
    ruleForm.system_prompt_name = undefined  // 清空系统提示词选择
    ruleForm.params.forEach(param => {
        param.rule_name = ''
        param.columnOptions = []
        param.sampleData = []
        param.sampleColumns = []
        param.filterConditions = []
        param.prompt.filter = {}
        param.prompt.select_fields = []
        param.prompt.name_fields = []
        param.prompt.rule_fields = []
    })
    ruleOptions.value = []

    if (!tenantId) {
        ruleAppOptions.value = []
        systemPromptOptions.value = []  // 清空系统提示词列表
        return
    }

    // 租户变更时重新加载系统提示词列表
    await loadSystemPrompts()

    // 超级管理员根据租户过滤应用
    loadingRuleApps.value = true
    try {
        const params: any = { page: 1, page_size: 100, tenant_id: tenantId }
        const res: any = await api.getAppList(params)
        const items = res?.data?.items || res?.data || []
        ruleAppOptions.value = items.map((a: any) => ({
            label: a.app_name_cn || a.app_name,
            value: a.app_name
        }))
    } catch (error) {
        console.error('加载应用失败:', error)
    } finally {
        loadingRuleApps.value = false
    }

    // 租户变更时重新加载系统提示词
    await loadSystemPrompts()
}

// 规则测试应用变更处理
const handleRuleAppChange = async (appName: string) => {
    ruleForm.params.forEach(param => {
        param.rule_name = ''
        param.columnOptions = []
        param.sampleData = []
        param.sampleColumns = []
        param.filterConditions = []
        param.prompt.filter = {}
        param.prompt.select_fields = []
        param.prompt.name_fields = []
        param.prompt.rule_fields = []
    })

    if (!appName) {
        ruleOptions.value = []
        return
    }

    // 加载规则列表
    loadingRules.value = true
    try {
        const res: any = await api.getRuleTestRules({ app_name: appName })
        if (res.code === 200) {
            ruleOptions.value = res.data.map((rule: any) => ({
                label: rule.rule_name || rule.rule_code,
                value: rule.rule_code
            }))
        }
    } catch (error: any) {
        message.error(error.message || '加载规则列表失败')
    } finally {
        loadingRules.value = false
    }
}

// 规则变更处理
const handleRuleChange = async (ruleCode: string, paramIndex: number) => {
    const param = ruleForm.params[paramIndex]
    param.columnOptions = []
    param.sampleData = []
    param.sampleColumns = []
    param.filterConditions = []
    param.prompt.filter = {}
    param.prompt.select_fields = []
    param.prompt.name_fields = []
    param.prompt.rule_fields = []

    if (!ruleCode || !ruleForm.app_name) return

    try {
        const res: any = await api.getRuleTestColumns({
            rule_code: ruleCode,
            app_name: ruleForm.app_name
        })

        if (res.code === 200) {
            const columns = res.data.columns || []
            param.columnOptions = columns.map((col: string) => ({
                label: col,
                value: col
            }))

            // 设置示例数据
            if (res.data.sample_data && res.data.sample_data.length > 0) {
                param.sampleColumns = columns.map((col: string, idx: number) => ({
                    title: col,
                    dataIndex: `col_${idx}`,
                    key: `col_${idx}`,
                    ellipsis: true
                }))

                param.sampleData = res.data.sample_data.map((row: string[], rowIdx: number) => {
                    const rowData: any = { key: rowIdx }
                    row.forEach((cell, cellIdx) => {
                        rowData[`col_${cellIdx}`] = cell
                    })
                    return rowData
                })
            }
        }
    } catch (error: any) {
        message.error(error.message || '加载规则表头失败')
    }
}

// 添加Filter条件
const addFilterCondition = (paramIndex: number) => {
    ruleForm.params[paramIndex].filterConditions.push({ column: '', value: '' })
}

// 删除Filter条件
const removeFilterCondition = (paramIndex: number, filterIndex: number) => {
    ruleForm.params[paramIndex].filterConditions.splice(filterIndex, 1)
}

// 添加规则参数
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
        columnOptions: [],
        sampleData: [],
        sampleColumns: [],
        filterConditions: []
    })
}

// 删除规则参数
const removeRuleParam = (index: number) => {
    ruleForm.params.splice(index, 1)
}

// 执行规则测试
const handleRuleExecute = async () => {
    // 超管必须选择租户
    if (isSuperUser.value && !ruleForm.tenant_id) {
        message.error('请选择租户')
        return
    }
    if (!ruleForm.app_name) {
        message.error('请选择应用')
        return
    }
    if (!ruleForm.query) {
        message.error('请输入用户输入')
        return
    }

    // 验证规则参数并构建filter
    for (let i = 0; i < ruleForm.params.length; i++) {
        const param = ruleForm.params[i]
        if (!param.rule_name) {
            message.error(`规则 ${i + 1} 的名称不能为空`)
            return
        }

        // 构建filter对象
        const filter: Record<string, string> = {}
        param.filterConditions.forEach((cond: { column: string; value: string }) => {
            if (cond.column && cond.value) {
                filter[cond.column] = cond.value
            }
        })
        param.prompt.filter = filter
    }

    ruleExecuting.value = true
    ruleExecuteResult.value = null

    try {
        // 构建请求参数
        const params = ruleForm.params.map(p => ({
            rule_name: p.rule_name,
            prompt: {
                type: p.prompt.type,
                filter: p.prompt.filter,
                select_fields: p.prompt.select_fields,
                name_fields: p.prompt.name_fields,
                rule_fields: p.prompt.rule_fields
            }
        }))

        const requestData: any = {
            app_name: ruleForm.app_name,
            query: ruleForm.query,
            params: params
        }

        // 超级用户传递tenant_id
        if (isSuperUser.value && ruleForm.tenant_id) {
            requestData.tenant_id = ruleForm.tenant_id
        }

        // 添加全局系统提示词（多个规则共用）
        if (ruleForm.system_prompt_name) {
            requestData.system_prompt_name = ruleForm.system_prompt_name
        }

        const res: any = await api.executeRuleTest(requestData)
        ruleExecuteResult.value = res

        if (res.code === 200) {
            message.success('执行成功')
        } else {
            message.error(res.msg || '执行失败')
        }
    } catch (error: any) {
        message.error(error.response?.data?.detail || error.message || '执行失败')
    } finally {
        ruleExecuting.value = false
    }
}

// 导出 Curl 命令
const handleExportCurl = async () => {
    // 验证表单
    if (isSuperUser.value && !ruleForm.tenant_id) {
        message.error('请选择租户')
        return
    }
    if (!ruleForm.app_name) {
        message.error('请选择应用')
        return
    }
    if (!ruleForm.query) {
        message.error('请输入用户输入')
        return
    }

    // 验证规则参数
    for (let i = 0; i < ruleForm.params.length; i++) {
        const param = ruleForm.params[i]
        if (!param.rule_name) {
            message.error(`规则 ${i + 1} 的名称不能为空`)
            return
        }
    }

    // 构建请求参数
    const params = ruleForm.params.map(p => {
        const filter: Record<string, string> = {}
        p.filterConditions.forEach((cond: { column: string; value: string }) => {
            if (cond.column && cond.value) {
                filter[cond.column] = cond.value
            }
        })
        return {
            rule_name: p.rule_name,
            prompt: {
                type: p.prompt.type,
                filter: filter,
                select_fields: p.prompt.select_fields,
                name_fields: p.prompt.name_fields,
                rule_fields: p.prompt.rule_fields,
                name_separator: p.prompt.name_separator
            }
        }
    })

    // 构建请求体
    const requestData: any = {
        app_name: ruleForm.app_name,
        query: ruleForm.query,
        params: params
    }

    // 超级用户传递tenant_id
    if (isSuperUser.value && ruleForm.tenant_id) {
        requestData.tenant_id = ruleForm.tenant_id
    }

    // 添加全局系统提示词（多个规则共用）
    if (ruleForm.system_prompt_name) {
        requestData.system_prompt_name = ruleForm.system_prompt_name
    }

    try {
        const res: any = await api.exportRuleTestCurl(requestData)
        if (res.code === 200 && res.data?.curl_command) {
            // 复制到剪贴板
            navigator.clipboard.writeText(res.data.curl_command).then(() => {
                message.success('Curl 命令已复制到剪贴板')
            }).catch(() => {
                message.error('复制失败，请手动复制')
                console.log(res.data.curl_command)
            })
        } else {
            message.error(res.msg || '导出失败')
        }
    } catch (error: any) {
        message.error(error.response?.data?.detail || error.message || '导出失败')
    }
}

// ==================== Tab 2: 聊天记录生成 ====================
const DEFAULT_SYSTEM_PROMPT = `你是一个专业的客服对话生成专家。请根据用户的要求生成真实的客服与用户的对话记录。

生成要求：
1. 对话格式：每轮对话包含"客服："和"用户："两部分
2. 对话内容要真实自然，符合实际客服场景
3. 用户问题要具体、有细节
4. 客服回复要专业、有帮助
5. 对话要有逻辑连贯性，前后呼应
6. 严格按照用户要求的轮数生成

输出格式示例：
客服：您好，欢迎咨询，请问有什么可以帮您？
用户：你好，我的车出了点问题。
客服：请问是什么车型？具体什么问题？
用户：比亚迪汉EV，突然无法启动了。
...

请根据用户的要求生成对话记录。`

const chatSystemPrompt = ref(DEFAULT_SYSTEM_PROMPT)
const chatSessionId = ref('')
const chatMessages = ref<{ role: string; content: string; timestamp?: string }[]>([])
const chatInput = ref('')
const chatLoading = ref(false)
const chatMessagesRef = ref<HTMLElement>()

const resetSystemPrompt = () => {
    chatSystemPrompt.value = DEFAULT_SYSTEM_PROMPT
    message.success('已恢复默认提示词')
}

const scrollToBottom = () => {
    nextTick(() => {
        if (chatMessagesRef.value) {
            chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
        }
    })
}

const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const handleChatSend = async () => {
    if (!chatInput.value.trim()) {
        message.warning('请输入消息')
        return
    }

    const userMessage = chatInput.value.trim()
    chatInput.value = ''
    chatLoading.value = true

    chatMessages.value.push({
        role: 'user',
        content: userMessage,
        timestamp: new Date().toISOString()
    })
    scrollToBottom()

    try {
        const res: any = await api.testFillChat({
            session_id: chatSessionId.value || undefined,
            system_prompt: chatSystemPrompt.value,
            message: userMessage
        })

        const data = res?.data || {}
        chatSessionId.value = data?.session_id || ''
        chatMessages.value = data?.history || []
        scrollToBottom()
    } catch (error: any) {
        message.error(error.message || '发送失败')
    } finally {
        chatLoading.value = false
    }
}

const startNewChat = () => {
    chatSessionId.value = ''
    chatMessages.value = []
    chatInput.value = ''
    message.success('已开始新对话')
}

const copyChatToFillTab = () => {
    if (chatMessages.value.length === 0) return

    const chatText = chatMessages.value.map(msg => {
        if (msg.role === 'user') {
            return `用户：${msg.content}`
        } else {
            return `客服：${msg.content}`
        }
    }).join('\n\n')

    fillForm.chat_record = chatText
    activeTab.value = 'fill'
    message.success('已复制到填单测试')
}

const exportChat = () => {
    if (chatMessages.value.length === 0) return

    const chatText = chatMessages.value.map(msg => {
        const time = msg.timestamp ? `[${formatTime(msg.timestamp)}] ` : ''
        const role = msg.role === 'user' ? '用户' : '助手'
        return `${time}${role}：${msg.content}`
    }).join('\n\n')

    const blob = new Blob([chatText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `chat_${chatSessionId.value || 'new'}_${new Date().toISOString().slice(0, 10)}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    message.success('已导出对话')
}

// ==================== Tab 3: 测试填单 ====================
const queryParams = reactive({
    tenant_id: undefined as number | undefined,
    app_name: undefined as string | undefined,
    system_prompt_group: undefined as string | undefined,
})

const fillForm = reactive({
    group_names: [] as string[],
    field_names: [] as string[],
    method: undefined as string | undefined,
    chat_record: ''
})

const appOptions = ref<{ label: string; value: string }[]>([])
const groupOptions = ref<{ label: string; value: string }[]>([])
const fieldOptions = ref<{ label: string; value: string }[]>([])
const allFieldSpecs = ref<any[]>([])

// 方法选项
const methodOptions = ref<{ label: string; value: string }[]>([
    { label: 'with_structured_output', value: 'with_structured_output' },
    { label: 'bind_tools_non_stream', value: 'bind_tools_non_stream' },
    { label: 'bind_tools_stream', value: 'bind_tools_stream' },
    { label: 'custom_fc_non_stream', value: 'custom_fc_non_stream' },
    { label: 'custom_fc_stream', value: 'custom_fc_stream' },
    { label: 'pydantic_parser', value: 'pydantic_parser' },
    { label: 'json_parser', value: 'json_parser' },
    { label: 'plain', value: 'plain' }
])

const filling = ref(false)
const fillResult = ref<any>(null)

const resultColumns = [
    { title: '字段名', dataIndex: 'field_name', key: 'field_name' },
    { title: '字段标签', dataIndex: 'field_label', key: 'field_label' },
    { title: '字段类型', dataIndex: 'field_type', key: 'field_type' },
    { title: '提取值', dataIndex: 'value', key: 'value' }
]

const resultTableData = computed(() => {
    // 适配新的返回结构：使用 fields 替代 result
    const fields = fillResult.value?.data?.fields
    if (!fields) return []

    return Object.entries(fields).map(([key, value]: [string, any]) => {
        // 多选类型：value 和 labels 都是数组
        if (value?.type === 'select_multi' && Array.isArray(value?.labels)) {
            return {
                field_name: key,
                field_label: value?.label || key,
                field_type: value?.type || 'text',
                value: value.labels.join(', ')  // 表格中用逗号分隔显示
            }
        }
        // 单选或其他类型
        return {
            field_name: key,
            field_label: value?.label || key,
            field_type: value?.type || 'text',
            value: value?.value !== undefined ? value.value : (typeof value === 'object' ? JSON.stringify(value) : value)
        }
    })
})

// 租户变化处理
const handleTenantChange = async (tenantId: number) => {
    // 重置所有下级选择
    queryParams.app_name = undefined
    queryParams.system_prompt_group = undefined
    fillForm.group_names = []
    fillForm.field_names = []
    fillForm.method = undefined
    groupOptions.value = []
    fieldOptions.value = []
    allFieldSpecs.value = []
    // 加载应用列表
    await loadApps()
}

// 加载应用列表
const loadApps = async () => {
    try {
        const params: any = { page: 1, page_size: 100 }
        // 超级用户选择了租户时，按租户过滤应用
        if (isSuperUser.value && queryParams.tenant_id) {
            params.tenant_id = queryParams.tenant_id
        }
        const res: any = await api.getAppList(params)
        const items = res?.data?.items || res?.data || []
        appOptions.value = items.map((a: any) => ({
            label: a.app_name,
            value: a.app_name
        }))
    } catch (error) {
        console.error('加载应用失败:', error)
    }
}

// 应用变化时加载字段组
const handleAppChange = async (appName: string) => {
    queryParams.system_prompt_group = undefined
    fillForm.group_names = []
    fillForm.field_names = []
    fillForm.method = undefined
    groupOptions.value = []
    fieldOptions.value = []
    allFieldSpecs.value = []

    if (!appName) return

    try {
        const params: any = {
            app_name: appName,
            page: 1,
            page_size: 100
        }
        if (isSuperUser.value && queryParams.tenant_id) {
            params.tenant_id = queryParams.tenant_id
        }
        const res: any = await api.getFieldGroupList(params)
        const items = res?.data?.items || res?.data || []
        groupOptions.value = items.map((g: any) => ({
            label: g.group_name,
            value: g.group_name
        }))
    } catch (error) {
        console.error('加载字段组失败:', error)
    }
}

// 字段组变化时加载字段
const handleGroupChange = async (groupNames: string[]) => {
    fillForm.field_names = []
    fillForm.method = undefined
    fieldOptions.value = []
    allFieldSpecs.value = []

    if (!groupNames || groupNames.length === 0 || !queryParams.app_name) return

    try {
        // 获取所有选中字段组的字段
        const allFields: any[] = []
        for (const groupName of groupNames) {
            const res: any = await api.getFieldGroupDetailByName({
                app_name: queryParams.app_name,
                group_name: groupName
            })
            const fieldSpecs = res?.data?.field_specs || []
            allFields.push(...fieldSpecs)
        }
        allFieldSpecs.value = allFields
        fieldOptions.value = allFields.map((f: any) => ({
            label: `${f.field_label || f.field_name} (${f.field_name})`,
            value: f.field_name
        }))
    } catch (error) {
        console.error('加载字段失败:', error)
    }
}

const handleTestFill = async () => {
    if (!queryParams.app_name) {
        message.warning('请选择应用')
        return
    }
    if (!fillForm.group_names || fillForm.group_names.length === 0) {
        message.warning('请选择字段组')
        return
    }
    if (!fillForm.chat_record.trim()) {
        message.warning('请输入聊天记录')
        return
    }

    filling.value = true
    fillResult.value = null

    try {
        const requestData: any = {
            app_name: queryParams.app_name,
            group_names: fillForm.group_names,
            field_names: fillForm.field_names.length > 0 ? fillForm.field_names : undefined,
            system_prompt_group: queryParams.system_prompt_group,
            chat_record: fillForm.chat_record,
            method: fillForm.method
        }

        // 超级用户传递tenant_id
        if (isSuperUser.value && queryParams.tenant_id) {
            requestData.tenant_id = queryParams.tenant_id
        }

        const data: any = await api.testFill(requestData)

        fillResult.value = data
        message.success('填单测试成功')
    } catch (error: any) {
        message.error(error.message || '填单测试失败')
    } finally {
        filling.value = false
    }
}

onMounted(() => {
    loadTenants()
    loadApps()
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

    // 聊天界面样式
    .chat-section {
        padding: 16px 0;
    }

    .system-prompt-card {
        margin-bottom: 16px;

        :deep(.ant-card-head) {
            padding: 0 16px;
            min-height: 40px;

            .ant-card-head-title {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
        }
    }

    .chat-window {
        border: 1px solid #e8e8e8;
        border-radius: 8px;
        overflow: hidden;
    }

    .chat-messages {
        height: 400px;
        overflow-y: auto;
        padding: 16px;
        background-color: #f5f5f5;

        .chat-empty {
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .chat-message {
            display: flex;
            margin-bottom: 16px;

            &.user {
                flex-direction: row-reverse;

                .message-content {
                    margin-right: 12px;
                    margin-left: 0;
                    background-color: #1890ff;
                    color: white;
                }
            }

            &.assistant {
                .message-content {
                    background-color: white;
                }
            }

            .message-avatar {
                flex-shrink: 0;
            }

            .message-content {
                max-width: 70%;
                margin-left: 12px;
                padding: 12px 16px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

                .message-text {
                    white-space: pre-wrap;
                    word-break: break-word;
                }

                .message-time {
                    margin-top: 4px;
                    font-size: 12px;
                    opacity: 0.7;
                    text-align: right;
                }
            }
        }
    }

    .chat-input-area {
        padding: 16px;
        background-color: white;
        border-top: 1px solid #e8e8e8;
    }

    // 填单测试样式
    .test-fill-section {
        padding: 16px 0;
    }

    .fill-result {
        margin-top: 24px;
    }
}
</style>
