<template>
    <div class="app-page">
        <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
            :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
            :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
            modal-width="700px" @search="handleSearch" @reset="handleReset" @table-change="handleTableChange"
            @modal-ok="handleSave">
            <!-- 筛选条件 -->
            <template #filter-items>
                <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item label="应用名称" class="filter-item">
                        <a-input v-model:value="queryParams.app_name" placeholder="请输入应用名称" allow-clear
                            @pressEnter="handleSearch" />
                    </a-form-item>
                </a-col>
                <a-col v-if="userStore.isSuperUser" :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item label="租户" class="filter-item">
                        <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户" allow-clear
                            :options="tenantOptions" @change="handleSearch" />
                    </a-form-item>
                </a-col>
            </template>

            <!-- 操作按钮 -->
            <template #actions>
                <a-button v-permission="'post/api/v1/autofill/app/create'" type="primary" @click="handleAdd">
                    <PlusOutlined />
                    新建应用
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

            <!-- 弹窗表单 -->
            <template #modal-form="{ form }">
                <a-form-item label="应用名称" name="app_name">
                    <a-input v-model:value="form.app_name" placeholder="请输入应用名称（英文、数字、下划线）"
                        :disabled="modalAction === 'edit'" />
                </a-form-item>
                <a-form-item v-if="userStore.isSuperUser" label="租户" name="tenant_id">
                    <a-select v-model:value="form.tenant_id" placeholder="请选择租户" :options="tenantOptions" />
                </a-form-item>
                <a-form-item label="Dify服务地址" name="dify_url">
                    <a-input v-model:value="form.dify_url" placeholder="请输入Dify服务地址，如：https://dify.example.com/v1" />
                </a-form-item>
                <a-form-item label="Dify API Key" name="dify_api_key">
                    <a-input-password v-model:value="form.dify_api_key" placeholder="请输入Dify API Key" />
                </a-form-item>
                <a-form-item label="应用描述" name="description">
                    <a-textarea v-model:value="form.description" placeholder="请输入应用描述" :rows="3" />
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
import { useUserStore } from '@/store'
import { copyToClipboard, formatDateTime } from '@/utils'
import { CopyOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'AppPage' })

const userStore = useUserStore()
const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
    app_name: '',
    tenant_id: undefined as number | undefined,
})

// 表格数据
const loading = ref(false)
const tableData = ref<any[]>([])
const pagination = reactive({
    current: 1,
    pageSize: 10,
    total: 0,
})

// 弹窗数据
const modalTitle = ref('')
const modalLoading = ref(false)
const modalAction = ref<'add' | 'edit'>('add')
const modalForm = reactive({
    id: undefined as number | undefined,
    app_name: '',
    tenant_id: undefined as number | undefined,
    dify_url: '',
    dify_api_key: '',
    description: '',
    is_active: true,
})

// 其他数据
const tenantOptions = ref<any[]>([])

// 计算属性
const columns = computed(() => [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '应用名称', dataIndex: 'app_name', key: 'app_name' },
    { title: 'API Key', key: 'api_key', width: 280 },
    { title: 'Dify地址', dataIndex: 'dify_url', key: 'dify_url', ellipsis: true },
    { title: '状态', key: 'is_active', width: 100 },
    { title: '创建时间', key: 'created_at', width: 180 },
    { title: '操作', key: 'action', width: 150, fixed: 'right' },
])

const filterItemCount = computed(() => {
    let count = 1
    if (userStore.isSuperUser) count++
    return count
})

const modalRules = {
    app_name: [
        { required: true, message: '请输入应用名称', trigger: 'blur' },
        { pattern: /^[a-zA-Z0-9_]+$/, message: '应用名称只能包含英文、数字、下划线', trigger: 'blur' },
    ],
    tenant_id: [{ required: true, message: '请选择租户', trigger: 'change', type: 'number' }],
}

// 方法
const maskApiKey = (apiKey: string) => {
    if (!apiKey) return ''
    if (apiKey.length <= 10) return apiKey
    return apiKey.substring(0, 10) + '...' + apiKey.substring(apiKey.length - 4)
}

const copyApiKey = (apiKey: string) => {
    copyToClipboard(apiKey)
    message.success('API Key 已复制到剪贴板')
}

// 加载数据
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

const handleAdd = () => {
    modalAction.value = 'add'
    modalTitle.value = '新建应用'
    Object.assign(modalForm, {
        id: undefined,
        app_name: '',
        tenant_id: userStore.isSuperUser ? undefined : userStore.userInfo?.current_tenant_id,
        dify_url: '',
        dify_api_key: '',
        description: '',
        is_active: true,
    })
    crudTableRef.value?.openAddModal()
}

const handleEdit = (record: any) => {
    modalAction.value = 'edit'
    modalTitle.value = '编辑应用'
    Object.assign(modalForm, { ...record })
    crudTableRef.value?.openEditModal(record)
}

const handleSave = async (form: Record<string, any>, action: 'add' | 'edit') => {
    modalLoading.value = true
    try {
        const apiCall = action === 'add' ? api.createApp : api.updateApp
        const res: any = await apiCall({ ...form })
        if (res.code === 200) {
            message.success(action === 'add' ? '创建成功' : '更新成功')
            crudTableRef.value?.closeModal()
            fetchData()
        } else {
            message.error(res.msg || '操作失败')
        }
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
    fetchData()
    fetchTenantOptions()
})
</script>

<style scoped lang="less">
.app-page {
    padding: 16px;
}
</style>
