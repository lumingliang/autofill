<template>
  <div class="tenant-page">
    <a-card>
      <a-form layout="inline" :model="queryParams" class="search-form">
        <a-form-item label="租户名称">
          <a-input v-model:value="queryParams.name" placeholder="请输入租户名称" allow-clear @pressEnter="handleSearch" />
        </a-form-item>
        <a-form-item label="域名">
          <a-input v-model:value="queryParams.domain" placeholder="请输入域名" allow-clear @pressEnter="handleSearch" />
        </a-form-item>
        <a-form-item>
          <a-space>
            <a-button type="primary" @click="handleSearch">查询</a-button>
            <a-button @click="handleReset">重置</a-button>
          </a-space>
        </a-form-item>
      </a-form>

      <div class="table-actions">
        <a-button v-permission="'post/api/v1/tenant/create'" type="primary" @click="handleAdd">
          <PlusOutlined />
          新建租户
        </a-button>
      </div>

      <a-table
        :columns="columns"
        :data-source="tableData"
        :loading="loading"
        :pagination="pagination"
        row-key="id"
        @change="handleTableChange"
      >
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
              <a-button v-permission="'post/api/v1/tenant/update'" type="link" size="small" @click="handleEdit(record)">编辑</a-button>
              <a-popconfirm title="确定删除该租户吗？删除后该租户下的所有数据将无法访问！" @confirm="handleDelete(record)">
                <a-button v-permission="'delete/api/v1/tenant/delete'" type="link" danger size="small">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 新增/编辑 弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="modalTitle"
      :confirm-loading="modalLoading"
      @ok="handleSave"
      @cancel="modalVisible = false"
    >
      <a-form
        ref="modalFormRef"
        :model="modalForm"
        :rules="modalRules"
        :label-col="{ span: 6 }"
        :wrapper-col="{ span: 16 }"
      >
        <a-form-item label="租户名称" name="name">
          <a-input v-model:value="modalForm.name" placeholder="请输入租户名称" />
        </a-form-item>
        <a-form-item label="域名" name="domain">
          <a-input v-model:value="modalForm.domain" placeholder="请输入租户域名，如：tenant-a" />
          <span style="color: #999; font-size: 12px">域名只能包含字母、数字和横线，用于标识租户</span>
        </a-form-item>
        <a-form-item label="描述" name="description">
          <a-textarea v-model:value="modalForm.description" placeholder="请输入租户描述" :rows="3" />
        </a-form-item>
        <a-form-item label="启用" name="is_active">
          <a-switch v-model:checked="modalForm.is_active" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import api from '@/api'
import { formatDateTime } from '@/utils'

const queryParams = reactive<any>({
  name: '',
  domain: '',
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

const columns = [
  { title: '租户名称', dataIndex: 'name', key: 'name', ellipsis: true },
  { title: '域名', dataIndex: 'domain', key: 'domain', ellipsis: true },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '状态', key: 'is_active', width: 80 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
  { title: '操作', key: 'action', width: 150 },
]

const modalVisible = ref(false)
const modalLoading = ref(false)
const modalAction = ref<'add' | 'edit'>('add')
const modalTitle = computed(() => (modalAction.value === 'add' ? '新增租户' : '编辑租户'))
const modalFormRef = ref()
const modalForm = reactive<any>({
  name: '',
  domain: '',
  description: '',
  is_active: true,
})

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
  modalAction.value = 'add'
  Object.assign(modalForm, {
    name: '',
    domain: '',
    description: '',
    is_active: true,
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
    const apiFn = modalAction.value === 'add' ? api.createTenant : api.updateTenant
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
    const res: any = await api.deleteTenant({ tenant_id: record.id })
    if (res.code === 200) {
      window.$message?.success('删除成功')
      loadData()
    }
  } catch (error) {
    console.error('删除失败', error)
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="less">
.tenant-page {
  .search-form {
    margin-bottom: 16px;
  }

  .table-actions {
    margin-bottom: 16px;
  }
}
</style>
