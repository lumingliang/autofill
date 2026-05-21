<template>
    <div class="manage-fields-modal">
        <!-- 筛选区域 -->
        <div class="filter-area">
            <a-row :gutter="16">
                <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item label="字段组筛选" class="filter-item">
                        <a-select v-model:value="filterGroupId" placeholder="请选择字段组筛选" allow-clear
                            :options="fieldGroupOptions" @change="handleFilterGroupChange" />
                    </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item label="字段名称" class="filter-item">
                        <a-input v-model:value="searchFieldName" placeholder="请输入字段名称" allow-clear
                            @pressEnter="handleSearch" />
                    </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item label="字段标签" class="filter-item">
                        <a-input v-model:value="searchFieldLabel" placeholder="请输入字段标签" allow-clear
                            @pressEnter="handleSearch" />
                    </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item label="字段类型" class="filter-item">
                        <a-select v-model:value="searchFieldType" placeholder="请选择字段类型" allow-clear
                            @change="handleSearch">
                            <a-select-option value="text">文本输入</a-select-option>
                            <a-select-option value="select">下拉单选</a-select-option>
                            <a-select-option value="multi_select">下拉多选</a-select-option>
                            <a-select-option value="template">模板类型</a-select-option>
                        </a-select>
                    </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
                    <a-form-item class="filter-item filter-actions">
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
        </div>

        <!-- 操作栏 -->
        <div class="action-bar">
            <a-space>
                <a-button type="primary" :loading="saveLoading" @click="handleSave">
                    <SaveOutlined />
                    保存
                </a-button>
                <a-button @click="handleClose">
                    关闭
                </a-button>
            </a-space>
        </div>

        <!-- 表格 -->
        <a-table :dataSource="tableData" :columns="columns" :loading="loading" :pagination="pagination"
            :row-selection="rowSelection" row-key="id" size="small" @change="handleTableChange">
            <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'field_type'">
                    <a-tag>{{ record.field_type }}</a-tag>
                </template>
                <template v-if="column.key === 'is_active'">
                    <a-tag :color="record.is_active ? 'green' : 'red'">
                        {{ record.is_active ? '启用' : '禁用' }}
                    </a-tag>
                </template>
                <template v-if="column.key === 'in_current_group'">
                    <a-tag :color="record.in_current_group ? 'blue' : 'default'">
                        {{ record.in_current_group ? '已关联' : '未关联' }}
                    </a-tag>
                </template>
            </template>
        </a-table>
    </div>
</template>

<script setup lang="ts">
import api from '@/api'
import { useUserStore } from '@/store/modules/user'
import {
    ReloadOutlined,
    SaveOutlined,
    SearchOutlined
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, onMounted, ref, watch } from 'vue'

const props = defineProps<{
    fieldGroupId: number
    fieldGroupName: string
    tenantId?: number
    appName?: string
}>()

const emit = defineEmits<{
    close: []
    success: []
}>()

const userStore = useUserStore()

// 筛选条件
// filterGroupId用于筛选特定字段组的字段，默认显示当前字段组
const filterGroupId = ref<number | undefined>(props.fieldGroupId)
const searchFieldName = ref('')
const searchFieldLabel = ref('')
const searchFieldType = ref<string | undefined>(undefined)

// 字段组选项
const fieldGroupOptions = ref<{ label: string; value: number }[]>([])

// 表格数据
const loading = ref(false)
const tableData = ref<any[]>([])
const pagination = ref({
    current: 1,
    pageSize: 10,
    total: 0,
})

// 当前字段组已关联的字段ID集合
const currentGroupFieldIds = ref<Set<number>>(new Set())

// 跨分页选中的字段ID集合
const selectedRowKeys = ref<number[]>([])

// 保存加载状态
const saveLoading = ref(false)

// 表格列定义
const columns = [
    {
        title: '字段名称',
        dataIndex: 'field_name',
        key: 'field_name',
        width: 150,
    },
    {
        title: '字段标签',
        dataIndex: 'field_label',
        key: 'field_label',
        width: 150,
    },
    {
        title: '字段类型',
        dataIndex: 'field_type',
        key: 'field_type',
        width: 100,
    },
    {
        title: '所属应用',
        dataIndex: 'app_name',
        key: 'app_name',
        width: 120,
    },
    {
        title: '当前字段组状态',
        key: 'in_current_group',
        width: 120,
    },
    {
        title: '状态',
        dataIndex: 'is_active',
        key: 'is_active',
        width: 80,
    },
]

// 行选择配置
const rowSelection = computed(() => ({
    type: 'checkbox' as const,
    selectedRowKeys: selectedRowKeys.value,
    onChange: (keys: number[], rows: any[]) => {
        selectedRowKeys.value = keys
    },
    preserveSelectedRowKeys: true,
}))

// 加载字段组选项
const fetchFieldGroupOptions = async () => {
    try {
        const params: any = {}
        if (props.tenantId) {
            params.tenant_id = props.tenantId
        }
        if (props.appName) {
            params.app_name = props.appName
        }
        const res: any = await api.getFieldGroupList(params)
        if (res.code === 200) {
            // API返回的数据格式可能是 {data: [...], total: n} 或 {data: {list: [...], total: n}}
            const list = Array.isArray(res.data) ? res.data : (res.data?.list || [])
            fieldGroupOptions.value = list.map((group: any) => ({
                label: group.group_name,
                value: group.id,
            }))
        }
    } catch (error) {
        console.error('获取字段组列表失败:', error)
    }
}

