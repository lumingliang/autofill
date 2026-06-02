<template>
  <a-layout has-sider class="user-page crud-page">
    <!-- 部门列表：仅普通用户显示，默认收起 -->
    <a-layout-sider v-if="!userStore.isSuperUser" theme="light" :collapsed-width="0" :width="240" collapsible
      default-collapsed style="background: #fff; border-right: 1px solid #f0f0f0">
      <div>
        <h3 style="margin-bottom: 12px">部门列表</h3>
        <a-tree :tree-data="deptTreeData" :field-names="{ key: 'id', title: 'name' }" block-node
          @click="handleDeptClick" />
      </div>
    </a-layout-sider>
    <a-layout-content>
      <a-card>
        <a-form :model="queryParams" class="crud-filter-form smart-filter-form">
          <a-row :gutter="16" class="filter-row">
            <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
              <a-form-item label="名称" class="filter-item">
                <a-input v-model:value="queryParams.username" placeholder="请输入用户名称" allow-clear
                  @pressEnter="handleSearch" />
              </a-form-item>
            </a-col>
            <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
              <a-form-item label="邮箱" class="filter-item">
                <a-input v-model:value="queryParams.email" placeholder="请输入邮箱" allow-clear @pressEnter="handleSearch" />
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
          <a-button v-permission="'post/api/v1/user/create'" type="primary" @click="handleAddUser">
            <PlusOutlined />
            新建用户
          </a-button>
        </div>

        <a-table class="crud-table" :columns="columns" :data-source="tableData" :loading="loading"
          :pagination="pagination" row-key="id" :scroll="{ x: 'max-content' }" @change="handleTableChange">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'roles'">
              <a-tag v-for="role in record.roles" :key="role.id" color="blue" style="margin: 2px 3px">
                {{ role.name }}
              </a-tag>
            </template>

            <template v-if="column.key === 'dept'">
              {{ record.dept?.name }}
            </template>
            <template v-if="column.key === 'is_superuser'">
              <a-tag :color="record.is_superuser ? 'green' : 'default'">
                {{ record.is_superuser ? '是' : '否' }}
              </a-tag>
            </template>
            <template v-if="column.key === 'last_login'">
              <span v-if="record.last_login">{{ formatDateTime(record.last_login) }}</span>
              <span v-else>-</span>
            </template>
            <template v-if="column.key === 'is_active'">
              <a-switch :checked="!record.is_active" :loading="!!record.publishing" size="small"
                @change="() => handleUpdateDisable(record)" />
            </template>
            <template v-if="column.key === 'action'">
              <a-space>
                <a-button v-permission="'post/api/v1/user/update'" type="link" size="small"
                  @click="handleEditUser(record)">编辑</a-button>
                <a-popconfirm title="确定删除该用户吗？" @confirm="handleDeleteUser(record)">
                  <a-button v-permission="'delete/api/v1/user/delete'" type="link" danger size="small">删除</a-button>
                </a-popconfirm>
                <a-popconfirm title="确定重置用户密码为123456吗？" @confirm="handleResetPassword(record)">
                  <a-button v-permission="'post/api/v1/user/reset_password'" type="link" size="small"
                    style="color: #faad14">重置密码</a-button>
                </a-popconfirm>
                <a-popconfirm v-if="!record.is_superuser" :title="'确定快捷登录到用户 ' + record.username + ' 吗？'"
                  @confirm="handleQuickLogin(record)">
                  <a-button v-permission="'post/api/v1/base/quick_login'" type="link" size="small"
                    style="color: #722ed1">快捷登录</a-button>
                </a-popconfirm>
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
          <a-form-item label="用户名称" name="username">
            <a-input v-model:value="modalForm.username" placeholder="请输入用户名称" />
          </a-form-item>
          <a-form-item label="邮箱" name="email">
            <a-input v-model:value="modalForm.email" placeholder="请输入邮箱" />
          </a-form-item>
          <a-form-item v-if="modalAction === 'add'" label="密码" name="password">
            <a-input-password v-model:value="modalForm.password" placeholder="请输入密码" />
          </a-form-item>
          <a-form-item v-if="modalAction === 'add'" label="确认密码" name="confirmPassword">
            <a-input-password v-model:value="modalForm.confirmPassword" placeholder="请确认密码" />
          </a-form-item>

          <!-- 角色选择 -->
          <a-form-item label="角色" name="role_ids"
            :rules="[{ type: 'array', required: modalAction === 'add', message: '请至少选择一个角色', trigger: ['blur', 'change'] }]">
            <a-checkbox-group v-model:value="modalForm.role_ids">
              <a-space wrap>
                <a-checkbox v-for="item in roleOptions" :key="item.id" :value="item.id">{{ item.name }}</a-checkbox>
              </a-space>
            </a-checkbox-group>
          </a-form-item>

          <!-- 部门选择 -->
          <a-form-item label="部门" name="dept_id">
            <a-tree-select v-model:value="modalForm.dept_id" :tree-data="deptTreeData"
              :field-names="{ value: 'id', label: 'name', children: 'children' }" placeholder="请选择部门" allow-clear
              tree-default-expand-all />
          </a-form-item>

          <!-- 仅超级管理员可见超级用户开关 -->
          <a-form-item v-if="userStore.isSuperUser" label="超级用户" name="is_superuser">
            <a-switch v-model:checked="modalForm.is_superuser" />
          </a-form-item>
          <a-form-item label="禁用" name="is_active">
            <a-switch :checked="!modalForm.is_active" @change="(val: boolean) => modalForm.is_active = !val" />
          </a-form-item>
        </a-form>
      </a-modal>
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import api from '@/api'
import { useUserStore } from '@/store'
import { formatDateTime } from '@/utils'
import { PlusOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons-vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const userStore = useUserStore()

const queryParams = reactive<any>({
  username: '',
  email: '',
})

// 计算表单项数量（用于控制按钮布局）
const filterItemCount = computed(() => {
  // 基础字段：名称、邮箱
  return 2
})

// 操作按钮列的栅格配置
// 单行时宽度自适应，多行时占据标准宽度
const getActionColProps = computed(() => {
  const isSingleLine = filterItemCount.value <= 2
  if (isSingleLine) {
    // 单行模式：宽度自适应，不设置固定宽度
    return {
      xs: 24,
      sm: 12,
      md: 'auto',
      lg: 'auto',
      xl: 'auto'
    }
  }
  // 多行模式：标准宽度
  return {
    xs: 24,
    sm: 12,
    md: 8,
    lg: 6,
    xl: 6
  }
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

const roleOptions = ref<any[]>([])
const deptOptions = ref<any[]>([])

const deptTreeData = computed(() => {
  return formatTreeData(deptOptions.value)
})

function formatTreeData(data: any[]): any[] {
  if (!data) return []
  return data.map((item) => ({
    ...item,
    children: item.children ? formatTreeData(item.children) : undefined,
  }))
}

const columns = computed(() => [
  { title: '名称', dataIndex: 'username', key: 'username', width: 120, ellipsis: true, resizable: true },
  { title: '邮箱', dataIndex: 'email', key: 'email', width: 180, ellipsis: true, resizable: true },
  { title: '用户角色', key: 'roles', width: 150, resizable: true },

  { title: '部门', key: 'dept', width: 120, ellipsis: true, resizable: true },
  { title: '超级用户', key: 'is_superuser', width: 90, resizable: true },
  { title: '上次登录时间', key: 'last_login', width: 180, ellipsis: true, resizable: true },
  { title: '禁用', key: 'is_active', width: 70, resizable: true },
  { title: '操作', key: 'action', width: 240, fixed: 'right' },
])

const modalVisible = ref(false)
const modalLoading = ref(false)
const modalAction = ref<'add' | 'edit'>('add')
const modalTitle = computed(() => (modalAction.value === 'add' ? '新增用户' : '编辑用户'))
const modalFormRef = ref()
const modalForm = reactive<any>({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  is_superuser: false,
  is_active: true,
  dept_id: undefined,
  role_ids: [],
})

const modalRules = computed(() => ({
  username: [{ required: true, message: '请输入名称', trigger: ['input', 'blur'] }],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: ['input', 'change'] },
    {
      validator: (_rule: any, value: string) => {
        if (!value) return Promise.resolve()
        const re = /^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$/
        if (!re.test(value)) return Promise.reject('邮箱格式错误')
        return Promise.resolve()
      },
      trigger: 'blur',
    },
  ],
  password: [{ required: modalAction.value === 'add', message: '请输入密码', trigger: ['input', 'blur', 'change'] }],
  confirmPassword: [
    { required: modalAction.value === 'add', message: '请再次输入密码', trigger: ['input'] },
    {
      validator: (_rule: any, value: string) => {
        if (modalAction.value === 'edit') return Promise.resolve()
        if (value !== modalForm.password) return Promise.reject('两次密码输入不一致')
        return Promise.resolve()
      },
      trigger: 'blur',
    },
  ],
}))

async function loadData() {
  loading.value = true
  try {
    const params = {
      ...queryParams,
      page: pagination.current,
      page_size: pagination.pageSize,
    }
    const res: any = await api.getUserList(params)
    tableData.value = res.data || []
    pagination.total = res.total || 0
  } finally {
    loading.value = false
  }
}

async function loadRoles() {
  const params: any = { page: 1, page_size: 9999 }
  const res: any = await api.getRoleList(params)
  roleOptions.value = res.data || []
}

async function loadDepts() {
  const params: any = {}
  const res: any = await api.getDepts(params)
  deptOptions.value = res.data || []
}

function handleSearch() {
  pagination.current = 1
  loadData()
}

function handleReset() {
  queryParams.username = ''
  queryParams.email = ''
  handleSearch()
}

function handleTableChange(p: any) {
  pagination.current = p.current
  pagination.pageSize = p.pageSize
  loadData()
}

function handleAddUser() {
  // 检查是否选择了租户（超管需要选择租户，普通用户使用当前租户）
  // 注意：检查 currentTenant（右上角选择器的选择状态）而不是 currentTenantId（JWT中的租户ID）
  if (userStore.isSuperUser && !userStore.currentTenant) {
    window.$message?.warning('请先选择租户')
    return
  }

  modalAction.value = 'add'
  Object.assign(modalForm, {
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    is_superuser: false,
    is_active: true,
    dept_id: undefined,
    role_ids: [],
  })
  roleOptions.value = []
  deptOptions.value = []

  loadRoles()
  loadDepts()
  modalVisible.value = true
}

async function handleEditUser(record: any) {
  // 检查是否选择了租户（超管需要选择租户，普通用户使用当前租户）
  // 注意：检查 currentTenant（右上角选择器的选择状态）而不是 currentTenantId（JWT中的租户ID）
  if (userStore.isSuperUser && !userStore.currentTenant) {
    window.$message?.warning('请先选择租户')
    return
  }

  modalAction.value = 'edit'
  Object.assign(modalForm, {
    id: record.id,
    username: record.username,
    email: record.email,
    password: '',
    confirmPassword: '',
    is_superuser: record.is_superuser,
    is_active: record.is_active,
    dept_id: record.dept?.id || null,
    role_ids: [],
  })
  roleOptions.value = []
  deptOptions.value = []

  await loadRoles()
  await loadDepts()
  // 从record.roles中提取角色ID
  modalForm.role_ids = record.roles?.map((r: any) => r.id) || []

  modalVisible.value = true
}

async function handleSave() {
  try {
    await modalFormRef.value.validate()
    modalLoading.value = true

    // 编辑用户时使用单租户角色更新接口
    if (modalAction.value === 'edit') {
      const params: any = {
        user_id: modalForm.id,
        role_ids: modalForm.role_ids || [],
      }
      const res: any = await api.updateUserTenantRoles(params)
      if (res.code === 200) {
        window.$message?.success('编辑成功')
        modalVisible.value = false
        loadData()
      } else {
        window.$message?.error(res.msg || '编辑失败')
      }
      return
    }

    // 新增用户使用原有接口
    const data = { ...modalForm }
    delete data.confirmPassword
    delete data.dept

    // 角色ID
    data.role_ids = modalForm.role_ids || []

    const res: any = await api.createUser(data)
    if (res.code === 200) {
      window.$message?.success('新增成功')
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

async function handleDeleteUser(record: any) {
  try {
    const res: any = await api.deleteUser({ user_id: record.id })
    if (res.code === 200) {
      window.$message?.success('删除成功')
      loadData()
    }
  } catch (error) {
    console.error('删除失败', error)
  }
}

async function handleResetPassword(record: any) {
  try {
    const res: any = await api.resetPassword({ user_id: record.id })
    if (res.code === 200) {
      window.$message?.success('密码已成功重置为123456')
      loadData()
    }
  } catch (error: any) {
    window.$message?.error('重置密码失败: ' + error.message)
  }
}

async function handleQuickLogin(record: any) {
  if (userStore.userId === record.id) {
    window.$message?.error('不能快捷登录到当前用户！')
    return
  }

  try {
    const hide = window.$message?.loading('正在快捷登录...', 0)
    const res: any = await api.quickLogin({ target_user_id: record.id })
    hide?.()

    if (res.code === 200) {
      const { access_token, current_tenant_id } = res.data

      const originalToken = localStorage.getItem('access_token')
      if (originalToken) {
        localStorage.setItem('original_token', originalToken)
      }

      const pendingAuth = {
        token: access_token,
        currentTenantId: current_tenant_id,
        isQuickLogin: true,
        targetUser: record.username,
      }
      localStorage.setItem('pending_auth', JSON.stringify(pendingAuth))

      await userStore.logoutWithoutRedirect()
      router.push('/login')
    } else {
      window.$message?.error(res.msg || '快捷登录失败')
    }
  } catch (error: any) {
    window.$message?.error('快捷登录失败: ' + error.message)
  }
}

async function handleUpdateDisable(row: any) {
  if (!row.id) return
  if (userStore.userId === row.id) {
    window.$message?.error('当前登录用户不可禁用！')
    return
  }
  row.publishing = true
  const newStatus = !row.is_active
  const role_ids = row.roles?.map((e: any) => e.id) || []
  const dept_id = row.dept?.id
  try {
    await api.updateUser({
      id: row.id,
      is_active: newStatus,
      role_ids,
      dept_id,
      username: row.username,
      email: row.email,
    })
    row.is_active = newStatus
    window.$message?.success(newStatus ? '已取消禁用该用户' : '已禁用该用户')
    loadData()
  } catch (err) {
    console.error(err)
  } finally {
    row.publishing = false
  }
}

async function handleModalTenantChange() {
  modalForm.role_ids = []
  modalForm.dept_id = undefined
  await loadRoles()
  await loadDepts()
}

let lastClickedNodeId: number | null = null

function handleDeptClick(_selectedKeys: any, e: any) {
  const node = e.node
  if (!node) return
  if (lastClickedNodeId === node.id) {
    queryParams.dept_id = undefined
    lastClickedNodeId = null
    loadData()
  } else {
    queryParams.dept_id = node.id
    lastClickedNodeId = node.id
    loadData()
  }
}

onMounted(() => {
  loadData()
  if (!userStore.isSuperUser) {
    loadRoles()
    loadDepts()
  }
})
</script>

<style scoped lang="less">
.user-page {
  .table-actions {
    margin-bottom: 16px;
  }
}
</style>
