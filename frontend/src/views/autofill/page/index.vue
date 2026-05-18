<template>
    <div class="page-management">
        <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
            :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
            :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
            modal-width="700px" @search="handleSearch" @reset="handleReset" @table-change="handleTableChange"
            @modal-ok="handleSave">
            <!-- 筛选条件 -->
            <template #filter-items>
                <a-col v-if="userStore.isSuperUser" :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item label="租户" class="filter-item">
                        <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户" allow-clear
                            :options="tenantOptions" @change="handleTenantChange" />
                    </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item label="页面名称" class="filter-item">
                        <a-input v-model:value="queryParams.page_name" placeholder="请输入页面名称" allow-clear
                            @pressEnter="handleSearch" />
                    </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item label="页面编码" class="filter-item">
                        <a-input v-model:value="queryParams.page_code" placeholder="请输入页面编码" allow-clear
                            @pressEnter="handleSearch" />
                    </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item label="应用名称" class="filter-item">
                        <a-select v-model:value="queryParams.app_name" placeholder="请选择应用" allow-clear
                            :options="appOptions" @change="handleSearch" />
                    </a-form-item>
                </a-col>
            </template>

            <!-- 操作按钮 -->
            <template #actions>
                <a-button v-permission="'post/api/v1/autofill/page/create'" type="primary" @click="handleAdd">
                    <PlusOutlined />
                    新建页面
                </a-button>
            </template>

            <!-- 表格列自定义 -->
            <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'is_active'">
                    <a-tag :color="record.is_active ? 'green' : 'red'">
                        {{ record.is_active ? '启用' : '禁用' }}
                    </a-tag>
                </template>
                <template v-if="column.key === 'created_at'">
                    <span v-if="record.created_at">{{ formatDateTime(record.created_at) }}</span>
                    <span v-else>-</span>
                </template>
                <template v-if="column.key === 'action'">
                    <a-space>
                        <a-button type="link" size="small" @click="handleViewDetail(record)">详情</a-button>
                        <a-button v-permission="'post/api/v1/autofill/page/update'" type="link" size="small"
                            @click="handleEdit(record)">编辑</a-button>
                        <a-popconfirm title="确定删除该页面吗？" @confirm="handleDelete(record)">
                            <a-button v-permission="'delete/api/v1/autofill/page/delete'" type="link" danger
                                size="small">删除</a-button>
                        </a-popconfirm>
                    </a-space>
                </template>
            </template>

            <!-- 弹窗表单 -->
            <template #modal-form="{ form }">
                <a-form-item v-if="userStore.isSuperUser" label="所属租户" name="tenant_id">
                    <a-select v-model:value="form.tenant_id" placeholder="请选择租户" :options="tenantOptions"
                        @change="(val: number) => handleModalTenantChange(val, form)" />
                </a-form-item>
                <a-form-item label="页面名称" name="page_name">
                    <a-input v-model:value="form.page_name" placeholder="请输入页面名称" />
                </a-form-item>
                <a-form-item label="所属应用" name="app_name">
                    <a-select v-model:value="form.app_name" placeholder="请选择应用" :options="appOptions"
                        :disabled="modalAction === 'edit'" />
                </a-form-item>
                <a-form-item label="页面描述" name="description">
                    <a-textarea v-model:value="form.description" placeholder="请输入页面描述" :rows="3" />
                </a-form-item>
                <a-form-item label="Dify Agent URL" name="dify_agent_url">
                    <a-input v-model:value="form.dify_agent_url" placeholder="请输入Dify Agent URL，如：https://dify.example.com/v1/chat-messages" />
                </a-form-item>
                <a-form-item label="Dify API Key" name="dify_api_key">
                    <a-input-password v-model:value="form.dify_api_key" placeholder="请输入Dify API Key" />
                </a-form-item>
                <a-form-item label="状态" name="is_active">
                    <a-switch v-model:checked="form.is_active" />
                </a-form-item>
            </template>
        </CrudTable>

        <!-- 详情弹窗 -->
        <a-modal v-model:open="detailModalVisible" title="页面详情" width="1000px" :footer="null">
            <div v-if="detailLoading" class="detail-loading">
                <a-spin size="large" />
            </div>
            <div v-else-if="detailData" class="detail-content">
                <!-- 基本信息 -->
                <a-card title="基本信息" class="detail-card">
                    <a-descriptions :column="2">
                        <a-descriptions-item label="页面名称">{{ detailData.basic_info?.page_name }}</a-descriptions-item>
                        <a-descriptions-item label="编码">{{ detailData.basic_info?.page_code }}</a-descriptions-item>
                        <a-descriptions-item label="应用">{{ detailData.basic_info?.app_name }}</a-descriptions-item>
                        <a-descriptions-item label="状态">
                            <a-tag :color="detailData.basic_info?.is_active ? 'green' : 'red'">
                                {{ detailData.basic_info?.is_active ? '启用' : '禁用' }}
                            </a-tag>
                        </a-descriptions-item>
                        <a-descriptions-item label="描述" :span="2">{{ detailData.basic_info?.description || '-'
                            }}</a-descriptions-item>
                        <a-descriptions-item label="Dify Agent URL" :span="2">{{ detailData.basic_info?.dify_agent_url || '-'
                            }}</a-descriptions-item>
                        <a-descriptions-item label="Dify API Key" :span="2">
                            <span v-if="detailData.basic_info?.dify_api_key">********</span>
                            <span v-else>-</span>
                        </a-descriptions-item>
                    </a-descriptions>
                </a-card>

                <!-- 字段组列表 -->
                <a-card title="字段组列表" class="detail-card">
                    <a-table :dataSource="detailData.field_groups" :columns="fieldGroupColumns" size="small"
                        :pagination="false">
                        <template #bodyCell="{ column, record }">
                            <template v-if="column.key === 'is_active'">
                                <a-tag :color="record.is_active ? 'green' : 'red'">
                                    {{ record.is_active ? '启用' : '禁用' }}
                                </a-tag>
                            </template>
                            <template v-if="column.key === 'action'">
                                <a-button type="link" size="small"
                                    @click="handleViewFieldGroupDetail(record)">查看详情</a-button>
                            </template>
                        </template>
                    </a-table>
                </a-card>

                <!-- 操作按钮 -->
                <div class="detail-actions">
                    <a-button type="primary" @click="handleExportMd">
                        <DownloadOutlined />
                        导出Markdown
                    </a-button>
                </div>
            </div>
        </a-modal>
    </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { useUserStore } from '@/store'
