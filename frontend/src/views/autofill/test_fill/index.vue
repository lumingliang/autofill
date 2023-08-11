<template>
    <div class="test-fill-page">
        <a-card title="智能填单测试" class="test-fill-card">
            <a-tabs v-model:activeKey="activeTab" type="card">
                <!-- Tab 1: 聊天记录生成 -->
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

                <!-- Tab 2: 测试填单 -->
                <a-tab-pane key="fill" tab="测试填单">
                    <div class="test-fill-section">
                        <a-form layout="vertical">
                            <!-- 第一行：租户选择（仅超级用户显示）、应用名称、页面名称 -->
                            <a-row :gutter="16">
                                <a-col :span="8" v-if="isSuperUser">
                                    <a-form-item label="租户">
                                        <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户"
                                            :options="tenantOptions" @change="handleTenantChange" style="width: 100%"
                                            allow-clear />
                                    </a-form-item>
                                </a-col>
                                <a-col :span="8">
                                    <a-form-item label="应用名称" required>
                                        <a-select v-model:value="queryParams.app_id" placeholder="请选择应用"
                                            :options="appOptions" @change="handleAppChange" style="width: 100%" />
                                    </a-form-item>
                                </a-col>
                                <a-col :span="8">
                                    <a-form-item label="页面名称" required>
                                        <a-select v-model:value="queryParams.page_id" placeholder="请选择页面"
                                            :options="pageOptions" @change="handlePageChange" style="width: 100%" />
                                    </a-form-item>
                                </a-col>
                            </a-row>
                            <!-- 第二行：字段组名称 -->
                            <a-row :gutter="16">
                                <a-col :span="8">
                                    <a-form-item label="字段组名称" required>
                                        <a-select v-model:value="queryParams.group_id" placeholder="请选择字段组"
                                            :options="groupOptions" @change="handleGroupChange" style="width: 100%" />
                                    </a-form-item>
                                </a-col>
                            </a-row>

                            <!-- 第二行：字段名称（多选） -->
                            <a-row :gutter="16">
                                <a-col :span="24">
                                    <a-form-item label="字段名称">
                                        <a-select v-model:value="fillForm.field_ids" mode="multiple"
                                            placeholder="请选择字段（不选则使用全部）" :options="fieldOptions" style="width: 100%" />
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
                                    <a-descriptions-item label="Session ID">{{ fillResult.session_id
                                    }}</a-descriptions-item>
                                    <a-descriptions-item label="页面">{{ fillResult.page_name }}</a-descriptions-item>
                                    <a-descriptions-item label="状态">
                                        <a-tag color="green">{{ fillResult.status }}</a-tag>
                                    </a-descriptions-item>
                                    <a-descriptions-item label="用时">{{ fillResult.elapsed_time?.toFixed(2)
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
import { CopyOutlined, DownloadOutlined, ExperimentOutlined, PlusOutlined, SendOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, nextTick, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'TestFillPage' })

// 当前激活的Tab
const activeTab = ref('chat')

// ==================== Tab 1: 聊天记录生成 ====================
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

// ==================== Tab 2: 测试填单 ====================
// 用户store
const userStore = useUserStore()
const isSuperUser = computed(() => userStore.isSuperUser)

// 查询参数（参考system/user页面的模式）
const queryParams = reactive({
    tenant_id: undefined as number | undefined,
    app_id: undefined as number | undefined,
    page_id: undefined as number | undefined,
    group_id: undefined as number | undefined,
})

const tenantOptions = ref<{ label: string; value: number }[]>([])

const fillForm = reactive({
    field_ids: [] as number[],
    chat_record: ''
})

const appOptions = ref<{ label: string; value: number }[]>([])
const pageOptions = ref<{ label: string; value: number }[]>([])
const groupOptions = ref<{ label: string; value: number }[]>([])
const fieldOptions = ref<{ label: string; value: number }[]>([])
const allFieldSpecs = ref<any[]>([])

const filling = ref(false)
const fillResult = ref<any>(null)

const resultColumns = [
    { title: '字段名', dataIndex: 'field_name', key: 'field_name' },
    { title: '字段标签', dataIndex: 'field_label', key: 'field_label' },
    { title: '字段类型', dataIndex: 'field_type', key: 'field_type' },
    { title: '提取值', dataIndex: 'value', key: 'value' }
]

const resultTableData = computed(() => {
    if (!fillResult.value?.result) return []

    return Object.entries(fillResult.value.result).map(([key, value]: [string, any]) => ({
        field_name: key,
        field_label: value?.field_label || key,
        field_type: value?.field_type || 'text',
        value: typeof value === 'object' ? JSON.stringify(value) : value
    }))
})

// 加载租户列表（超级管理员和租户管理员都需要）
const loadTenants = async () => {
    if (!isSuperUser.value && !userStore.isTenantAdmin) return
    try {
        const res: any = await api.getTenantSelect()
        tenantOptions.value = (res.data || []).map((item: any) => ({ label: item.name, value: item.id }))
    } catch (error) {
        console.error('加载租户失败:', error)
    }
}

// 租户变化处理（参考system/user页面的模式，只作为查询条件，不切换当前租户）
const handleTenantChange = async (tenantId: number) => {
    // 重置所有下级选择
    queryParams.app_id = undefined
    queryParams.page_id = undefined
    queryParams.group_id = undefined
    fillForm.field_ids = []
    appOptions.value = []
    pageOptions.value = []
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
            value: a.id
        }))
    } catch (error) {
        console.error('加载应用失败:', error)
    }
}

