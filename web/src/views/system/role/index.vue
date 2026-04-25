<script setup>
import { computed, h, nextTick, onMounted, ref, resolveDirective, withDirectives, watch } from 'vue'
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NPopconfirm,
  NTag,
  NTree,
  NDrawer,
  NDrawerContent,
  NTabs,
  NTabPane,
  NGrid,
  NGi,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TenantSelect from '@/components/tenant/TenantSelect.vue'

import { formatDate, renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
import api from '@/api'
import TheIcon from '@/components/icon/TheIcon.vue'
import { useUserStore } from '@/store'

const userStore = useUserStore()
const isSuperUser = computed(() => userStore.isSuperUser)

defineOptions({ name: '角色管理' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

const {
  modalVisible,
  modalAction,
  modalTitle,
  modalLoading,
  handleAdd: originalHandleAdd,
  handleDelete,
  handleEdit: originalHandleEdit,
  handleSave,
  modalForm,
  modalFormRef,
} = useCRUD({
  name: '角色',
  initForm: {},
  doCreate: api.createRole,
  doDelete: api.deleteRole,
  doUpdate: api.updateRole,
  refresh: () => $table.value?.handleSearch(),
})

// 自定义 handleAdd，打开弹窗后清除校验
function handleAdd() {
  originalHandleAdd()
  nextTick(() => {
    modalFormRef.value?.restoreValidation()
  })
}

// 自定义 handleEdit，打开弹窗后清除校验
function handleEdit(row) {
  originalHandleEdit(row)
  nextTick(() => {
    modalFormRef.value?.restoreValidation()
  })
}

// 表单校验规则
const validateRole = {
  tenant_id: {
    required: true,
    message: '请选择所属租户',
    trigger: ['change', 'blur'],
    type: 'number',
  },
  name: {
    required: true,
    message: '请输入角色名称',
    trigger: ['input', 'blur'],
  },
}

const pattern = ref('')
const menuOption = ref([]) // 菜单选项

const active = ref(false)
const menu_ids = ref([])
const role_id = ref(0)
const apiOption = ref([])
const api_ids = ref([])
const apiTree = ref([])

function buildApiTree(data) {
  const processedData = []
  const groupedData = {}

  data.forEach((item) => {
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
  processedData.push(...Object.values(groupedData))
  return processedData
}

onMounted(() => {
  $table.value?.handleSearch()
})

const columns = computed(() => [
  {
    title: '角色名',
    key: 'name',
    width: 80,
    align: 'center',
    ellipsis: { tooltip: true },
    render(row) {
      return h(NTag, { type: 'info' }, { default: () => row.name })
    },
  },
  // 多租户：仅超级管理员可见租户列
  ...(isSuperUser.value ? [{
    title: '所属租户',
    key: 'tenant_name',
    width: 80,
    align: 'center',
    render(row) {
      return h(NTag, { type: 'warning' }, { default: () => row.tenant_name || '系统角色' })
    },
  }] : []),
  {
    title: '角色描述',
    key: 'desc',
    width: 80,
    align: 'center',
  },
  {
    title: '创建日期',
    key: 'created_at',
    width: 60,
    align: 'center',
    render(row) {
      return h('span', formatDate(row.created_at))
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
              onClick: () => {
                handleEdit(row)
              },
            },
            {
              default: () => '编辑',
              icon: renderIcon('material-symbols:edit-outline', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/role/update']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ role_id: row.id }, false),
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
                [[vPermission, 'delete/api/v1/role/delete']]
              ),
            default: () => h('div', {}, '确定删除该角色吗?'),
          }
        ),
        withDirectives(
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              onClick: async () => {
                try {
                  // 使用 Promise.all 来同时发送所有请求
                  const [menusResponse, apisResponse, roleAuthorizedResponse] = await Promise.all([
                    api.getMenus({ page: 1, page_size: 9999 }),
                    api.getApis({ page: 1, page_size: 9999 }),
                    api.getRoleAuthorized({ id: row.id }),
                  ])

                  // 处理每个请求的响应
                  menuOption.value = menusResponse.data
                  apiOption.value = buildApiTree(apisResponse.data)
                  menu_ids.value = roleAuthorizedResponse.data.menus.map((v) => v.id)
                  api_ids.value = roleAuthorizedResponse.data.apis.map(
                    (v) => v.method.toLowerCase() + v.path
                  )

                  active.value = true
                  role_id.value = row.id
                } catch (error) {
                  // 错误处理
                  console.error('Error loading data:', error)
                }
              },
            },
            {
              default: () => '设置权限',
              icon: renderIcon('material-symbols:edit-outline', { size: 16 }),
            }
          ),
          [[vPermission, 'get/api/v1/role/authorized']]
        ),
      ]
    },
  },
])