import { formatDateTime } from '@/utils'
import { DownloadOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'PageManagement' })

const userStore = useUserStore()
const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
    page_name: '',
    page_code: '',
    app_name: undefined as string | undefined,
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
    page_name: '',
    page_code: '',
    app_name: '',
    tenant_id: undefined as number | undefined,
    description: '',
    dify_agent_url: '',
    dify_api_key: '',
    is_active: true,
})

// 其他数据
const appOptions = ref<any[]>([])
const tenantOptions = ref<any[]>([])

// 详情弹窗
const detailModalVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref<any>(null)
const currentDetailId = ref<number | null>(null)

// 字段组表格列
const fieldGroupColumns = [
    { title: '字段组名称', dataIndex: 'group_name', key: 'group_name' },
    { title: '编码', dataIndex: 'group_code', key: 'group_code' },
    { title: '字段数', dataIndex: 'field_count', key: 'field_count', width: 80 },
    { title: '状态', key: 'is_active', width: 80 },
    { title: '操作', key: 'action', width: 100 },
]

// 计算属性
const columns = computed(() => [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '页面名称', dataIndex: 'page_name', key: 'page_name' },
    { title: '页面编码', dataIndex: 'page_code', key: 'page_code' },
    { title: '应用名称', dataIndex: 'app_name', key: 'app_name' },
    { title: '状态', key: 'is_active', width: 100 },
    { title: '创建时间', key: 'created_at', width: 180 },
    { title: '操作', key: 'action', width: 150, fixed: 'right' },
])

const filterItemCount = computed(() => {
    let count = 3
    if (userStore.isSuperUser) count++
    return count
})

const modalRules = {
    page_name: [
        { required: true, message: '请输入页面名称', trigger: 'blur' },
    ],
    app_id: [
        { required: true, message: '请选择应用', trigger: 'change' },
    ],
}

