<template>
  <div class="tenant-page">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
      :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
      @search="handleSearch" @reset="handleReset" @table-change="handleTableChange" @modal-ok="handleSave">
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="租户名称" class="filter-item">
            <a-input v-model:value="queryParams.name" placeholder="请输入租户名称" allow-clear @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="域名" class="filter-item">
            <a-input v-model:value="queryParams.domain" placeholder="请输入域名" allow-clear @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
      </template>

      <!-- 操作按钮 -->
      <template #actions>
        <a-button v-permission="'post/api/v1/tenant/create'" type="primary" @click="handleAdd">
          <PlusOutlined />
          新建租户
        </a-button>
      </template>

      <!-- 表格列自定义 -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'is_active'">
          <a-tag :color="record.is_active ? 'success' : 'error'">
            {{ record.is_active ? '启用' : '禁用' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'created_at'">
          {{ formatDateTime(record.created_at) }}
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button v-permission="'post/api/v1/tenant/update'" type="link" size="small"
              @click="handleEdit(record)">编辑</a-button>
            <a-button v-permission="'get/api/v1/tenant/assigned_users'" type="link" size="small"
              @click="handleViewAssignedUsers(record)">已分配用户</a-button>
            <a-button v-permission="'post/api/v1/tenant/batch_add_users'" type="link" size="small"
              @click="handleAssignUsers(record)">分配用户</a-button>
            <a-popconfirm title="确定删除该租户吗？删除后该租户下的所有数据将无法访问！" @confirm="handleDelete(record)">
              <a-button v-permission="'delete/api/v1/tenant/delete'" type="link" danger size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>

      <!-- 弹窗表单 -->
      <template #modal-form="{ form }">
        <a-form-item label="租户名称" name="name">
          <a-input v-model:value="form.name" placeholder="请输入租户名称" />
        </a-form-item>
        <a-form-item label="域名" name="domain">
          <a-input v-model:value="form.domain" placeholder="请输入租户域名，如：tenant-a" />
          <span style="color: #999; font-size: 12px">域名只能包含字母、数字和横线，用于标识租户</span>
        </a-form-item>
        <a-form-item label="描述" name="description">
          <a-textarea v-model:value="form.description" placeholder="请输入租户描述" :rows="3" />
        </a-form-item>
        <a-form-item label="启用" name="is_active">
          <a-switch v-model:checked="form.is_active" />
        </a-form-item>
      </template>
    </CrudTable>

    <!-- 分配用户弹窗 - 支持跨页勾选 -->
    <a-modal v-model:open="assignModalVisible" title="分配用户" :width="750" :confirm-loading="assignModalLoading"
      @ok="handleAssignConfirm" @cancel="handleAssignCancel">
      <div class="assign-users-container">
        <!-- 搜索区域 -->
        <div class="search-area">
          <a-input-search v-model:value="userSearchKeyword" placeholder="搜索用户名或邮箱" allow-clear
            @search="handleUserSearch" @pressEnter="handleUserSearch" />
        </div>

        <!-- 用户列表 - 使用 preserveSelectedRowKeys 支持跨页勾选 -->
        <div class="user-list-area">
          <a-table :columns="userColumns" :data-source="userList" :loading="userLoading" :pagination="userPagination"
            size="small" row-key="id" 
            :row-selection="{ 
              selectedRowKeys: selectedUserKeys, 
              onChange: onUserSelectChange,
              preserveSelectedRowKeys: true
            }"
            @change="handleUserTableChange">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'is_active'">
                <a-tag :color="record.is_active ? 'success' : 'error'">
                  {{ record.is_active ? '启用' : '禁用' }}
                </a-tag>
              </template>
            </template>
          </a-table>
        </div>

        <!-- 已选择提示 -->
        <div class="selected-info">
          <a-space>
            <span>已选择 <a-tag color="blue">{{ selectedUserKeys.length }}</a-tag> 个用户</span>
            <a-button v-if="selectedUserKeys.length > 0" type="link" size="small" @click="clearUserSelection">清空选择</a-button>
          </a-space>
        </div>
      </div>
    </a-modal>

    <!-- 已分配用户弹窗 - 支持批量解除 -->
    <a-modal v-model:open="assignedUsersModalVisible" title="已分配用户" :width="800" 
      :footer="null" @cancel="handleAssignedUsersCancel">
      <div class="assigned-users-container">
        <!-- 搜索区域 -->
        <div class="search-area">
          <a-input-search v-model:value="assignedUserSearchKeyword" placeholder="搜索用户名或邮箱" allow-clear
            @search="handleAssignedUserSearch" @pressEnter="handleAssignedUserSearch" />
        </div>

        <!-- 已分配用户列表 - 支持跨页勾选 -->
        <div class="user-list-area">
          <a-table :columns="assignedUserColumns" :data-source="assignedUserList" :loading="assignedUserLoading" 
            :pagination="assignedUserPagination" size="small" row-key="id"
            :row-selection="{ 
              selectedRowKeys: selectedAssignedUserKeys, 
              onChange: onAssignedUserSelectChange,
              preserveSelectedRowKeys: true
            }"
            @change="handleAssignedUserTableChange">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'is_active'">
                <a-tag :color="record.is_active ? 'success' : 'error'">
                  {{ record.is_active ? '启用' : '禁用' }}
                </a-tag>
              </template>
              <template v-if="column.key === 'assigned_at'">
                {{ formatDateTime(record.assigned_at) }}
              </template>
            </template>
          </a-table>
        </div>

        <!-- 底部操作栏 -->
        <div class="footer-actions">
          <a-space>
            <span>已选择 <a-tag color="blue">{{ selectedAssignedUserKeys.length }}</a-tag> 个用户</span>
            <a-button v-if="selectedAssignedUserKeys.length > 0" type="link" size="small" @click="clearAssignedUserSelection">清空选择</a-button>
            <a-button 
              v-if="selectedAssignedUserKeys.length > 0" 
              type="primary" 
              danger 
              size="small"
              :loading="removeUsersLoading"
              @click="handleBatchRemoveUsers">
              批量解除分配
            </a-button>
          </a-space>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { formatDateTime } from '@/utils'
