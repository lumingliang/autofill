<template>
  <div class="role-page">
    <a-card>
      <a-form layout="inline" :model="queryParams" class="search-form">
        <a-form-item label="角色名">
          <a-input v-model:value="queryParams.role_name" placeholder="请输入角色名" allow-clear @pressEnter="handleSearch" />
        </a-form-item>
        <a-form-item v-if="userStore.isSuperUser" label="租户">
          <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户" allow-clear style="width: 180px"
            :options="tenantOptions" @change="handleSearch" />
        </a-form-item>
        <a-form-item>
          <a-space>
            <a-button type="primary" @click="handleSearch">查询</a-button>
            <a-button @click="handleReset">重置</a-button>
          </a-space>
        </a-form-item>
      </a-form>

      <div class="table-actions">
        <a-button v-permission="'post/api/v1/role/create'" type="primary" @click="handleAdd">
          <PlusOutlined />
          新建角色
        </a-button>
      </div>

      <a-table :columns="columns" :data-source="tableData" :loading="loading" :pagination="pagination" row-key="id"
        @change="handleTableChange">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <a-tag color="blue">{{ record.name }}</a-tag>
          </template>
          <template v-if="column.key === 'tenant_name'">
            <a-tag color="orange">{{ record.tenant_name || '系统角色' }}</a-tag>
          </template>
          <template v-if="column.key === 'created_at'">
            {{ formatDateTime(record.created_at) }}
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button v-permission="'post/api/v1/role/update'" type="link" size="small"
                @click="handleEdit(record)">编辑</a-button>
              <a-popconfirm title="确定删除该角色吗？" @confirm="handleDelete(record)">
                <a-button v-permission="'delete/api/v1/role/delete'" type="link" danger size="small">删除</a-button>
              </a-popconfirm>
              <a-button v-permission="'get/api/v1/role/authorized'" type="link" size="small"
                @click="handleSetPermission(record)">设置权限</a-button>
              <a-button v-permission="'post/api/v1/role/assign_users'" type="link" size="small"
                @click="handleAssignUsers(record)">分配用户</a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 新增/编辑 弹窗 -->
    <a-modal v-model:open="modalVisible" :title="modalTitle" :confirm-loading="modalLoading" @ok="handleSave"
      @cancel="modalVisible = false">
      <a-form ref="modalFormRef" :model="modalForm" :rules="modalRules" :label-col="{ span: 6 }"
        :wrapper-col="{ span: 16 }">
        <a-form-item v-if="userStore.isSuperUser" label="所属租户" name="tenant_id">
          <a-select v-model:value="modalForm.tenant_id" placeholder="请选择所属租户" :options="tenantOptions" />
        </a-form-item>
        <a-form-item label="角色名" name="name">
          <a-input v-model:value="modalForm.name" placeholder="请输入角色名称" />
        </a-form-item>
        <a-form-item label="角色描述" name="desc">
          <a-input v-model:value="modalForm.desc" placeholder="请输入角色描述" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 设置权限 Drawer -->
    <a-drawer v-model:open="drawerVisible" title="设置权限" placement="right" :width="500"
      :footer-style="{ textAlign: 'right' }">
      <a-input v-model:value="pattern" placeholder="筛选" style="margin-bottom: 16px" />
      <a-tabs v-model:activeKey="activeTab">
        <a-tab-pane key="menu" tab="菜单权限">
          <a-tree v-model:checkedKeys="menuIds" checkable :tree-data="menuOptions"
            :field-names="{ title: 'name', key: 'id', children: 'children' }" :search-value="pattern"
            :default-expand-all="true" :block-node="true" :selectable="false" />
        </a-tab-pane>
        <a-tab-pane key="api" tab="接口权限">
          <a-tree ref="apiTreeRef" v-model:checkedKeys="apiIds" checkable :tree-data="apiOptions"
            :field-names="{ title: 'summary', key: 'unique_id', children: 'children' }" :search-value="pattern"
            :default-expand-all="true" :block-node="true" :selectable="false" />
        </a-tab-pane>
      </a-tabs>
      <template #footer>
        <a-button v-permission="'post/api/v1/role/authorized'" type="primary"
          @click="updateRoleAuthorized">确定</a-button>
      </template>
    </a-drawer>

    <!-- 分配用户弹窗 -->
    <a-modal v-model:open="assignUserModalVisible" title="分配用户" :confirm-loading="assignUserModalLoading"
      @ok="handleSaveAssignUsers" @cancel="assignUserModalVisible = false" width="600px">
      <a-form :label-col="{ span: 4 }" :wrapper-col="{ span: 20 }">
        <a-form-item label="角色">
          <a-tag color="blue">{{ currentRole?.name }}</a-tag>
          <a-tag v-if="currentRole?.tenant_name" color="orange">{{ currentRole.tenant_name }}</a-tag>
          <span v-else-if="currentRole && !currentRole.tenant_id" class="ant-tag ant-tag-orange">系统角色</span>
        </a-form-item>
        <a-form-item label="选择用户">
          <a-select v-model:value="selectedUserIds" mode="multiple" placeholder="请选择要分配的用户" style="width: 100%"
            :options="userOptions" show-search :filter-option="filterUserOption" allow-clear />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '@/store'
