<template>
    <div class="dify-agent-page">
        <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
            :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
            :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
            modal-width="700px" @search="handleSearch" @reset="handleReset" @table-change="handleTableChange"
            @modal-ok="handleSave">
            <!-- 筛选条件 -->
            <template #filter-items>
                <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item label="Agent名称" class="filter-item">
                        <a-input v-model:value="queryParams.name" placeholder="请输入Agent名称" allow-clear
                            @pressEnter="handleSearch" />
                    </a-form-item>
                </a-col>
            </template>

            <!-- 操作按钮 -->
            <template #actions>
                <a-button v-permission="'post/api/v1/autofill/dify-agent/create'" type="primary" @click="handleAdd">
                    <PlusOutlined />
                    新建 Agent
                </a-button>
            </template>

            <!-- 表格列自定义 -->
            <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'is_active'">
                    <a-tag :color="record.is_active ? 'green' : 'red'">
                        {{ record.is_active ? '启用' : '禁用' }}
                    </a-tag>
                </template>
                <template v-if="column.key === 'api_key'">
                    <a-space>
                        <span>{{ maskApiKey(record.api_key) }}</span>
                        <a-button type="link" size="small" @click="copyApiKey(record.api_key)">
                            <CopyOutlined />
                        </a-button>
                    </a-space>
                </template>
                <template v-if="column.key === 'agent_url'">
                    <a-tooltip :title="record.agent_url">
                        <span class="ellipsis-text">{{ record.agent_url }}</span>
                    </a-tooltip>
                </template>
                <template v-if="column.key === 'created_at'">
                    <span v-if="record.created_at">{{ formatDateTime(record.created_at) }}</span>
                    <span v-else>-</span>
                </template>
                <template v-if="column.key === 'action'">
                    <a-space>
                        <a-button v-permission="'post/api/v1/autofill/dify-agent/update'" type="link" size="small"
                            @click="handleEdit(record)">编辑</a-button>
                        <a-popconfirm title="确定删除该 Agent 吗？" @confirm="handleDelete(record)">
                            <a-button v-permission="'delete/api/v1/autofill/dify-agent/delete'" type="link" danger
                                size="small">删除</a-button>
                        </a-popconfirm>
                    </a-space>
                </template>
            </template>

            <!-- 弹窗表单 -->
            <template #modal-form="{ form }">
                <a-form-item label="Agent名称" name="name">
                    <a-input v-model:value="form.name" placeholder="请输入Agent名称" />
                </a-form-item>
                <a-form-item label="API Key" name="api_key">
                    <a-input v-model:value="form.api_key" placeholder="请输入Dify API Key" />
                </a-form-item>
                <a-form-item label="Agent URL" name="agent_url">
                    <a-input v-model:value="form.agent_url"
                        placeholder="请输入Dify Agent URL，例如：https://api.dify.ai/v1/chat-messages" />
                </a-form-item>
                <a-form-item label="描述" name="description">
                    <a-textarea v-model:value="form.description" placeholder="请输入描述" :rows="3" />
                </a-form-item>
                <a-form-item label="状态" name="is_active">
                    <a-switch v-model:checked="form.is_active" />
                </a-form-item>
            </template>
        </CrudTable>
    </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { copyToClipboard, formatDateTime } from '@/utils'
import { CopyOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'DifyAgentPage' })

const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
    name: '',
})

// 表格数据
const loading = ref(false)
const tableData = ref<any[]>([])
const pagination = reactive({
    current: 1,
    pageSize: 10,
    total: 0,
})

// 表格列定义
const columns = [
    {
        title: 'ID',
        dataIndex: 'id',
        key: 'id',
        width: 80,
    },
    {
        title: 'Agent名称',
        dataIndex: 'name',
        key: 'name',
        width: 150,
    },
    {
        title: 'API Key',
        dataIndex: 'api_key',
        key: 'api_key',
        width: 200,
    },
    {
        title: 'Agent URL',
        dataIndex: 'agent_url',
        key: 'agent_url',
        width: 250,
    },
    {
        title: '描述',
        dataIndex: 'description',
        key: 'description',
        width: 150,
        ellipsis: true,
    },
    {
        title: '状态',
        dataIndex: 'is_active',
        key: 'is_active',
        width: 100,
    },
    {
        title: '创建时间',
        dataIndex: 'created_at',
        key: 'created_at',
        width: 180,
    },
    {
        title: '操作',
        key: 'action',
        fixed: 'right',
        width: 150,
    },
]