// 应用变化时加载页面
const handleAppChange = async (appId: number) => {
    queryParams.page_id = undefined
    queryParams.group_id = undefined
    fillForm.field_ids = []
    pageOptions.value = []
    groupOptions.value = []
    fieldOptions.value = []
    allFieldSpecs.value = []

    if (!appId) return

    try {
        const params: any = { page: 1, page_size: 100 }
        if (isSuperUser.value && queryParams.tenant_id) {
            params.tenant_id = queryParams.tenant_id
        }
        const res: any = await api.getPageList({ app_id: appId, ...params })
        const items = res?.data?.items || res?.data || []
        pageOptions.value = items.map((p: any) => ({
            label: p.page_name,
            value: p.id
        }))
    } catch (error) {
        console.error('加载页面失败:', error)
    }
}

// 页面变化时加载字段组
const handlePageChange = async (pageId: number) => {
    queryParams.group_id = undefined
    fillForm.field_ids = []
    groupOptions.value = []
    fieldOptions.value = []
    allFieldSpecs.value = []

    if (!pageId || !queryParams.app_id) return

    try {
        const res: any = await api.getFieldGroupList({
            page_id: pageId,
            page: 1,
            page_size: 100
        })
        const items = res?.data?.items || res?.data || []
        groupOptions.value = items.map((g: any) => ({
            label: g.group_name,
            value: g.id
        }))
    } catch (error) {
        console.error('加载字段组失败:', error)
    }
}

// 字段组变化时加载字段
const handleGroupChange = async (groupId: number) => {
    fillForm.field_ids = []
    fieldOptions.value = []
    allFieldSpecs.value = []

    if (!groupId || !queryParams.app_id || !queryParams.page_id) return

    try {
        const res: any = await api.getFieldSpecsByGroup({ field_group_id: groupId })
        const fieldSpecs = res?.data || []
        allFieldSpecs.value = fieldSpecs
        fieldOptions.value = fieldSpecs.map((f: any) => ({
            label: `${f.field_label || f.field_name} (${f.field_name})`,
            value: f.id
        }))
    } catch (error) {
        console.error('加载字段失败:', error)
    }
}

const handleTestFill = async () => {
    if (!queryParams.app_id) {
        message.warning('请选择应用')
        return
    }
    if (!queryParams.page_id) {
        message.warning('请选择页面')
        return
    }
    if (!queryParams.group_id) {
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
        // 构建字段ID列表
        const fieldIdsToUse = fillForm.field_ids.length > 0
            ? fillForm.field_ids
            : allFieldSpecs.value.map(f => f.id)

        const requestData: any = {
            app_id: queryParams.app_id,
            page_id: queryParams.page_id,
            group_id: queryParams.group_id,
            field_ids: fieldIdsToUse,
            chat_record: fillForm.chat_record
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
})
</script>

<style scoped lang="less">
.test-fill-page {
    padding: 20px;

    .test-fill-card {
        min-height: calc(100vh - 140px);
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
    }

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
                margin-left: 0;
                margin-right: 12px;
                background-color: #1890ff;
                color: white;
                border-radius: 12px 12px 0 12px;
            }
        }

        &.assistant {
            .message-content {
                background-color: white;
                border-radius: 12px 12px 12px 0;
            }
        }
    }

    .message-content {
        margin-left: 12px;
        padding: 12px 16px;
        max-width: 70%;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .message-text {
        white-space: pre-wrap;
        word-break: break-word;
    }

    .message-time {
        font-size: 12px;
        margin-top: 4px;
        opacity: 0.7;
    }

    .chat-input-area {
        padding: 16px;
        background-color: white;
        border-top: 1px solid #e8e8e8;
    }

    // 填单结果样式
    .fill-result {
        margin-top: 16px;
    }
}
</style>
