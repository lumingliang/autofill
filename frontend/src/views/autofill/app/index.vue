<template>
    <a-layout class="app-page crud-page">
        <a-layout-content style="padding: 16px">
            <a-card>
                <a-form :model="queryParams" class="crud-filter-form smart-filter-form">
                    <a-row :gutter="16" class="filter-row">
                        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                            <a-form-item label="应用名称" class="filter-item">
                                <a-input v-model:value="queryParams.app_name" placeholder="请输入应用名称" allow-clear
                                    @pressEnter="handleSearch" />
                            </a-form-item>
                        </a-col>
                        <a-col v-if="userStore.isSuperUser" :xs="24" :sm="12" :md="8" :lg="6" :xl="6"
                            class="filter-item-col">
                            <a-form-item label="租户" class="filter-item">
                                <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户" allow-clear
                                    :options="tenantOptions" @change="handleSearch" />
                            </a-form-item>
                        </a-col>
                        <a-col v-bind="getActionColProps" class="filter-actions-col"
                            :class="filterItemCount <= 2 ? 'single-line' : 'multi-line'">
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

                <div class="table-actions">
                    <a-button v-permission="'post/api/v1/autofill/app/create'" type="primary" @click="handleAdd">
                        <PlusOutlined />
                        新建应用
                    </a-button>
                </div>

                <a-table class="crud-table" :columns="columns" :data-source="tableData" :loading="loading"
                    :pagination="pagination" row-key="id" :scroll="{ x: 'max-content' }" @change="handleTableChange">
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
                        <template v-if="column.key === 'created_at'">
                            <span v-if="record.created_at">{{ formatDateTime(record.created_at) }}</span>
                            <span v-else>-</span>
                        </template>
                        <template v-if="column.key === 'action'">
                            <a-space>
                                <a-button v-permission="'post/api/v1/autofill/app/update'" type="link" size="small"
                                    @click="handleEdit(record)">编辑</a-button>
                                <a-popconfirm title="确定删除该应用吗？" @confirm="handleDelete(record)">
                                    <a-button v-permission="'delete/api/v1/autofill/app/delete'" type="link" danger
                                        size="small">删除</a-button>
                                </a-popconfirm>
                            </a-space>
                        </template>
                    </template>
                </a-table>
            </a-card>

            <!-- 新增/编辑 弹窗 -->
            <a-modal v-model:open="modalVisible" :title="modalTitle" :confirm-loading="modalLoading" @ok="handleSave"
                @cancel="modalVisible = false" width="700px">
                <a-form ref="modalFormRef" :model="modalForm" :rules="modalRules" :label-col="{ span: 6 }"
                    :wrapper-col="{ span: 16 }">
                    <a-form-item label="应用名称" name="app_name">
                        <a-input v-model:value="modalForm.app_name" placeholder="请输入应用名称（英文、数字、下划线）"
                            :disabled="modalAction === 'edit'" />
                    </a-form-item>
                    <a-form-item v-if="userStore.isSuperUser" label="租户" name="tenant_id">
                        <a-select v-model:value="modalForm.tenant_id" placeholder="请选择租户" :options="tenantOptions" />
                    </a-form-item>
                    <a-form-item label="Dify服务地址" name="dify_url">
                        <a-input v-model:value="modalForm.dify_url"
                            placeholder="请输入Dify服务地址，如：https://dify.example.com/v1" />
                    </a-form-item>
                    <a-form-item label="Dify API Key" name="dify_api_key">
                        <a-input-password v-model:value="modalForm.dify_api_key" placeholder="请输入Dify API Key" />
                    </a-form-item>
                    <a-form-item label="应用描述" name="description">
                        <a-textarea v-model:value="modalForm.description" placeholder="请输入应用描述" :rows="3" />
                    </a-form-item>
                    <a-form-item label="状态" name="is_active">
                        <a-switch v-model:checked="modalForm.is_active" />
                    </a-form-item>
                </a-form>
            </a-modal>
        </a-layout-content>
    </a-layout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { PlusOutlined, SearchOutlined, ReloadOutlined, CopyOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '@/store'
import api from '@/api'
import { formatDateTime, copyToClipboard } from '@/utils'
import { message } from 'ant-design-vue'

const userStore = useUserStore()

const queryParams = reactive<any>({
    app_name: '',
    tenant_id: undefined,
})

const tenantOptions = ref<any[]>([])

const filterItemCount = computed(() => {
    let count = 1
    if (userStore.isSuperUser) count++
    return count
})

const getActionColProps = computed(() => {
    const isSingleLine = filterItemCount.value <= 2
    if (isSingleLine) {
        return { xs: 24, sm: 12, md: 8, lg: 6, xl: 6 }
    }
    return { xs: 24, sm: 24, md: 24, lg: 24, xl: 24 }
})

const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '应用名称', dataIndex: 'app_name', key: 'app_name' },
    { title: 'API Key', key: 'api_key', width: 280 },
    { title: 'Dify地址', dataIndex: 'dify_url', key: 'dify_url', ellipsis: true },
    { title: '状态', key: 'is_active', width: 100 },
    { title: '创建时间', key: 'created_at', width: 180 },
    { title: '操作', key: 'action', width: 150, fixed: 'right' },
]

