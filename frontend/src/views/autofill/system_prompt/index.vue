<template>
    <div class="system-prompt-management">
        <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
            :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
            :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
            modal-width="800px" @search="handleSearch" @reset="handleReset" @table-change="handleTableChange"
            @modal-ok="handleSave">
            <!-- 筛选条件 -->
            <template #filter-items>
                <a-col v-if="userStore.isSuperUser" :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item label="租户" class="filter-item">
                        <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户" allow-clear
                            :options="tenantOptions" @change="handleSearch" />
                    </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item label="提示词名称" class="filter-item">
                        <a-input v-model:value="queryParams.keyword" placeholder="请输入提示词名称" allow-clear
                            @pressEnter="handleSearch" />
                    </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item label="分类" class="filter-item">
                        <a-select v-model:value="queryParams.category" placeholder="请选择分类" allow-clear
                            :options="categoryOptions" @change="handleSearch" />
                    </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item label="是否默认" class="filter-item">
                        <a-select v-model:value="queryParams.is_default" placeholder="请选择" allow-clear :options="[
                            { label: '是', value: true },
                            { label: '否', value: false }
                        ]" @change="handleSearch" />
                    </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item label="状态" class="filter-item">
                        <a-select v-model:value="queryParams.is_active" placeholder="请选择状态" allow-clear :options="[
                            { label: '启用', value: true },
                            { label: '禁用', value: false }
                        ]" @change="handleSearch" />
                    </a-form-item>
                </a-col>
            </template>

            <!-- 操作按钮 -->
            <template #actions>
                <a-space>
                    <a-button type="primary" @click="handleAdd">
                        <PlusOutlined />
                        新建提示词
                    </a-button>
                </a-space>
            </template>

            <!-- 表格列自定义 -->
            <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'category'">
                    <a-tag :color="getCategoryColor(record.category)">
                        {{ getCategoryLabel(record.category) }}
                    </a-tag>
                </template>
                <template v-if="column.key === 'is_default'">
                    <a-tag :color="record.is_default ? 'blue' : 'default'">
                        {{ record.is_default ? '是' : '否' }}
                    </a-tag>
                </template>
                <template v-if="column.key === 'is_active'">
                    <a-tag :color="record.is_active ? 'green' : 'red'">
                        {{ record.is_active ? '启用' : '禁用' }}
                    </a-tag>
                </template>
                <template v-if="column.key === 'content'">
                    <a-typography-text :content="record.content" ellipsis style="max-width: 200px" />
                </template>
                <template v-if="column.key === 'created_at'">
                    <span v-if="record.created_at">{{ formatDateTime(record.created_at) }}</span>
                    <span v-else>-</span>
                </template>
                <template v-if="column.key === 'action'">
                    <a-space>
                        <a-button type="link" size="small" @click="handleEdit(record)">编辑</a-button>
                        <a-popconfirm title="确定删除该提示词吗？" @confirm="handleDelete(record)">
                            <a-button type="link" danger size="small">删除</a-button>
                        </a-popconfirm>
                    </a-space>
                </template>
            </template>

            <!-- 弹窗表单 -->
            <template #modal-form="{ form }">
                <a-form-item v-if="userStore.isSuperUser" label="所属租户" name="tenant_id">
                    <a-select v-model:value="form.tenant_id" placeholder="请选择租户" :options="tenantOptions" />
                </a-form-item>
                <a-form-item label="提示词名称" name="name" required>
                    <a-input v-model:value="form.name" placeholder="请输入提示词名称" />
                </a-form-item>
                <a-form-item label="分类" name="category" required>
                    <a-select v-model:value="form.category" placeholder="请选择或输入分类" :options="categoryOptions"
                        show-search allow-clear mode="combobox" :filter-option="filterCategoryOption"
                        @search="handleCategorySearch" @change="handleCategoryChange">
                        <template #dropdownRender="{ menuNode: menu }">
                            <VNodes :vnodes="menu" />
                            <a-divider style="margin: 4px 0" />
                            <a-space style="padding: 4px 8px">
                                <a-input v-model:value="newCategoryName" placeholder="输入新分类" size="small"
                                    @pressEnter="handleAddNewCategory" />
                                <a-button type="primary" size="small" @click="handleAddNewCategory">添加</a-button>
                            </a-space>
                        </template>
                    </a-select>
                </a-form-item>
                <a-form-item label="提示词内容" name="content" required>
                    <a-textarea v-model:value="form.content"
                        placeholder="请输入提示词内容，可用变量：{task_prompts}, {query}, {response_format}" :rows="8" />
                </a-form-item>
                <a-form-item label="描述" name="description">
                    <a-textarea v-model:value="form.description" placeholder="请输入描述" :rows="3" />
                </a-form-item>
                <a-form-item label="是否默认" name="is_default">
                    <a-switch v-model:checked="form.is_default" />
                </a-form-item>
                <a-form-item label="是否启用" name="is_active">
                    <a-switch v-model:checked="form.is_active" />
                </a-form-item>
            </template>
        </CrudTable>
    </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { useUserStore } from '@/store/modules/user'
import { PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, onMounted, reactive, ref } from 'vue'

// 用于渲染下拉菜单的辅助组件
const VNodes = (_: any, { attrs }: any) => {
    return attrs.vnodes
}
const userStore = useUserStore()
const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 表格列定义
const columns = computed(() => [
    {
        title: '提示词名称',
        dataIndex: 'name',
        key: 'name',
        width: 200
    },
    {
        title: '分类',
        dataIndex: 'category',
        key: 'category',
        width: 120
    },
    {
        title: '内容',
        dataIndex: 'content',
        key: 'content',
        width: 250
    },
    {
        title: '是否默认',
        dataIndex: 'is_default',
        key: 'is_default',
        width: 100
    },
    {
        title: '状态',
        dataIndex: 'is_active',
        key: 'is_active',
        width: 100
    },
    {
        title: '创建时间',
        dataIndex: 'created_at',
        key: 'created_at',
        width: 180
    },
    {
        title: '操作',
        key: 'action',
        width: 150,
        fixed: 'right'
    }
])

// 分类选项（动态加载）
const categoryOptions = ref<{ label: string; value: string }[]>([])
const newCategoryName = ref('')

// 加载分类选项
const loadCategories = async () => {
    try {
        const params: any = {}
        if (userStore.isSuperUser && queryParams.tenant_id) {
            params.tenant_id = queryParams.tenant_id
        }
        const res: any = await api.getSystemPromptCategories(params)
        if (res.code === 200 && Array.isArray(res.data)) {
            categoryOptions.value = res.data.map((cat: string) => ({
                label: cat,
                value: cat
            }))
        }
    } catch (error) {
        console.error('加载分类失败', error)
    }
}

// 分类搜索过滤
const filterCategoryOption = (input: string, option: any) => {
    return option.value.toLowerCase().indexOf(input.toLowerCase()) >= 0
}

// 分类搜索
const handleCategorySearch = (value: string) => {
    newCategoryName.value = value
}

// 分类变更
const handleCategoryChange = (value: string) => {
    modalForm.category = value
}

// 添加新分类
const handleAddNewCategory = () => {
    const name = newCategoryName.value.trim()
    if (!name) {
        message.warning('请输入分类名称')
        return
    }
    // 检查是否已存在
    if (!categoryOptions.value.find(opt => opt.value === name)) {
        categoryOptions.value.push({ label: name, value: name })
    }
    modalForm.category = name
    newCategoryName.value = ''
    message.success('已添加新分类')
}

// 查询参数
const queryParams = reactive({
    page: 1,
    page_size: 20,
    tenant_id: undefined as number | undefined,
    keyword: '',
    category: undefined as string | undefined,
    is_default: undefined as boolean | undefined,
    is_active: undefined as boolean | undefined
})

// 表格数据
const tableData = ref<any[]>([])
const loading = ref(false)
const pagination = reactive({
    current: 1,
    pageSize: 20,
    total: 0,
    showSizeChanger: true,
    showQuickJumper: true,
    showTotal: (total: number) => `共 ${total} 条`
})

// 租户选项
const tenantOptions = ref<{ label: string; value: number }[]>([])
const filterItemCount = computed(() => userStore.isSuperUser ? 3 : 2)

// 弹窗相关
const modalTitle = ref('新建提示词')
const modalLoading = ref(false)
const isEdit = ref(false)
const currentId = ref<string | null>(null)

const modalForm = reactive({
    tenant_id: undefined as number | undefined,
    name: '',
    category: 'general',
    content: '',
    description: '',
    is_default: false,
    is_active: true
})

const modalRules = {
    name: [{ required: true, message: '请输入提示词名称', trigger: 'blur' }],
    category: [{ required: true, message: '请选择分类', trigger: 'change' }],
    content: [{ required: true, message: '请输入提示词内容', trigger: 'blur' }]
}

// 获取分类标签（动态分类直接显示）
const getCategoryLabel = (category: string) => {
    return category || '-'
}

// 获取分类颜色（根据分类名称动态生成）
const getCategoryColor = (category: string) => {
    const colorMap: Record<string, string> = {
        'general': 'default',
        'default': 'default',
        '通用': 'default',
        'choice': 'blue',
        'multi_choice': 'blue',
        '选择题': 'blue',
        'text': 'green',
        'fill_blank': 'green',
        '填空题': 'green',
        'multi_task': 'purple',
        '多任务': 'purple',
        'plain': 'cyan',
        'json': 'orange'
    }
    return colorMap[category] || 'default'
}

// 格式化日期时间
const formatDateTime = (dateStr: string) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN')
}

// 加载租户选项
const loadTenantOptions = async () => {
    if (!userStore.isSuperUser) return
    try {
        const res: any = await api.getTenantSelect()
        if (res.code === 200) {
            tenantOptions.value = res.data.map((item: any) => ({
                label: item.name,
                value: item.id
            }))
        }
    } catch (error) {
        console.error('加载租户列表失败', error)
    }
}

