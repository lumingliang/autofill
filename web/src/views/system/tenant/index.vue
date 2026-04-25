<script setup>
import { h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NPopconfirm,
  NSwitch,
  NTag,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'

import { formatDate, renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
import api from '@/api'
import TheIcon from '@/components/icon/TheIcon.vue'

defineOptions({ name: '租户管理' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

const {
  modalVisible,
  modalAction,
  modalTitle,
  modalLoading,
  handleAdd,
  handleDelete,
  handleEdit,
  handleSave,
  modalForm,
  modalFormRef,
} = useCRUD({
  name: '租户',
  initForm: { is_active: true },
  doCreate: api.createTenant,
  doDelete: api.deleteTenant,
  doUpdate: api.updateTenant,
  refresh: () => $table.value?.handleSearch(),
})

onMounted(() => {
  $table.value?.handleSearch()
})

const columns = [
  {
    title: '租户名称',
    key: 'name',
    width: 100,
    align: 'center',
    ellipsis: { tooltip: true },
  },
  {
    title: '域名',
    key: 'domain',
    width: 100,
    align: 'center',
    ellipsis: { tooltip: true },
  },
  {
    title: '描述',
    key: 'description',
    width: 120,
    align: 'center',
    ellipsis: { tooltip: true },
  },
  {
    title: '状态',
    key: 'is_active',
    width: 60,
    align: 'center',
    render(row) {
      return h(
        NTag,
        { type: row.is_active ? 'success' : 'error' },
        { default: () => (row.is_active ? '启用' : '禁用') }
      )
    },
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 80,
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
          [[vPermission, 'post/api/v1/tenant/update']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ tenant_id: row.id }, false),
            onNegativeClick: () => {},
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
                [[vPermission, 'delete/api/v1/tenant/delete']]
              ),
            default: () => h('div', {}, '确定删除该租户吗?删除后该租户下的所有数据将无法访问!'),
          }
        ),
      ]
    },
  },
]

const validateTenant = {
  name: [
    {
      required: true,
      message: '请输入租户名称',
      trigger: ['input', 'blur'],
    },
  ],
  domain: [
    {
      required: true,
      message: '请输入租户域名',
      trigger: ['input', 'blur'],
    },
    {
      trigger: ['blur'],
      validator: (rule, value, callback) => {
        // 域名格式验证：只允许字母、数字、横线
        const re = /^[a-zA-Z0-9-]+$/
        if (!re.test(value)) {
          callback('域名只能包含字母、数字和横线')
          return
        }
        callback()
      },
    },
  ],
}
</script>

<template>
  <CommonPage show-footer title="租户管理">
    <template #action>
      <NButton v-permission="'post/api/v1/tenant/create'" type="primary" @click="handleAdd">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建租户
      </NButton>
    </template>

    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="api.getTenantList"
    >
      <template #queryBar>
        <QueryBarItem label="租户名称" :label-width="70">
          <NInput
            v-model:value="queryItems.name"
            clearable
            type="text"
            placeholder="请输入租户名称"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem label="域名" :label-width="40">
          <NInput
            v-model:value="queryItems.domain"
            clearable
            type="text"
            placeholder="请输入域名"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
      </template>
    </CrudTable>

    <CrudModal
      v-model:visible="modalVisible"
      :title="modalTitle"
      :loading="modalLoading"
      @save="handleSave"
    >
      <NForm
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="80"
        :model="modalForm"
        :rules="validateTenant"
        :disabled="modalAction === 'view'"
      >
        <NFormItem
          label="租户名称"
          path="name"
        >
          <NInput v-model:value="modalForm.name" placeholder="请输入租户名称" />
        </NFormItem>
        <NFormItem
          label="域名"
          path="domain"
        >
          <NInput v-model:value="modalForm.domain" placeholder="请输入租户域名，如：tenant-a" />
          <span class="text-gray-400 text-xs mt-1">域名只能包含字母、数字和横线，用于标识租户</span>
        </NFormItem>
        <NFormItem label="描述" path="description">
          <NInput
            v-model:value="modalForm.description"
            type="textarea"
            placeholder="请输入租户描述"
          />
        </NFormItem>
        <NFormItem label="启用" path="is_active">
          <NSwitch
            v-model:value="modalForm.is_active"
            :checked-value="true"
            :unchecked-value="false"
          />
        </NFormItem>
      </NForm>
    </CrudModal>
  </CommonPage>
</template>
