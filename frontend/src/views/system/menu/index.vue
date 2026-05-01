<template>
  <div class="menu-page crud-page">
    <a-card>
      <div class="table-actions">
        <a-button v-permission="'post/api/v1/menu/create'" type="primary" @click="handleClickAdd">
          <PlusOutlined />
          新建根菜单
        </a-button>
      </div>

      <a-table
        class="crud-table"
        :columns="columns"
        :data-source="tableData"
        :loading="loading"
        :pagination="false"
        row-key="id"
        :scroll="{ x: 'max-content' }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'menu_type'">
            <a-tag :color="record.menu_type === 'catalog' ? 'blue' : 'green'">
              {{ record.menu_type === 'catalog' ? '目录' : '菜单' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'icon'">
            <component :is="getIcon(record.icon)" v-if="record.icon" />
          </template>
          <template v-if="column.key === 'keepalive'">
            <a-switch
              :checked="record.keepalive"
              size="small"
              :loading="!!record.publishingKeepalive"
              @change="() => handleUpdateKeepalive(record)"
            />
          </template>
          <template v-if="column.key === 'is_hidden'">
            <a-switch
              :checked="record.is_hidden"
              size="small"
              :loading="!!record.publishingHidden"
              @change="() => handleUpdateHidden(record)"
            />
          </template>
          <template v-if="column.key === 'created_at'">
            {{ formatDateTime(record.created_at) }}
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button
                v-permission="'post/api/v1/menu/create'"
                type="link"
                size="small"
                :style="{ display: record.children && record.menu_type !== 'menu' ? '' : 'none' }"
                @click="handleAddChild(record)"
              >
                子菜单
              </a-button>
              <a-button v-permission="'post/api/v1/menu/update'" type="link" size="small" @click="handleEdit(record)">编辑</a-button>
              <a-popconfirm title="确定删除该菜单吗？" @confirm="handleDelete(record)">
                <a-button
                  v-permission="'delete/api/v1/menu/delete'"
                  type="link"
                  danger
                  size="small"
                  :style="{ display: record.children && record.children.length > 0 ? 'none' : '' }"
                >
                  删除
                </a-button>
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
        <a-form-item label="菜单类型" name="menu_type">
          <a-radio-group v-model:value="modalForm.menu_type">
            <a-radio value="catalog">目录</a-radio>
            <a-radio value="menu">菜单</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="上级菜单" name="parent_id">
          <a-tree-select
            v-model:value="modalForm.parent_id"
            :tree-data="menuOptions"
            :field-names="{ label: 'name', value: 'id', children: 'children' }"
            placeholder="请选择上级菜单"
            tree-default-expand-all
          />
        </a-form-item>
        <a-form-item label="菜单名称" name="name">
          <a-input v-model:value="modalForm.name" placeholder="请输入唯一菜单名称" />
        </a-form-item>
        <a-form-item label="访问路径" name="path">
          <a-input v-model:value="modalForm.path" placeholder="请输入访问路径" />
        </a-form-item>
        <a-form-item v-if="modalForm.menu_type === 'menu'" label="组件路径" name="component">
          <a-input v-model:value="modalForm.component" placeholder="请输入组件路径，例如：/system/user" />
        </a-form-item>
        <a-form-item label="跳转路径" name="redirect">
          <a-input
            v-model:value="modalForm.redirect"
            :disabled="modalForm.parent_id !== 0"
            :placeholder="modalForm.parent_id !== 0 ? '只有一级菜单可以设置跳转路径' : '请输入跳转路径'"
          />
        </a-form-item>
        <a-form-item label="菜单图标" name="icon">
          <IconSelector v-model:value="modalForm.icon" />
        </a-form-item>
        <a-form-item label="显示排序" name="order">
          <a-input-number v-model:value="modalForm.order" :min="1" style="width: 100%" />
        </a-form-item>
        <a-form-item label="是否隐藏" name="is_hidden">
          <a-switch v-model:checked="modalForm.is_hidden" />
        </a-form-item>
        <a-form-item label="KeepAlive" name="keepalive">
          <a-switch v-model:checked="modalForm.keepalive" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { PlusOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import api from '@/api'
import { formatDateTime } from '@/utils'
import * as Icons from '@ant-design/icons-vue'
import IconSelector from '@/components/IconSelector/index.vue'

defineOptions({ name: '菜单管理' })

const loading = ref(false)
const tableData = ref<any[]>([])
const menuOptions = ref<any[]>([])

const columns = [
  { title: '菜单名称', dataIndex: 'name', key: 'name', width: 150, ellipsis: true, resizable: true },
  { title: '菜单类型', key: 'menu_type', width: 80, resizable: true },
  { title: '图标', key: 'icon', width: 60, resizable: true },
  { title: '排序', dataIndex: 'order', key: 'order', width: 60, resizable: true },
  { title: '访问路径', dataIndex: 'path', key: 'path', width: 150, ellipsis: true, resizable: true },
  { title: '跳转路径', dataIndex: 'redirect', key: 'redirect', width: 150, ellipsis: true, resizable: true },
  { title: '组件路径', dataIndex: 'component', key: 'component', width: 200, ellipsis: true, resizable: true },
  { title: '保活', key: 'keepalive', width: 70, resizable: true },
  { title: '隐藏', key: 'is_hidden', width: 70, resizable: true },
  { title: '创建日期', dataIndex: 'created_at', key: 'created_at', width: 180, ellipsis: true, resizable: true },
  { title: '操作', key: 'action', width: 200, fixed: 'right' },
]

const modalVisible = ref(false)
const modalLoading = ref(false)
const modalAction = ref<'add' | 'edit'>('add')
const modalTitle = computed(() => (modalAction.value === 'add' ? '新增菜单' : '编辑菜单'))
const modalFormRef = ref()
const modalForm = reactive<any>({
  menu_type: 'catalog',
  parent_id: 0,
  name: '',
  path: '',
  component: '',
  redirect: '',
  icon: '',
  order: 1,
  is_hidden: false,
  keepalive: true,
})

const modalRules = {
  name: [{ required: true, message: '请输入唯一菜单名称', trigger: ['input', 'blur'] }],
  path: [{ required: true, message: '请输入访问路径', trigger: ['blur'] }],
}

function getIcon(iconName: string) {
  return (Icons as any)[iconName] || null
}

async function loadData() {
  loading.value = true
  try {
    const res: any = await api.getMenus({})
    tableData.value = res.data || []
  } finally {
    loading.value = false
  }
}

async function getTreeSelect() {
  const res: any = await api.getMenus({})
  const menu = { id: 0, name: '根目录', children: [] }
  menu.children = res.data || []
  menuOptions.value = [menu]
}

function handleClickAdd() {
  modalAction.value = 'add'
  Object.assign(modalForm, {
    menu_type: 'catalog',
    parent_id: 0,
    name: '',
    path: '',
    component: '',
    redirect: '',
    icon: '',
    order: 1,
    is_hidden: false,
    keepalive: true,
  })
  modalVisible.value = true
}

function handleAddChild(record: any) {
  modalAction.value = 'add'
  Object.assign(modalForm, {
    menu_type: 'menu',
    parent_id: record.id,
    name: '',
    path: '',
    component: '',
    redirect: '',
    icon: '',
    order: 1,
    is_hidden: false,
    keepalive: true,
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
    const apiFn = modalAction.value === 'add' ? api.createMenu : api.updateMenu
    const res: any = await apiFn({ ...modalForm })
    if (res.code === 200) {
      window.$message?.success(modalAction.value === 'add' ? '新增成功' : '编辑成功')
      modalVisible.value = false
      loadData()
      getTreeSelect()
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
    const res: any = await api.deleteMenu({ id: record.id })
    if (res.code === 200) {
      window.$message?.success('删除成功')
      loadData()
      getTreeSelect()
    }
  } catch (error) {
    console.error('删除失败', error)
  }
}

async function handleUpdateKeepalive(row: any) {
  if (!row.id) return
  row.publishingKeepalive = true
  const newVal = !row.keepalive
  try {
    await api.updateMenu({ ...row, keepalive: newVal })
    row.keepalive = newVal
    window.$message?.success(newVal ? '已开启' : '已关闭')
  } catch (err) {
    console.error(err)
  } finally {
    row.publishingKeepalive = false
  }
}

async function handleUpdateHidden(row: any) {
  if (!row.id) return
  row.publishingHidden = true
  const newVal = !row.is_hidden
  try {
    await api.updateMenu({ ...row, is_hidden: newVal })
    row.is_hidden = newVal
    window.$message?.success(newVal ? '已隐藏' : '已取消隐藏')
  } catch (err) {
    console.error(err)
  } finally {
    row.publishingHidden = false
  }
}

onMounted(() => {
  loadData()
  getTreeSelect()
})
</script>

<style scoped lang="less">
.menu-page {
  .table-actions {
    margin-bottom: 16px;
  }

  :deep(.ant-table) {
    .ant-table-row {
      &:hover {
        background-color: #f5f5f5;
      }
    }

    // 树形结构展开按钮样式优化
    .ant-table-cell-with-append {
      .ant-table-row-expand-icon {
        width: 16px;
        height: 16px;
        line-height: 14px;
        border: 1px solid #d9d9d9;
        border-radius: 2px;
        background: #fff;
        color: #666;
        transition: all 0.3s;

        &:hover {
          border-color: #1890ff;
          color: #1890ff;
        }
      }
    }

    // 层级缩进样式优化
    .ant-table-cell {
      .ant-table-row-indent {
        padding-left: 8px;
      }
    }

    // 操作列按钮间距
    .ant-space {
      gap: 8px !important;
    }
  }
}
</style>