import { PlusOutlined } from '@ant-design/icons-vue'
import { computed, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'TenantPage' })

const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  name: '',
  domain: '',
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
const modalForm = reactive({
  id: undefined as number | undefined,
  name: '',
  domain: '',
  description: '',
  is_active: true,
})

// 分配用户弹窗数据
const assignModalVisible = ref(false)
const assignModalLoading = ref(false)
const currentTenant = ref<any>(null)
const userSearchKeyword = ref('')
const userList = ref<any[]>([])
const userLoading = ref(false)
const selectedUserKeys = ref<number[]>([])
const userPagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
})

// 已分配用户弹窗数据
const assignedUsersModalVisible = ref(false)
const assignedUserSearchKeyword = ref('')
const assignedUserList = ref<any[]>([])
const assignedUserLoading = ref(false)
const selectedAssignedUserKeys = ref<number[]>([])
const assignedUserPagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
})
const removeUsersLoading = ref(false)

// 计算属性
const columns = computed(() => [
  { title: '租户名称', dataIndex: 'name', key: 'name', width: 150, ellipsis: true },
  { title: '域名', dataIndex: 'domain', key: 'domain', width: 200, ellipsis: true },
  { title: '描述', dataIndex: 'description', key: 'description', width: 250, ellipsis: true },
  { title: '状态', key: 'is_active', width: 80 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 280, fixed: 'right' },
])

const userColumns = computed(() => [
  { title: '用户名', dataIndex: 'username', key: 'username', width: 120 },
  { title: '邮箱', dataIndex: 'email', key: 'email', width: 180, ellipsis: true },
  { title: '状态', key: 'is_active', width: 80 },
])

const assignedUserColumns = computed(() => [
  { title: '用户名', dataIndex: 'username', key: 'username', width: 120 },
  { title: '邮箱', dataIndex: 'email', key: 'email', width: 180, ellipsis: true },
  { title: '状态', key: 'is_active', width: 80 },
  { title: '分配时间', dataIndex: 'assigned_at', key: 'assigned_at', width: 180 },
])

const filterItemCount = computed(() => 2)

const modalRules = {
  name: [{ required: true, message: '请输入租户名称', trigger: ['input', 'blur'] }],
  domain: [
    { required: true, message: '请输入租户域名', trigger: ['input', 'blur'] },
    {
      validator: (_rule: any, value: string) => {
        if (!value) return Promise.resolve()
        const re = /^[a-zA-Z0-9-]+$/
        if (!re.test(value)) return Promise.reject('域名只能包含字母、数字和横线')
        return Promise.resolve()
      },
      trigger: 'blur',
    },
  ],
}