const tableData = ref<any[]>([])
const loading = ref(false)
const pagination = reactive({
    current: 1,
    pageSize: 10,
    total: 0,
    showSizeChanger: true,
    showTotal: (total: number) => `共 ${total} 条`,
})

const modalVisible = ref(false)
const modalLoading = ref(false)
const modalAction = ref<'add' | 'edit'>('add')
const modalTitle = computed(() => modalAction.value === 'add' ? '新建应用' : '编辑应用')
const modalFormRef = ref<any>(null)
const modalForm = reactive<any>({
    id: undefined,
    app_name: '',
    tenant_id: undefined,
    dify_url: '',
    dify_api_key: '',
    description: '',
    is_active: true,
})

const modalRules = {
    app_name: [
        { required: true, message: '请输入应用名称', trigger: 'blur' },
        { pattern: /^[a-zA-Z0-9_]+$/, message: '应用名称只能包含英文、数字、下划线', trigger: 'blur' },
    ],
    tenant_id: [{ required: true, message: '请选择租户', trigger: 'change', type: 'number' }],
}

const maskApiKey = (apiKey: string) => {
    if (!apiKey) return ''
    if (apiKey.length <= 10) return apiKey
    return apiKey.substring(0, 10) + '...' + apiKey.substring(apiKey.length - 4)
}

const copyApiKey = (apiKey: string) => {
    copyToClipboard(apiKey)
    message.success('API Key 已复制到剪贴板')
}

const fetchData = async () => {
    loading.value = true
    try {
        const res: any = await api.getAppList({
            page: pagination.current,
            page_size: pagination.pageSize,
            ...queryParams,
        })
        if (res.code === 200) {
            tableData.value = res.data || []
            pagination.total = res.total || 0
        }
    } finally {
        loading.value = false
    }
}

const fetchTenantOptions = async () => {
    if (!userStore.isSuperUser) return
    try {
        const res: any = await api.getTenantSelect()
        if (res.code === 200) {
            tenantOptions.value = (res.data || []).map((t: any) => ({
                label: t.name,
                value: t.id,
            }))
        }
    } catch (error) {
        console.error('获取租户列表失败', error)
    }
}

const handleSearch = () => {
    pagination.current = 1
    fetchData()
}

const handleReset = () => {
    queryParams.app_name = ''
    queryParams.tenant_id = undefined
    pagination.current = 1
    fetchData()
}

const handleTableChange = (pag: any) => {
    pagination.current = pag.current
    pagination.pageSize = pag.pageSize
    fetchData()
}

const resetModalForm = () => {
    modalForm.id = undefined
    modalForm.app_name = ''
    modalForm.tenant_id = userStore.isSuperUser ? undefined : userStore.userInfo?.current_tenant_id
    modalForm.dify_url = ''
    modalForm.dify_api_key = ''
    modalForm.description = ''
    modalForm.is_active = true
}

const handleAdd = () => {
    modalAction.value = 'add'
    resetModalForm()
    modalVisible.value = true
}

const handleEdit = (record: any) => {
    modalAction.value = 'edit'
    resetModalForm()
    Object.assign(modalForm, record)
    modalVisible.value = true
}

const handleSave = async () => {
    try {
        await modalFormRef.value?.validate()
        modalLoading.value = true

        const apiCall = modalAction.value === 'add' ? api.createApp : api.updateApp
        const res: any = await apiCall({ ...modalForm })

        if (res.code === 200) {
            message.success(modalAction.value === 'add' ? '创建成功' : '更新成功')
            modalVisible.value = false
            fetchData()
        } else {
            message.error(res.msg || '操作失败')
        }
    } catch (error) {
        console.error('保存失败', error)
    } finally {
        modalLoading.value = false
    }
}

const handleDelete = async (record: any) => {
    try {
        const res: any = await api.deleteApp({ id: record.id })
        if (res.code === 200) {
            message.success('删除成功')
            fetchData()
        } else {
            message.error(res.msg || '删除失败')
        }
    } catch (error) {
        console.error('删除失败', error)
    }
}

onMounted(() => {
    fetchTenantOptions()
    fetchData()
})
</script>
