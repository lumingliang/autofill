<script setup>
import { computed, h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
import { NButton, NForm, NFormItem, NInput, NInputNumber, NPopconfirm, NTreeSelect, NSelect } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
import api from '@/api'
import { useUserStore } from '@/store'

defineOptions({ name: '部门管理' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')
const userStore = useUserStore()

const isSuperUser = computed(() => userStore.isSuperUser)

const {
  modalVisible,
  modalTitle,
  modalLoading,
  handleSave: originalHandleSave,
  modalForm,
  modalFormRef,
  handleEdit,
  handleDelete,
  handleAdd,
} = useCRUD({
  name: '部门',
  initForm: { order: 0 },
  doCreate: api.createDept,
  doUpdate: api.updateDept,
  doDelete: api.deleteDept,
  refresh: () => $table.value?.handleSearch(),
})

// 自定义保存处理，保存成功后刷新部门列表
const handleSave = async () => {
  await originalHandleSave()
  // 刷新部门下拉列表
  await loadDepts()
}

const deptOptions = ref([])
const tenantOptions = ref([])
const isDisabled = ref(false)

// 加载部门列表
const loadDepts = async () => {
  const params = {}
  if (queryItems.value.tenant_id) {
    params.tenant_id = queryItems.value.tenant_id
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

onMounted(() => {
  $table.value?.handleSearch()
  loadDepts()
  loadTenants()
})

const deptRules = {
  name: [
    {
      required: true,
      message: '请输入部门名称',
      trigger: ['input', 'blur', 'change'],
    },
  ],
}

async function addDept() {
  isDisabled.value = false
  handleAdd()
  // 超级管理员新增时，默认不选租户
  if (isSuperUser.value) {
    modalForm.value.tenant_id = null
  }
}

// 处理编辑部门
async function handleEditDept(row) {
  if (row.parent_id === 0) {
    isDisabled.value = true
  } else {
    isDisabled.value = false
  }
  handleEdit(row)
}

const columns = [
  {
    title: '部门名称',
    key: 'name',
    width: 'auto',
    align: 'center',
    ellipsis: { tooltip: true },
  },
  // 多租户：仅超级管理员可见租户列
  ...(isSuperUser.value ? [{
    title: '所属租户',
    key: 'tenant_name',
    width: 'auto',
    align: 'center',
    ellipsis: { tooltip: true },
  }] : []),
  {
    title: '备注',
    key: 'desc',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: '操作',
    key: 'actions',
    width: 'auto',
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
              style: 'margin-left: 8px;',
              onClick: () => handleEditDept(row),
            },
            {
              default: () => '编辑',
              icon: renderIcon('material-symbols:edit', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/dept/update']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ dept_id: row.id }, false),
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
                    style: 'margin-left: 8px;',
                  },
                  {
                    default: () => '删除',
                    icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
                  }
                ),
                [[vPermission, 'delete/api/v1/dept/delete']]
              ),
            default: () => h('div', {}, '确定删除该部门吗?'),
          }
        ),
      ]
    },
  },
]
</script>

<template>
  <!-- 业务页面 -->
  <CommonPage show-footer title="部门列表">
    <template #action>
      <div>
        <NButton v-permission="'post/api/v1/dept/create'" class="float-right mr-15" type="primary" @click="addDept">
          <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建部门
        </NButton>
      </div>
    </template>
    <!-- 表格 -->
    <CrudTable ref="$table" v-model:query-items="queryItems" :columns="columns" :get-data="api.getDepts">
      <template #queryBar>
        <QueryBarItem label="部门名称">
          <NInput v-model:value="queryItems.name" clearable type="text" placeholder="请输入部门名称"
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
        :rules="deptRules">
        <!-- 超级管理员：选择所属租户 -->
        <NFormItem v-if="isSuperUser" label="所属租户" path="tenant_id">
          <NSelect v-model:value="modalForm.tenant_id" :options="tenantOptions" placeholder="请选择租户" clearable
            class="min-w-120px" />
        </NFormItem>
        <NFormItem label="父级部门" path="parent_id">
          <NTreeSelect v-model:value="modalForm.parent_id" :options="deptOptions" key-field="id" label-field="name"
            placeholder="请选择父级部门" clearable default-expand-all :disabled="isDisabled"></NTreeSelect>
        </NFormItem>
        <NFormItem label="部门名称" path="name">
          <NInput v-model:value="modalForm.name" clearable placeholder="请输入部门名称" />
        </NFormItem>
        <NFormItem label="备注" path="desc">
          <NInput v-model:value="modalForm.desc" type="textarea" clearable />
        </NFormItem>
        <NFormItem label="排序" path="order">
          <NInputNumber v-model:value="modalForm.order" min="0"></NInputNumber>
        </NFormItem>
      </NForm>
    </CrudModal>
  </CommonPage>
</template>