// 加载数据
async function loadData() {
  loading.value = true
  try {
    const params = {
      ...queryParams,
      page: pagination.current,
      page_size: pagination.pageSize,
    }
    const res: any = await api.getTenantList(params)
    tableData.value = res.data || []
    pagination.total = res.total || 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.current = 1
  loadData()
}

function handleReset() {
  queryParams.name = ''
  queryParams.domain = ''
  handleSearch()
}

function handleTableChange(p: any) {
  pagination.current = p.current
  pagination.pageSize = p.pageSize
  loadData()
}

function handleAdd() {
  modalTitle.value = '新增租户'
  Object.assign(modalForm, {
    id: undefined,
    name: '',
    domain: '',
    description: '',
    is_active: true,
  })
  crudTableRef.value?.openAddModal()
}

function handleEdit(record: any) {
  modalTitle.value = '编辑租户'
  Object.assign(modalForm, { ...record })
  crudTableRef.value?.openEditModal(record)
}

async function handleSave(form: Record<string, any>, action: 'add' | 'edit') {
  modalLoading.value = true
  try {
    const apiFn = action === 'add' ? api.createTenant : api.updateTenant
    const res: any = await apiFn({ ...form })
    if (res.code === 200) {
      window.$message?.success(action === 'add' ? '新增成功' : '编辑成功')
      crudTableRef.value?.closeModal()
      loadData()
    }
  } finally {
    modalLoading.value = false
  }
}

async function handleDelete(record: any) {
  try {
    const res: any = await api.deleteTenant({ tenant_id: record.id })
    if (res.code === 200) {
      window.$message?.success('删除成功')
      loadData()
    }
  } catch (error) {
    console.error('删除失败', error)
  }
}

// 分配用户相关方法
function handleAssignUsers(record: any) {
  currentTenant.value = record
  assignModalVisible.value = true
  userSearchKeyword.value = ''
  selectedUserKeys.value = []
  userPagination.current = 1
  loadUserList()
}

async function loadUserList() {
  if (!currentTenant.value) return

  userLoading.value = true
  try {
    const params = {
      keyword: userSearchKeyword.value,
      exclude_tenant_id: currentTenant.value.id,
      page: userPagination.current,
      page_size: userPagination.pageSize,
    }
    const res: any = await api.searchUsersForTenant(params)
    userList.value = res.data || []
    userPagination.total = res.total || 0
  } finally {
    userLoading.value = false
  }
}

function handleUserSearch() {
  userPagination.current = 1
  loadUserList()
}

function handleUserTableChange(p: any) {
  userPagination.current = p.current
  userPagination.pageSize = p.pageSize
  loadUserList()
}

function onUserSelectChange(selectedRowKeys: number[]) {
  selectedUserKeys.value = selectedRowKeys
}

function clearUserSelection() {
  selectedUserKeys.value = []
}

async function handleAssignConfirm() {
  if (selectedUserKeys.value.length === 0) {
    window.$message?.warning('请至少选择一个用户')
    return
  }

  assignModalLoading.value = true
  try {
    const res: any = await api.batchAddUsersToTenant({
      tenant_id: currentTenant.value.id,
      user_ids: selectedUserKeys.value,
    })
    if (res.code === 200) {
      window.$message?.success(res.msg || '分配成功')
      assignModalVisible.value = false
    }
  } finally {
    assignModalLoading.value = false
  }
}

function handleAssignCancel() {
  assignModalVisible.value = false
  currentTenant.value = null
  selectedUserKeys.value = []
  userList.value = []
}

// 已分配用户相关方法
function handleViewAssignedUsers(record: any) {
  currentTenant.value = record
  assignedUsersModalVisible.value = true
  assignedUserSearchKeyword.value = ''
  selectedAssignedUserKeys.value = []
  assignedUserPagination.current = 1
  loadAssignedUserList()
}

async function loadAssignedUserList() {
  if (!currentTenant.value) return

  assignedUserLoading.value = true
  try {
    const params = {
      tenant_id: currentTenant.value.id,
      keyword: assignedUserSearchKeyword.value,
      page: assignedUserPagination.current,
      page_size: assignedUserPagination.pageSize,
    }
    const res: any = await api.getTenantAssignedUsers(params)
    assignedUserList.value = res.data || []
    assignedUserPagination.total = res.total || 0
  } finally {
    assignedUserLoading.value = false
  }
}

function handleAssignedUserSearch() {
  assignedUserPagination.current = 1
  loadAssignedUserList()
}

function handleAssignedUserTableChange(p: any) {
  assignedUserPagination.current = p.current
  assignedUserPagination.pageSize = p.pageSize
  loadAssignedUserList()
}

function onAssignedUserSelectChange(selectedRowKeys: number[]) {
  selectedAssignedUserKeys.value = selectedRowKeys
}

function clearAssignedUserSelection() {
  selectedAssignedUserKeys.value = []
}

async function handleBatchRemoveUsers() {
  if (selectedAssignedUserKeys.value.length === 0) {
    window.$message?.warning('请至少选择一个用户')
    return
  }

  removeUsersLoading.value = true
  try {
    const res: any = await api.batchRemoveUsersFromTenant({
      tenant_id: currentTenant.value.id,
      user_ids: selectedAssignedUserKeys.value,
    })
    if (res.code === 200) {
      window.$message?.success(res.msg || '解除分配成功')
      selectedAssignedUserKeys.value = []
      loadAssignedUserList()
    }
  } finally {
    removeUsersLoading.value = false
  }
}

function handleAssignedUsersCancel() {
  assignedUsersModalVisible.value = false
  currentTenant.value = null
  selectedAssignedUserKeys.value = []
  assignedUserList.value = []
}

onMounted(loadData)
</script>

<style scoped lang="less">
.tenant-page {
  padding: 20px;
}

.assign-users-container,
.assigned-users-container {
  .search-area {
    margin-bottom: 16px;
  }

  .user-list-area {
    margin-bottom: 16px;
  }

  .selected-info,
  .footer-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #666;
  }
}
</style>