import api from '@/api'
import { formatDateTime } from '@/utils'

const userStore = useUserStore()

const queryParams = reactive<any>({
  role_name: '',
  tenant_id: undefined,
})

const loading = ref(false)
const tableData = ref<any[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

const tenantOptions = ref<any[]>([])

const columns = computed(() => [
  { title: '角色名', dataIndex: 'name', key: 'name' },
  ...(userStore.isSuperUser ? [{ title: '所属租户', key: 'tenant_name' }] : []),
  { title: '角色描述', dataIndex: 'desc', key: 'desc' },
  { title: '创建日期', dataIndex: 'created_at', key: 'created_at' },
  { title: '操作', key: 'action', width: 200 },
])

const modalVisible = ref(false)
const modalLoading = ref(false)
const modalAction = ref<'add' | 'edit'>('add')
const modalTitle = computed(() => (modalAction.value === 'add' ? '新增角色' : '编辑角色'))
const modalFormRef = ref()
const modalForm = reactive<any>({
  name: '',
  desc: '',
  tenant_id: undefined,
})

const modalRules = {
  tenant_id: { required: true, message: '请选择所属租户', trigger: ['change', 'blur'], type: 'number' },
  name: { required: true, message: '请输入角色名称', trigger: ['input', 'blur'] },
}

// 权限设置
const drawerVisible = ref(false)
const pattern = ref('')
const activeTab = ref('menu')
const menuOptions = ref<any[]>([])
const menuIds = ref<number[]>([])
const apiOptions = ref<any[]>([])
const apiIds = ref<string[]>([])
const roleId = ref(0)
const apiTreeRef = ref<any>(null)

// 分配用户
const assignUserModalVisible = ref(false)
const assignUserModalLoading = ref(false)
const currentRole = ref<any>(null)
const selectedUserIds = ref<number[]>([])
const userOptions = ref<any[]>([])

async function loadData() {
  loading.value = true
  try {
    const params = {
      ...queryParams,
      page: pagination.current,
      page_size: pagination.pageSize,
    }
    const res: any = await api.getRoleList(params)
    tableData.value = res.data || []
    pagination.total = res.total || 0
  } finally {
    loading.value = false
  }
}

async function loadTenants() {
  if (!userStore.isSuperUser) return
  const res: any = await api.getTenantSelect()
  tenantOptions.value = (res.data || []).map((item: any) => ({ label: item.name, value: item.id }))
}

function handleSearch() {
  pagination.current = 1
  loadData()
}

function handleReset() {
  queryParams.role_name = ''
  queryParams.tenant_id = undefined
  handleSearch()
}

function handleTableChange(p: any) {
  pagination.current = p.current
  pagination.pageSize = p.pageSize
  loadData()
}

function handleAdd() {
  modalAction.value = 'add'
  Object.assign(modalForm, {
    name: '',
    desc: '',
    tenant_id: undefined,
  })
  modalVisible.value = true
}

function handleEdit(record: any) {
  modalAction.value = 'edit'
  Object.assign(modalForm, { ...record })
  modalVisible.value = true
}

async function handleSave() {
  try {
    await modalFormRef.value.validate()
    modalLoading.value = true
    const apiFn = modalAction.value === 'add' ? api.createRole : api.updateRole
    const res: any = await apiFn({ ...modalForm })
    if (res.code === 200) {
      window.$message?.success(modalAction.value === 'add' ? '新增成功' : '编辑成功')
      modalVisible.value = false
      loadData()
    }
  } catch (error: any) {
    if (error.errorFields) return
    console.error('保存失败', error)
  } finally {
    modalLoading.value = false
  }
}

async function handleDelete(record: any) {
  try {
    const res: any = await api.deleteRole({ role_id: record.id })
    if (res.code === 200) {
      window.$message?.success('删除成功')
      loadData()
    }
  } catch (error) {
    console.error('删除失败', error)
  }
}

function buildApiTree(data: any[]) {
  const groupedData: any = {}
  data.forEach((item: any) => {
    const tags = item['tags']
    const pathParts = item['path'].split('/')
    const path = pathParts.slice(0, -1).join('/')
    const summary = tags.charAt(0).toUpperCase() + tags.slice(1)
    const unique_id = item['method'].toLowerCase() + item['path']
    if (!(path in groupedData)) {
      groupedData[path] = { unique_id: path, path: path, summary: summary, children: [] }
    }
    groupedData[path].children.push({
      id: item['id'],
      path: item['path'],
      method: item['method'],
      summary: item['summary'],
      unique_id: unique_id,
    })
  })
  return Object.values(groupedData)
}

async function handleSetPermission(record: any) {
  try {
    const [menusResponse, apisResponse, roleAuthorizedResponse] = await Promise.all([
      api.getMenus({ page: 1, page_size: 9999 }),
      api.getApis({ page: 1, page_size: 9999 }),
      api.getRoleAuthorized({ id: record.id }),
    ])

    menuOptions.value = menusResponse.data || []
    apiOptions.value = buildApiTree(apisResponse.data || [])
    menuIds.value = (roleAuthorizedResponse.data?.menus || []).map((v: any) => v.id)
    apiIds.value = (roleAuthorizedResponse.data?.apis || []).map(
      (v: any) => v.method.toLowerCase() + v.path
    )

    drawerVisible.value = true
    roleId.value = record.id
  } catch (error) {
    console.error('Error loading data:', error)
  }
}

async function updateRoleAuthorized() {
  const apiInfos: any[] = []
  apiOptions.value.forEach((group: any) => {
    if (group.children) {
      group.children.forEach((item: any) => {
        if (apiIds.value.includes(item.unique_id)) {
          apiInfos.push({
            path: item.path,
            method: item.method,
          })
        }
      })
    }
  })

  try {
    const res: any = await api.updateRoleAuthorized({
      id: roleId.value,
      menu_ids: menuIds.value,
      api_infos: apiInfos,
    })
    if (res.code === 200) {
      window.$message?.success('设置成功')
    } else {
      window.$message?.error(res.msg || '设置失败')
    }

    const result = await api.getRoleAuthorized({ id: roleId.value })
    menuIds.value = (result.data?.menus || []).map((v: any) => v.id)
    apiIds.value = (result.data?.apis || []).map(
      (v: any) => v.method.toLowerCase() + v.path
    )
  } catch (error: any) {
    window.$message?.error('设置失败: ' + error.message)
  }
}

onMounted(() => {
  loadData()
  loadTenants()
})

// 加载用户列表（用于下拉选择）
async function loadUserOptions(tenantId?: number) {
  const params: any = { page: 1, page_size: 9999 }
  if (tenantId) {
    params.tenant_id = tenantId
  }
  const res: any = await api.getUserList(params)
  userOptions.value = (res.data || []).map((item: any) => ({
    label: `${item.username} (${item.email})`,
    value: item.id,
  }))
}

// 过滤用户选项
function filterUserOption(input: string, option: any) {
  return option.label.toLowerCase().includes(input.toLowerCase())
}

// 打开分配用户弹窗
async function handleAssignUsers(record: any) {
  currentRole.value = record
  assignUserModalVisible.value = true
  selectedUserIds.value = []

  try {
    // 加载用户列表
    await loadUserOptions(record.tenant_id)

    // 获取当前角色已分配的用户
    const res: any = await api.getRoleUsers({ role_id: record.id })
    if (res.code === 200) {
      selectedUserIds.value = res.data || []
    }
  } catch (error) {
    console.error('加载数据失败', error)
  }
}

// 保存分配用户
async function handleSaveAssignUsers() {
  try {
    assignUserModalLoading.value = true
    const res: any = await api.assignUsersToRole({
      role_id: currentRole.value?.id,
      user_ids: selectedUserIds.value,
    })
    if (res.code === 200) {
      window.$message?.success('分配成功')
      assignUserModalVisible.value = false
    } else {
      window.$message?.error(res.msg || '分配失败')
    }
  } catch (error: any) {
    window.$message?.error('分配失败: ' + error.message)
  } finally {
    assignUserModalLoading.value = false
  }
}
</script>

<style scoped lang="less">
.role-page {
  .search-form {
    margin-bottom: 16px;
  }

  .table-actions {
    margin-bottom: 16px;
  }
}
</style>
