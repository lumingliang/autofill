<template>
  <div class="role-page">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
      :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
      @search="handleSearch" @reset="handleReset" @table-change="handleTableChange" @modal-ok="handleSave">
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col v-if="userStore.isSuperUser" :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="租户" class="filter-item">
            <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户" allow-clear :options="tenantOptions"
              @change="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="角色名" class="filter-item">
            <a-input v-model:value="queryParams.role_name" placeholder="请输入角色名" allow-clear
              @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
      </template>

      <!-- 操作按钮 -->
      <template #actions>
        <a-button v-permission="'post/api/v1/role/create'" type="primary" @click="handleAdd">
          <PlusOutlined />
          新建角色
        </a-button>
      </template>

      <!-- 表格列自定义 -->
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

      <!-- 弹窗表单 -->
      <template #modal-form="{ form, action }">
        <a-form-item v-if="userStore.isSuperUser" label="所属租户" name="tenant_id">
          <a-select v-model:value="form.tenant_id" placeholder="请选择所属租户" :options="tenantOptions" />
        </a-form-item>
        <a-form-item label="角色名" name="name">
          <a-input v-model:value="form.name" placeholder="请输入角色名称" />
        </a-form-item>
        <a-form-item label="角色描述" name="desc">
          <a-input v-model:value="form.desc" placeholder="请输入角色描述" />
        </a-form-item>
      </template>
    </CrudTable>

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
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { useUserStore } from '@/store'
import { formatDateTime } from '@/utils'
import { PlusOutlined } from '@ant-design/icons-vue'
import { computed, onMounted, reactive, ref } from 'vue'

const userStore = useUserStore()
const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  role_name: '',
  tenant_id: undefined as number | undefined,
})

// 计算表单项数量
const filterItemCount = computed(() => {
  let count = 1
  if (userStore.isSuperUser) count++
  return count
})

// 表格数据
const loading = ref(false)
const tableData = ref<any[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
})

// 租户选项
const tenantOptions = ref<{ label: string; value: number }[]>([])

// 表格列
const columns = computed(() => [
  { title: '角色名', dataIndex: 'name', key: 'name', width: 150 },
  ...(userStore.isSuperUser ? [{ title: '所属租户', key: 'tenant_name', width: 150 }] : []),
  { title: '角色描述', dataIndex: 'desc', key: 'desc', width: 200, ellipsis: true },
  { title: '创建日期', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 280, fixed: 'right' as const },
])

// 弹窗相关
const modalTitle = ref('')
const modalLoading = ref(false)
const modalForm = reactive({
  name: '',
  desc: '',
  tenant_id: undefined as number | undefined,
})
const modalRules = computed(() => ({
  tenant_id: { required: userStore.isSuperUser, message: '请选择所属租户', trigger: ['change', 'blur'], type: 'number' },
  name: { required: true, message: '请输入角色名称', trigger: ['input', 'blur'] },
}))

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
const userOptions = ref<{ label: string; value: number }[]>([])

// 加载数据
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

// 加载租户选项
async function loadTenants() {
  if (!userStore.isSuperUser) return
  const res: any = await api.getTenantSelect()
  tenantOptions.value = (res.data || []).map((item: any) => ({ label: item.name, value: item.id }))
}

// 查询
function handleSearch() {
  pagination.current = 1
  loadData()
}

// 重置
function handleReset() {
  queryParams.role_name = ''
  queryParams.tenant_id = undefined
  handleSearch()
}

// 表格变化
function handleTableChange(p: any) {
  pagination.current = p.current
  pagination.pageSize = p.pageSize
  loadData()
}

// 新增
function handleAdd() {
  modalTitle.value = '新增角色'
  Object.assign(modalForm, { name: '', desc: '', tenant_id: undefined })
  crudTableRef.value?.openAddModal()
}

// 编辑
function handleEdit(record: any) {
  modalTitle.value = '编辑角色'
  crudTableRef.value?.openEditModal(record)
}

// 保存
async function handleSave(form: Record<string, any>, action: 'add' | 'edit') {
  try {
    modalLoading.value = true
    const apiFn = action === 'add' ? api.createRole : api.updateRole
    const res: any = await apiFn({ ...form })
    if (res.code === 200) {
      window.$message?.success(action === 'add' ? '新增成功' : '编辑成功')
      crudTableRef.value?.closeModal()
      loadData()
    }
  } catch (error) {
    console.error('保存失败', error)
  } finally {
    modalLoading.value = false
  }
}

// 删除
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

// 构建API树
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

// 设置权限
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

// 更新权限
async function updateRoleAuthorized() {
  const apiInfos: any[] = []
  apiOptions.value.forEach((group: any) => {
    if (group.children) {
      group.children.forEach((item: any) => {
        if (apiIds.value.includes(item.unique_id)) {
          apiInfos.push({ path: item.path, method: item.method })
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
    apiIds.value = (result.data?.apis || []).map((v: any) => v.method.toLowerCase() + v.path)
  } catch (error: any) {
    window.$message?.error('设置失败: ' + error.message)
  }
}

// 加载用户选项
async function loadUserOptions(roleId: number) {
  const res: any = await api.getRoleAvailableUsers({
    role_id: roleId,
    page: 1,
    page_size: 9999,
  })
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
    await loadUserOptions(record.id)
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

onMounted(() => {
  loadData()
  loadTenants()
})
</script>