async function updateRoleAuthorized() {
  const checkData = apiTree.value.getCheckedData()
  const apiInfos = []
  checkData &&
    checkData.options.forEach((item) => {
      if (!item.children) {
        apiInfos.push({
          path: item.path,
          method: item.method,
        })
      }
    })
  const { code, msg } = await api.updateRoleAuthorized({
    id: role_id.value,
    menu_ids: menu_ids.value,
    api_infos: apiInfos,
  })
  if (code === 200) {
    $message?.success('设置成功')
  } else {
    $message?.error(msg)
  }

  const result = await api.getRoleAuthorized({ id: role_id.value })
  menu_ids.value = result.data.menus.map((v) => {
    return v.id
  })
}
</script>

<template>
  <CommonPage show-footer title="角色列表">
    <template #action>
      <NButton v-permission="'post/api/v1/role/create'" type="primary" @click="handleAdd">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建角色
      </NButton>
    </template>

    <CrudTable ref="$table" v-model:query-items="queryItems" :columns="columns" :get-data="api.getRoleList">
      <template #queryBar>
        <QueryBarItem label="角色名" :label-width="50">
          <NInput v-model:value="queryItems.role_name" clearable type="text" placeholder="请输入角色名"
            @keypress.enter="$table?.handleSearch()" />
        </QueryBarItem>
        <!-- 多租户：仅超级管理员可见租户筛选 -->
        <QueryBarItem v-if="isSuperUser" label="租户" :label-width="40">
          <TenantSelect v-model="queryItems.tenant_id" @change="$table?.handleSearch()" />
        </QueryBarItem>
      </template>
    </CrudTable>

    <CrudModal v-model:visible="modalVisible" :title="modalTitle" :loading="modalLoading" @save="handleSave">
      <NForm ref="modalFormRef" label-placement="left" label-align="left" :label-width="80" :model="modalForm"
        :rules="validateRole" :disabled="modalAction === 'view'">
        <!-- 多租户：仅超级管理员可见租户选择 -->
        <NFormItem v-if="isSuperUser" label="所属租户" path="tenant_id">
          <TenantSelect v-model="modalForm.tenant_id" />
        </NFormItem>
        <NFormItem label="角色名" path="name">
          <NInput v-model:value="modalForm.name" placeholder="请输入角色名称" />
        </NFormItem>

        <NFormItem label="角色描述" path="desc">
          <NInput v-model:value="modalForm.desc" placeholder="请输入角色描述" />
        </NFormItem>
      </NForm>
    </CrudModal>

    <NDrawer v-model:show="active" placement="right" :width="500">
      <NDrawerContent>
        <NGrid x-gap="24" cols="12">
          <NGi span="8">
            <NInput v-model:value="pattern" type="text" placeholder="筛选" style="flex-grow: 1"></NInput>
          </NGi>
          <NGi offset="2">
            <NButton v-permission="'post/api/v1/role/authorized'" type="info" @click="updateRoleAuthorized">确定</NButton>
          </NGi>
        </NGrid>
        <NTabs>
          <NTabPane name="menu" tab="菜单权限" display-directive="show">
            <!-- TODO：级联 -->
            <NTree :data="menuOption" :checked-keys="menu_ids" :pattern="pattern" :show-irrelevant-nodes="false"
              key-field="id" label-field="name" checkable :default-expand-all="true" :block-line="true"
              :selectable="false" @update:checked-keys="(v) => (menu_ids = v)" />
          </NTabPane>
          <NTabPane name="resource" tab="接口权限" display-directive="show">
            <NTree ref="apiTree" :data="apiOption" :checked-keys="api_ids" :pattern="pattern"
              :show-irrelevant-nodes="false" key-field="unique_id" label-field="summary" checkable
              :default-expand-all="true" :block-line="true" :selectable="false" cascade
              @update:checked-keys="(v) => (api_ids = v)" />
          </NTabPane>
        </NTabs>
        <template #header> 设置权限 </template>
      </NDrawerContent>
    </NDrawer>
  </CommonPage>
</template>