// 方法
// 加载数据
const fetchData = async () => {
    loading.value = true
    try {
        const res: any = await api.getPageList({
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

const fetchAppOptions = async (tenantId?: number) => {
    try {
        const params: any = {}
        // 如果指定了租户，只加载该租户的应用
        if (tenantId && tenantId > 0) {
            params.tenant_id = tenantId
        }
        const res: any = await api.getAppSelect(params)
        if (res.code === 200) {
            appOptions.value = (res.data || []).map((app: any) => ({
                label: app.label,
                value: app.value,
            }))
        }
    } catch (error) {
        console.error('获取应用列表失败:', error)
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
        console.error('获取租户列表失败:', error)
    }
}



const handleSearch = () => {
    pagination.current = 1
    fetchData()
}

const handleReset = () => {
    queryParams.page_name = ''
    queryParams.page_code = ''
    queryParams.app_name = undefined
    queryParams.tenant_id = undefined
    pagination.current = 1
    fetchData()
}

const handleTenantChange = (tenantId: number) => {
    // 重置应用选择
    queryParams.app_name = undefined
    // 重新加载该租户的应用
    fetchAppOptions(tenantId)
    // 刷新数据
    handleSearch()
}

// 弹窗中租户变更处理
const handleModalTenantChange = (tenantId: number, form: any) => {
    // 重置应用选择
    form.app_name = undefined
    // 重新加载该租户的应用
    fetchAppOptions(tenantId)
}

const handleTableChange = (pag: any) => {
    pagination.current = pag.current
    pagination.pageSize = pag.pageSize
    fetchData()
}

const handleAdd = () => {
    modalAction.value = 'add'
    modalTitle.value = '新建页面'
    modalForm.id = undefined
    modalForm.page_name = ''
    modalForm.page_code = ''
    modalForm.app_name = ''
    modalForm.tenant_id = userStore.isSuperUser ? undefined : userStore.userInfo?.current_tenant_id
    modalForm.description = ''
    modalForm.dify_agent_url = ''
    modalForm.dify_api_key = ''
    modalForm.is_active = true
    crudTableRef.value?.openAddModal()
}

const handleEdit = (record: any) => {
    modalAction.value = 'edit'
    modalTitle.value = '编辑页面'
    modalForm.id = record.id
    modalForm.page_name = record.page_name
    modalForm.page_code = record.page_code
    modalForm.app_name = record.app_name
    modalForm.tenant_id = record.tenant_id
    modalForm.description = record.description
    modalForm.dify_agent_url = record.dify_agent_url || ''
    modalForm.dify_api_key = record.dify_api_key || ''
    modalForm.is_active = record.is_active
    crudTableRef.value?.openEditModal(record)
}

// 查看详情
const handleViewDetail = async (record: any) => {
    currentDetailId.value = record.id
    detailModalVisible.value = true
    detailLoading.value = true
    try {
        const res: any = await api.getPageDetail({ id: record.id })
        if (res.code === 200) {
            detailData.value = res.data
        } else {
            message.error(res.msg || '获取详情失败')
        }
    } catch (error: any) {
        message.error(error.message || '获取详情失败')
    } finally {
        detailLoading.value = false
    }
}

// 查看字段组详情
const handleViewFieldGroupDetail = (record: any) => {
    // 打开新标签页查看字段组详情
    const route = `/autofill/field_group?id=${record.id}`
    window.open(route, '_blank')
}

// 导出Markdown
const handleExportMd = async () => {
    if (!currentDetailId.value) return
    try {
        const res: any = await api.exportPageMd({ id: currentDetailId.value })
        if (res.code === 200 && res.data?.markdown) {
            // 创建下载
            const blob = new Blob([res.data.markdown], { type: 'text/markdown' })
            const url = URL.createObjectURL(blob)
            const link = document.createElement('a')
            link.href = url
            link.download = res.data.filename || `page_${currentDetailId.value}.md`
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            URL.revokeObjectURL(url)
            message.success('导出成功')
        } else {
            message.error(res.msg || '导出失败')
        }
    } catch (error: any) {
        message.error(error.message || '导出失败')
    }
}

const handleSave = async () => {
    modalLoading.value = true
    try {
        const apiFunc = modalAction.value === 'add' ? api.createPage : api.updatePage
        const res: any = await apiFunc({ ...modalForm })
        if (res.code === 200) {
            message.success(modalAction.value === 'add' ? '创建成功' : '更新成功')
            crudTableRef.value?.closeModal()
            fetchData()
        } else {
            message.error(res.msg || '操作失败')
        }
    } catch (error: any) {
        message.error(error.message || '操作失败')
    } finally {
        modalLoading.value = false
    }
}

const handleDelete = async (record: any) => {
    try {
        const res: any = await api.deletePage({ id: record.id })
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

onMounted(() => {
    fetchData()
    fetchAppOptions()
    fetchTenantOptions()
})
</script>

<style scoped lang="less">
.page-management {

    .detail-loading {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 200px;
    }

    .detail-content {
        max-height: 70vh;
        overflow-y: auto;

        .detail-card {
            margin-bottom: 16px;

            &:last-child {
                margin-bottom: 0;
            }
        }

        .detail-actions {
            display: flex;
            justify-content: flex-end;
            padding-top: 16px;
            border-top: 1px solid #e8e8e8;
        }
    }
}
</style>