// 加载当前字段组已关联的字段
const fetchCurrentGroupFields = async () => {
    try {
        const res: any = await api.getFieldSpecsByGroup({ field_group_id: props.fieldGroupId })
        if (res.code === 200) {
            const fields = res.data || []
            currentGroupFieldIds.value = new Set(fields.map((f: any) => f.id))
            // 自动勾选当前字段组的字段
            selectedRowKeys.value = Array.from(currentGroupFieldIds.value)
        }
    } catch (error) {
        console.error('获取当前字段组字段失败:', error)
    }
}

// 加载表格数据
const fetchData = async () => {
    loading.value = true
    try {
        const params: any = {
            page: pagination.value.current,
            page_size: pagination.value.pageSize,
        }

        // 如果有过滤字段组，则查询该字段组下的字段
        if (filterGroupId.value) {
            params.field_group_id = filterGroupId.value
        }

        // 搜索条件
        if (searchFieldName.value) {
            params.field_name = searchFieldName.value
        }
        if (searchFieldLabel.value) {
            params.field_label = searchFieldLabel.value
        }
        if (searchFieldType.value) {
            params.field_type = searchFieldType.value
        }

        // 租户和应用过滤
        if (props.tenantId) {
            params.tenant_id = props.tenantId
        }
        if (props.appName) {
            params.app_name = props.appName
        }

        const res: any = await api.getFieldSpecList(params)
        if (res.code === 200) {
            // API返回的数据格式可能是 {data: [...], total: n} 或 {data: {list: [...], total: n}}
            const list = Array.isArray(res.data) ? res.data : (res.data?.list || [])
            // 标记是否在当前字段组中
            tableData.value = list.map((item: any) => ({
                ...item,
                in_current_group: currentGroupFieldIds.value.has(item.id),
            }))
            pagination.value.total = Array.isArray(res.data) ? res.data.length : (res.data?.total || 0)
        }
    } catch (error) {
        console.error('获取字段列表失败:', error)
        message.error('获取字段列表失败')
    } finally {
        loading.value = false
    }
}

// 筛选字段组变更
const handleFilterGroupChange = (value: number | undefined) => {
    filterGroupId.value = value
    pagination.value.current = 1
    fetchData()
}

// 查询
const handleSearch = () => {
    pagination.value.current = 1
    fetchData()
}

// 重置
const handleReset = () => {
    filterGroupId.value = undefined
    searchFieldName.value = ''
    searchFieldLabel.value = ''
    searchFieldType.value = undefined
    pagination.value.current = 1
    fetchData()
}

// 表格分页变更
const handleTableChange = (pag: any) => {
    pagination.value.current = pag.current
    pagination.value.pageSize = pag.pageSize
    fetchData()
}

// 保存字段关联变更
const handleSave = async () => {
    saveLoading.value = true
    try {
        // 计算需要添加的字段（当前选中但不在原字段组中的）
        const toAdd = selectedRowKeys.value.filter(id => !currentGroupFieldIds.value.has(id))
        // 计算需要移除的字段（在原字段组中但当前未选中的）
        const toRemove = Array.from(currentGroupFieldIds.value).filter(id => !selectedRowKeys.value.includes(id))

        let addRes: any = null
        let removeRes: any = null

        // 执行添加
        if (toAdd.length > 0) {
            addRes = await api.batchAddFieldsToGroup({
                field_group_id: props.fieldGroupId,
                field_spec_ids: toAdd,
            })
        }

        // 执行移除
        if (toRemove.length > 0) {
            removeRes = await api.batchRemoveFieldsFromGroup({
                field_group_id: props.fieldGroupId,
                field_spec_ids: toRemove,
            })
        }

        // 处理结果
        if (toAdd.length === 0 && toRemove.length === 0) {
            message.info('没有变更需要保存')
        } else {
            const addMsg = addRes?.data?.message || (toAdd.length > 0 ? `添加 ${toAdd.length} 个字段` : '')
            const removeMsg = removeRes?.data?.message || (toRemove.length > 0 ? `移除 ${toRemove.length} 个字段` : '')
            message.success([addMsg, removeMsg].filter(Boolean).join('，'))
            // 刷新当前字段组字段列表
            await fetchCurrentGroupFields()
            // 刷新表格数据
            await fetchData()
            emit('success')
        }
    } catch (error) {
        console.error('保存字段关联失败:', error)
        message.error('保存字段关联失败')
    } finally {
        saveLoading.value = false
    }
}

// 关闭
const handleClose = () => {
    emit('close')
}

// 监听字段组ID变化
watch(() => props.fieldGroupId, async (newVal) => {
    if (newVal) {
        filterGroupId.value = newVal
        await fetchCurrentGroupFields()
        await fetchData()
    }
})

onMounted(async () => {
    await fetchFieldGroupOptions()
    await fetchCurrentGroupFields()
    await fetchData()
})
</script>

<style scoped lang="less">
.manage-fields-modal {
    .filter-area {
        margin-bottom: 16px;
        padding: 16px;
        background-color: #f5f5f5;
        border-radius: 4px;

        .filter-item-col {
            margin-bottom: 8px;
        }

        .filter-item {
            margin-bottom: 0;

            :deep(.ant-form-item-label) {
                line-height: 32px;
                padding-bottom: 4px;
            }

            // 下拉框选项文字过长时显示省略号
            :deep(.ant-select-selection-item) {
                max-width: 100%;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            :deep(.ant-select-dropdown .ant-select-item-option-content) {
                max-width: 300px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
        }

        .filter-actions {
            display: flex;
            align-items: flex-end;
            height: 100%;
            padding-bottom: 8px;
        }
    }

    .action-bar {
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
}
</style>