// 筛选项数量
const filterItemCount = computed(() => {
    let count = 0
    if (queryParams.name) count++
    return count
})

// 弹窗相关
const modalTitle = ref('')
const modalLoading = ref(false)
const modalAction = ref<'add' | 'edit'>('add')
const modalForm = reactive({
    id: 0,
    name: '',
    api_key: '',
    agent_url: '',
    description: '',
    is_active: true,
})

// 表单校验规则
const modalRules = {
    name: [{ required: true, message: '请输入Agent名称', trigger: 'blur' }],
    api_key: [{ required: true, message: '请输入API Key', trigger: 'blur' }],
    agent_url: [{ required: true, message: '请输入Agent URL', trigger: 'blur' }],
}

// 获取表格数据
const fetchData = async () => {
    loading.value = true
    try {
        const res: any = await api.getDifyAgentList({
            page: pagination.current,
            page_size: pagination.pageSize,
            name: queryParams.name,
        })
        if (res.code === 200) {
            tableData.value = res.data || []
            pagination.total = res.total || 0
        } else {
            message.error(res.msg || '获取列表失败')
        }
    } catch (error) {
        message.error('获取列表失败')
    } finally {
        loading.value = false
    }
}

// 搜索
const handleSearch = () => {
    pagination.current = 1
    fetchData()
}

// 重置
const handleReset = () => {
    queryParams.name = ''
    pagination.current = 1
    fetchData()
}

// 表格变化（分页、排序等）
const handleTableChange = (pag: any) => {
    pagination.current = pag.current
    pagination.pageSize = pag.pageSize
    fetchData()
}

// 新增
const handleAdd = () => {
    modalAction.value = 'add'
    modalTitle.value = '新建 Agent'
    modalForm.id = 0
    modalForm.name = ''
    modalForm.api_key = ''
    modalForm.agent_url = ''
    modalForm.description = ''
    modalForm.is_active = true
    crudTableRef.value?.openAddModal()
}

// 编辑
const handleEdit = (record: any) => {
    modalAction.value = 'edit'
    modalTitle.value = '编辑 Agent'
    modalForm.id = record.id
    modalForm.name = record.name
    modalForm.api_key = record.api_key
    modalForm.agent_url = record.agent_url
    modalForm.description = record.description
    modalForm.is_active = record.is_active
    crudTableRef.value?.openEditModal(record)
}

// 保存
const handleSave = async () => {
    modalLoading.value = true
    try {
        if (modalAction.value === 'add') {
            const res: any = await api.createDifyAgent({
                name: modalForm.name,
                api_key: modalForm.api_key,
                agent_url: modalForm.agent_url,
                description: modalForm.description,
                is_active: modalForm.is_active,
            })
            if (res.code === 200) {
                message.success('创建成功')
                crudTableRef.value?.closeModal()
                fetchData()
            } else {
                message.error(res.msg || '创建失败')
            }
        } else {
            const res: any = await api.updateDifyAgent({
                id: modalForm.id,
                name: modalForm.name,
                api_key: modalForm.api_key,
                agent_url: modalForm.agent_url,
                description: modalForm.description,
                is_active: modalForm.is_active,
            })
            if (res.code === 200) {
                message.success('更新成功')
                crudTableRef.value?.closeModal()
                fetchData()
            } else {
                message.error(res.msg || '更新失败')
            }
        }
    } catch (error: any) {
        message.error(error.message || '操作失败')
    } finally {
        modalLoading.value = false
    }
}

// 删除
const handleDelete = async (record: any) => {
    try {
        const res: any = await api.deleteDifyAgent({ id: record.id })
        if (res.code === 200) {
            message.success('删除成功')
            fetchData()
        } else {
            message.error(res.msg || '删除失败')
        }
    } catch (error: any) {
        message.error(error.message || '删除失败')
    }
}

// 复制 API Key
const copyApiKey = async (apiKey: string) => {
    try {
        await copyToClipboard(apiKey)
        message.success('已复制到剪贴板')
    } catch (error) {
        message.error('复制失败')
    }
}

// 隐藏 API Key
const maskApiKey = (apiKey: string) => {
    if (!apiKey) return ''
    if (apiKey.length <= 8) return apiKey
    return apiKey.substring(0, 4) + '****' + apiKey.substring(apiKey.length - 4)
}

onMounted(() => {
    fetchData()
})
</script>

<style scoped lang="less">
.dify-agent-page {
    padding: 20px;
}

.ellipsis-text {
    display: inline-block;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
</style>