// 加载表格数据
const loadTableData = async () => {
    loading.value = true
    try {
        const params = {
            page: queryParams.page,
            page_size: queryParams.page_size,
            tenant_id: queryParams.tenant_id,
            keyword: queryParams.keyword || undefined,
            category: queryParams.category,
            is_default: queryParams.is_default,
            is_active: queryParams.is_active
        }
        const res: any = await api.getSystemPromptList(params)
        if (res.code === 200) {
            tableData.value = res.data || []
            pagination.total = res.total || 0
        }
    } catch (error) {
        message.error('加载数据失败')
        console.error(error)
    } finally {
        loading.value = false
    }
}

// 搜索
const handleSearch = () => {
    queryParams.page = 1
    pagination.current = 1
    loadTableData()
}

// 重置
const handleReset = () => {
    queryParams.page = 1
    queryParams.page_size = 20
    queryParams.tenant_id = undefined
    queryParams.keyword = ''
    queryParams.category = undefined
    queryParams.is_default = undefined
    queryParams.is_active = undefined
    pagination.current = 1
    loadTableData()
}

// 表格变化
const handleTableChange = (pag: any) => {
    queryParams.page = pag.current
    queryParams.page_size = pag.pageSize
    pagination.current = pag.current
    pagination.pageSize = pag.pageSize
    loadTableData()
}

// 新增
const handleAdd = () => {
    isEdit.value = false
    currentId.value = null
    modalTitle.value = '新建提示词'
    modalForm.tenant_id = userStore.isSuperUser ? undefined : userStore.currentTenant?.id
    modalForm.name = ''
    modalForm.category = 'general'
    modalForm.content = ''
    modalForm.description = ''
    modalForm.is_default = false
    modalForm.is_active = true
    crudTableRef.value?.openAddModal()
}

// 编辑
const handleEdit = async (record: any) => {
    isEdit.value = true
    currentId.value = record.id
    modalTitle.value = '编辑提示词'
    try {
        const res: any = await api.getSystemPromptById({ id: record.id })
        if (res.code === 200) {
            const data = res.data
            // 如果租户ID为0（全局提示词），超管显示为undefined以便选择，普通账号显示当前租户
            modalForm.tenant_id = data.tenant_id === 0 ? (userStore.isSuperUser ? undefined : userStore.currentTenant?.id) : data.tenant_id
            modalForm.name = data.name
            modalForm.category = data.category
            modalForm.content = data.content
            modalForm.description = data.description || ''
            modalForm.is_default = data.is_default
            modalForm.is_active = data.is_active
            // 不传递 tenant_id，避免覆盖已处理的 modalForm.tenant_id
            const { tenant_id, ...recordWithoutTenant } = record
            crudTableRef.value?.openEditModal(recordWithoutTenant)
        }
    } catch (error) {
        message.error('获取详情失败')
        console.error(error)
    }
}

// 保存
const handleSave = async (form: Record<string, any>, action: 'add' | 'edit') => {
    modalLoading.value = true
    try {
        if (action === 'edit' && currentId.value) {
            const res: any = await api.updateSystemPrompt({
                id: currentId.value,
                tenant_id: userStore.isSuperUser ? form.tenant_id : undefined,
                name: form.name,
                category: form.category,
                content: form.content,
                description: form.description,
                is_default: form.is_default,
                is_active: form.is_active
            })
            if (res.code === 200) {
                message.success('更新成功')
                crudTableRef.value?.closeModal()
                loadTableData()
            }
        } else {
            const res: any = await api.createSystemPrompt({
                tenant_id: form.tenant_id,
                name: form.name,
                category: form.category,
                content: form.content,
                description: form.description,
                is_default: form.is_default,
                is_active: form.is_active
            })
            if (res.code === 200) {
                message.success('创建成功')
                crudTableRef.value?.closeModal()
                loadTableData()
            }
        }
    } catch (error) {
        message.error(action === 'edit' ? '更新失败' : '创建失败')
        console.error(error)
    } finally {
        modalLoading.value = false
    }
}

// 删除
const handleDelete = async (record: any) => {
    try {
        const params: any = { id: record.id }
        // 超管传递租户ID进行删除
        if (userStore.isSuperUser && record.tenant_id !== undefined) {
            params.tenant_id = record.tenant_id
        }
        const res: any = await api.deleteSystemPrompt(params)
        if (res.code === 200) {
            message.success('删除成功')
            loadTableData()
        }
    } catch (error) {
        message.error('删除失败')
        console.error(error)
    }
}

onMounted(() => {
    loadTenantOptions()
    loadCategories()
    loadTableData()
})
</script>

<style scoped lang="less">
.system-prompt-management {
    padding: 16px;

    .filter-item-col {
        padding: 0 8px;
    }

    .filter-item {
        margin-bottom: 16px;
    }
}
</style>
