<script setup>
import { computed, h, nextTick, onMounted, ref, resolveDirective, withDirectives, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton,
  NCheckbox,
  NCheckboxGroup,
  NForm,
  NFormItem,
  NInput,
  NSpace,
  NSwitch,
  NTag,
  NPopconfirm,
  NLayout,
  NLayoutSider,
  NLayoutContent,
  NTreeSelect,
  NSelect,
  NTree,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'

import { formatDate, renderIcon, lStorage } from '@/utils'
import { useCRUD } from '@/composables'
import api from '@/api'
import { addDynamicRoutes } from '@/router'
import TheIcon from '@/components/icon/TheIcon.vue'
import { useUserStore } from '@/store'

defineOptions({ name: '用户管理' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')
const router = useRouter()

const userStore = useUserStore()
const isSuperUser = computed(() => userStore.isSuperUser)
const currentTenantId = computed(() => userStore.userInfo?.current_tenant_id)

const {
  modalVisible,
  modalTitle,
  modalAction,
  modalLoading,
  handleSave,
  modalForm,
  modalFormRef,
  handleEdit,
  handleDelete,
  handleAdd,
} = useCRUD({
  name: '用户',
  initForm: {
    is_active: true,
    is_superuser: false,
    role_ids: [],
    dept_id: null,
  },
  doCreate: api.createUser,
  doUpdate: api.updateUser,
  doDelete: api.deleteUser,
  refresh: () => $table.value?.handleSearch(),
})

// 选项数据
const roleOptions = ref([])
const deptOptions = ref([])
const tenantOptions = ref([])

// 加载角色列表（根据租户ID）
const loadRoles = async (tenantId = null) => {
  const params = { page: 1, page_size: 9999 }
  if (tenantId) {
    params.tenant_id = tenantId
  }
  const res = await api.getRoleList(params)
  roleOptions.value = res.data || []
}

// 加载部门列表（根据租户ID）
const loadDepts = async (tenantId = null) => {
  const params = {}
  if (tenantId) {
    params.tenant_id = tenantId
  }
  const res = await api.getDepts(params)
  deptOptions.value = res.data || []
}

// 加载租户列表（仅超级管理员）
const loadTenants = async () => {
  if (!isSuperUser.value) return
  const res = await api.getTenantSelect()
  tenantOptions.value = (res.data || []).map(item => ({
    label: item.name,
    value: item.id
  }))
}

// 初始化数据
onMounted(() => {
  $table.value?.handleSearch()
  loadTenants()
  // 普通用户直接加载当前租户的数据
  if (!isSuperUser.value && currentTenantId.value) {
    loadRoles(currentTenantId.value)
    loadDepts(currentTenantId.value)
  }
})

// 监听租户选择变化（超级管理员）- 用于新增/编辑时选择操作租户
watch(() => modalForm.value.tenant_id, async (newTenantId) => {
  if (!isSuperUser.value) return

  // 清空已选择的角色和部门
  modalForm.value.role_ids = []
  modalForm.value.dept_id = null

  // 如果选择了租户，加载该租户的角色和部门
  if (newTenantId) {
    await loadRoles(newTenantId)
    await loadDepts(newTenantId)
  } else {
    // 未选时清空选项
    roleOptions.value = []
    deptOptions.value = []
  }
}, { immediate: false })

const columns = computed(() => [
  {
    title: '名称',
    key: 'username',
    width: 60,
    align: 'center',
    ellipsis: { tooltip: true },
  },
  {
    title: '邮箱',
    key: 'email',
    width: 60,
    align: 'center',
    ellipsis: { tooltip: true },
  },
  {
    title: '用户角色',
    key: 'role',
    width: 60,
    align: 'center',
    render(row) {
      const roles = row.roles ?? []
      const group = []
      for (let i = 0; i < roles.length; i++)
        group.push(
          h(NTag, { type: 'info', style: { margin: '2px 3px' } }, { default: () => roles[i].name })
        )
      return h('span', group)
    },
  },
  // 多租户：仅超级管理员可见租户列
  ...(isSuperUser.value ? [{
    title: '所属租户',
    key: 'tenants',
    width: 80,
    align: 'center',
    render(row) {
      const tenants = row.tenants ?? []
      const group = []
      for (let i = 0; i < tenants.length; i++)
        group.push(
          h(NTag, { type: 'warning', style: { margin: '2px 3px' } }, { default: () => tenants[i].name })
        )
      return h('span', group)
    },
  }] : []),
  {
    title: '部门',
    key: 'dept.name',
    align: 'center',
    width: 40,
    ellipsis: { tooltip: true },
  },
  {
    title: '超级用户',
    key: 'is_superuser',
    align: 'center',
    width: 40,
    render(row) {
      return h(
        NTag,
        { type: 'info', style: { margin: '2px 3px' } },
        { default: () => (row.is_superuser ? '是' : '否') }
      )
    },
  },
  {
    title: '上次登录时间',
    key: 'last_login',
    align: 'center',
    width: 80,
    ellipsis: { tooltip: true },
    render(row) {
      return h(
        NButton,
        { size: 'small', type: 'text', ghost: true },
        {
          default: () => (row.last_login !== null ? formatDate(row.last_login) : null),
          icon: renderIcon('mdi:update', { size: 16 }),
        }
      )
    },
  },
  {
    title: '禁用',
    key: 'is_active',
    width: 50,
    align: 'center',
    render(row) {
      return h(NSwitch, {
        size: 'small',
        rubberBand: false,
        value: row.is_active,
        loading: !!row.publishing,
        checkedValue: false,
        uncheckedValue: true,
        onUpdateValue: () => handleUpdateDisable(row),
      })
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    align: 'center',
    fixed: 'right',
    render(row) {
      return [
        withDirectives(
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              style: 'margin-right: 8px;',
              onClick: () => handleEditUser(row),
            },
            {
              default: () => '编辑',
              icon: renderIcon('material-symbols:edit', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/user/update']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ user_id: row.id }, false),
            onNegativeClick: () => { },
          },
          {
            trigger: () =>
              withDirectives(
                h(
                  NButton,
                  {
                    size: 'small',
                    type: 'error',
                    style: 'margin-right: 8px;',
                  },
                  {
                    default: () => '删除',
                    icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
                  }
                ),
                [[vPermission, 'delete/api/v1/user/delete']]
              ),
            default: () => h('div', {}, '确定删除该用户吗?'),
          }
        ),
        !row.is_superuser && h(
          NPopconfirm,
          {
            onPositiveClick: async () => {
              try {
                await api.resetPassword({ user_id: row.id });
                $message.success('密码已成功重置为123456');
                await $table.value?.handleSearch();
              } catch (error) {
                $message.error('重置密码失败: ' + error.message);
              }
            },
            onNegativeClick: () => { },
          },
          {
            trigger: () =>
              withDirectives(
                h(
                  NButton,
                  {
                    size: 'small',
                    type: 'warning',
                    style: 'margin-right: 8px;',
                  },
                  {
                    default: () => '重置密码',
                    icon: renderIcon('material-symbols:lock-reset', { size: 16 }),
                  }
                ),
                [[vPermission, 'post/api/v1/user/reset_password']]
              ),
            default: () => h('div', {}, '确定重置用户密码为123456吗?'),
          }
        ),
        // 快捷登录按钮
        !row.is_superuser && h(
          NPopconfirm,
          {
            onPositiveClick: async () => {
              try {
                await handleQuickLogin(row);
              } catch (error) {
                $message.error('快捷登录失败: ' + error.message);
              }
            },
            onNegativeClick: () => { },
          },
          {
            trigger: () =>
              withDirectives(
                h(
                  NButton,
                  {
                    size: 'small',
                    type: 'info',
                    style: 'margin-right: 8px;',
                  },
                  {
                    default: () => '快捷登录',
                    icon: renderIcon('material-symbols:login', { size: 16 }),
                  }
                ),
                [[vPermission, 'post/api/v1/base/quick_login']]
              ),
            default: () => h('div', {}, `确定快捷登录到用户 "${row.username}" 吗?`),
          }
        ),
      ]
    },
  },
])

// 处理编辑用户
async function handleEditUser(row) {
  handleEdit(row)

  // 设置表单值
  modalForm.value.dept_id = row.dept?.id || null
  modalForm.value.role_ids = row.roles?.map((e) => e.id) || []

  // 超级管理员设置租户
  if (isSuperUser.value) {
    // 存储已分配租户列表（用于展示）
    modalForm.value.assigned_tenant_ids = row.tenants?.map((t) => t.id) || []
    // 清空当前选择的操作租户
    modalForm.value.tenant_id = null
    // 编辑时默认加载第一个租户的角色和部门（如果有）
    if (row.tenants?.length > 0) {
      const tenantId = row.tenants[0].id
      modalForm.value.tenant_id = tenantId
      await loadRoles(tenantId)
      await loadDepts(tenantId)
    }
  } else {
    // 普通用户加载当前租户数据
    await loadRoles(currentTenantId.value)
    await loadDepts(currentTenantId.value)
  }

  delete modalForm.value.dept
}

// 处理新增用户
function handleAddUser() {
  handleAdd()
  // 清空选项
  roleOptions.value = []
  deptOptions.value = []

  // 普通用户自动加载当前租户的角色和部门
  if (!isSuperUser.value) {
    loadRoles(currentTenantId.value)
    loadDepts(currentTenantId.value)
  }
}

// 修改用户禁用状态
async function handleUpdateDisable(row) {
  if (!row.id) return
  const userStore = useUserStore()
  if (userStore.userId === row.id) {
    $message.error('当前登录用户不可禁用！')
    return
  }
  row.publishing = true
  row.is_active = row.is_active === false ? true : false
  row.publishing = false
  const role_ids = []
  row.roles.forEach((e) => {
    role_ids.push(e.id)
  })
  row.role_ids = role_ids
  row.dept_id = row.dept?.id
  try {
    await api.updateUser(row)
    $message?.success(row.is_active ? '已取消禁用该用户' : '已禁用该用户')
    $table.value?.handleSearch()
  } catch (err) {
    // 有异常恢复原来的状态
    row.is_active = row.is_active === false ? true : false
  } finally {
    row.publishing = false
  }
}

// 快捷登录处理函数
async function handleQuickLogin(row) {
  const userStore = useUserStore()

  // 不能快捷登录到自己
  if (userStore.userId === row.id) {
    $message.error('不能快捷登录到当前用户！')
    return
  }

  let loadingMessage = null
  try {
    loadingMessage = $message.loading('正在快捷登录...', { duration: 0 })
    const res = await api.quickLogin({ target_user_id: row.id })
    if (loadingMessage) {
      loadingMessage.destroy()
    }

    if (res.code === 200) {
      const { access_token, tenants, need_select_tenant, current_tenant_id } = res.data

      // 保存原始用户的token（用于返回）
      const originalToken = lStorage.get('access_token')
      lStorage.set('original_token', originalToken)

      // 构建待验证的登录信息
      const pendingAuth = {
        token: access_token,
        tenants,
        needSelectTenant: need_select_tenant,
        currentTenantId: current_tenant_id,
        isQuickLogin: true,
        targetUser: row.username
      }
      lStorage.set('pending_auth', JSON.stringify(pendingAuth))

      // 触发退出登录
      await userStore.logoutWithoutRedirect()

      // 跳转到登录页
      router.push('/login')
    } else {
      $message.error(res.msg || '快捷登录失败')
    }
  } catch (error) {
    if (loadingMessage) {
      loadingMessage.destroy()
    }
    $message.error('快捷登录失败: ' + error.message)
  }
}

let lastClickedNodeId = null

const nodeProps = ({ option }) => {
  return {
    onClick() {
      if (lastClickedNodeId === option.id) {
        $table.value?.handleSearch()
        lastClickedNodeId = null
      } else {
        // 使用递归查询该部门及其所有子部门下的用户
        api.getUserList({ dept_id: option.id, dept_recursive: true }).then((res) => {
          $table.value.tableData = res.data
          lastClickedNodeId = option.id
        })
      }
    },
  }
}

const validateAddUser = {
  username: [
    {
      required: true,
      message: '请输入名称',
      trigger: ['input', 'blur'],
    },
  ],
  email: [
    {
      required: true,
      message: '请输入邮箱地址',
      trigger: ['input', 'change'],
    },
    {
      trigger: ['blur'],
      validator: (rule, value, callback) => {
        const re = /^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$/
        if (!re.test(modalForm.value.email)) {
          callback('邮箱格式错误')
          return
        }
        callback()
      },
    },
  ],
  password: [
    {
      required: true,
      message: '请输入密码',
      trigger: ['input', 'blur', 'change'],
    },
  ],
  confirmPassword: [
    {
      required: true,
      message: '请再次输入密码',
      trigger: ['input'],
    },
    {
      trigger: ['blur'],
      validator: (rule, value, callback) => {
        if (value !== modalForm.value.password) {
          callback('两次密码输入不一致')
          return
        }
        callback()
      },
    },
  ],
  role_ids: [
    {
      type: 'array',
      required: true,
      message: '请至少选择一个角色',
      trigger: ['blur', 'change'],
    },
  ],
}
</script>

<template>
  <NLayout has-sider wh-full>
    <!-- 部门列表：仅普通用户显示，默认收起 -->
    <NLayoutSider v-if="!isSuperUser" bordered content-style="padding: 24px;" :collapsed-width="0" :width="240"
      show-trigger="arrow-circle" :default-collapsed="true">
      <h1>部门列表</h1>
      <br />
      <NTree block-line :data="deptOptions" key-field="id" label-field="name" :node-props="nodeProps">
      </NTree>
    </NLayoutSider>
    <NLayoutContent>
      <CommonPage show-footer title="用户列表">
        <template #action>
          <NButton v-permission="'post/api/v1/user/create'" type="primary" @click="handleAddUser">
            <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建用户
          </NButton>
        </template>
        <!-- 表格 -->
        <CrudTable ref="$table" v-model:query-items="queryItems" :columns="columns" :get-data="api.getUserList">
          <template #queryBar>
            <QueryBarItem label="名称">
              <NInput v-model:value="queryItems.username" clearable type="text" placeholder="请输入用户名称"
                @keypress.enter="$table?.handleSearch()" />
            </QueryBarItem>
            <QueryBarItem label="邮箱">
              <NInput v-model:value="queryItems.email" clearable type="text" placeholder="请输入邮箱"
                @keypress.enter="$table?.handleSearch()" />
            </QueryBarItem>
            <!-- 多租户：仅超级管理员可见租户筛选 -->
            <QueryBarItem v-if="isSuperUser" label="租户">
              <NSelect v-model:value="queryItems.tenant_id" :options="tenantOptions" placeholder="请选择租户" clearable
                class="min-w-120px" @update:value="$table?.handleSearch()" />
            </QueryBarItem>
          </template>
        </CrudTable>

        <!-- 新增/编辑 弹窗 -->
        <CrudModal v-model:visible="modalVisible" :title="modalTitle" :loading="modalLoading" @save="handleSave">
          <NForm ref="modalFormRef" label-placement="left" label-align="left" :label-width="80" :model="modalForm"
            :rules="validateAddUser">
            <NFormItem label="用户名称" path="username">
              <NInput v-model:value="modalForm.username" clearable placeholder="请输入用户名称" />
            </NFormItem>
            <NFormItem label="邮箱" path="email">
              <NInput v-model:value="modalForm.email" clearable placeholder="请输入邮箱" />
            </NFormItem>
            <NFormItem v-if="modalAction === 'add'" label="密码" path="password">
              <NInput v-model:value="modalForm.password" show-password-on="mousedown" type="password" clearable
                placeholder="请输入密码" />
            </NFormItem>
            <NFormItem v-if="modalAction === 'add'" label="确认密码" path="confirmPassword">
              <NInput v-model:value="modalForm.confirmPassword" show-password-on="mousedown" type="password" clearable
                placeholder="请确认密码" />
            </NFormItem>

            <!-- 超级管理员：编辑时显示已分配租户（只读） -->
            <NFormItem v-if="isSuperUser && modalAction === 'edit'" label="已分配租户">
              <NSelect :value="modalForm.assigned_tenant_ids" :options="tenantOptions" multiple disabled
                placeholder="该用户已分配的租户" class="min-w-200px" />
            </NFormItem>

            <!-- 超级管理员：选择操作租户（单选） -->
            <NFormItem v-if="isSuperUser" label="选择租户" path="tenant_id">
              <NSelect v-model:value="modalForm.tenant_id" :options="tenantOptions" placeholder="请选择要操作的租户" clearable
                class="min-w-200px" />
            </NFormItem>

            <!-- 角色选择 -->
            <NFormItem label="角色" path="role_ids">
              <NCheckboxGroup v-model:value="modalForm.role_ids">
                <NSpace item-style="display: flex;">
                  <NCheckbox v-for="item in roleOptions" :key="item.id" :value="item.id" :label="item.name" />
                </NSpace>
              </NCheckboxGroup>
            </NFormItem>

            <!-- 部门选择 -->
            <NFormItem label="部门" path="dept_id">
              <NTreeSelect v-model:value="modalForm.dept_id" :options="deptOptions" key-field="id" label-field="name"
                placeholder="请选择部门" clearable default-expand-all />
            </NFormItem>

            <!-- 仅超级管理员可见超级用户开关 -->
            <NFormItem v-if="isSuperUser" label="超级用户" path="is_superuser">
              <NSwitch v-model:value="modalForm.is_superuser" size="small" :checked-value="true"
                :unchecked-value="false">
              </NSwitch>
            </NFormItem>
            <NFormItem label="禁用" path="is_active">
              <NSwitch v-model:value="modalForm.is_active" :checked-value="false" :unchecked-value="true"
                :default-value="true" />
            </NFormItem>
          </NForm>
        </CrudModal>
      </CommonPage>
    </NLayoutContent>
  </NLayout>
  <!-- 业务页面 -->
</template>
