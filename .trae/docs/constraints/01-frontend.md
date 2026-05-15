# 前端技术约束

> 本文档包含 Vue 3 + TypeScript 前端开发的所有约束规则。

---

## 1. 框架约束

### 1.1 Vue 3 组合式 API 规范

```typescript
// ✅ 正确：使用 <script setup> 语法
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

// 组件名定义
defineOptions({ name: '组件名称' })

// Props 定义
const props = withDefaults(defineProps<{
  title: string
  visible?: boolean
}>(), {
  visible: false
})

// Emits 定义
const emit = defineEmits<{
  update: [value: string]
  submit: []
}>()

// 响应式数据
const loading = ref(false)
const formData = reactive<FormType>({ name: '' })

// 计算属性
const displayTitle = computed(() => props.title || '默认标题')

// 生命周期
onMounted(() => {
  initData()
})

// 方法
async function initData() {
  // 实现
}
</script>
```

#### 禁止使用

```typescript
// ❌ 错误：Options API
export default {
  data() { return {} },
  methods: {}
}

// ❌ 错误：不使用 TypeScript
<script setup>

// ❌ 错误：不使用类型定义
const data = ref({})
```

---

## 2. 状态管理约束

### 2.1 Pinia Store 规范

```typescript
// ✅ 正确：使用 Setup Store 语法
// store/modules/{module}.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  // State
  const userInfo = ref<Record<string, any>>({})
  
  // Getters
  const isSuperUser = computed(() => userInfo.value?.is_superuser)
  
  // Actions
  async function getUserInfo() {
    // 实现
  }
  
  return {
    userInfo,
    isSuperUser,
    getUserInfo
  }
})
```

### 2.2 Store 使用规范

```typescript
// ✅ 正确：在组件中使用
<script setup lang="ts">
import { useUserStore, usePermissionStore } from '@/store'

const userStore = useUserStore()
const permissionStore = usePermissionStore()

// 访问 state
console.log(userStore.userInfo)

// 访问 getter
console.log(userStore.isSuperUser)

// 调用 action
await userStore.getUserInfo()
</script>
```

---

## 3. 组件约束

### 3.1 组件文件结构

```vue
<template>
  <!-- 模板内容 -->
</template>

<script setup lang="ts">
// 1. 导入（按顺序：Vue/Pinia/第三方/本地）
// 2. defineOptions
// 3. Props/Emits 定义
// 4. 注入（store、router 等）
// 5. 响应式数据
// 6. 计算属性
// 7. 监听
// 8. 生命周期
// 9. 方法
</script>

<style scoped lang="less">
/* 样式 */
</style>
```

### 3.2 组件 Props 约束

```typescript
// ✅ 正确：使用接口定义复杂 Props
interface UserInfo {
  id: number
  name: string
  email?: string
}

const props = withDefaults(defineProps<{
  user: UserInfo
  loading?: boolean
  size?: 'small' | 'middle' | 'large'
}>(), {
  loading: false,
  size: 'middle'
})
```

### 3.3 Vue Transition 约束

> **⚠️ 重要约束**: Vue 的 `<Transition>` 组件要求子组件只能有一个根元素。

```vue
<!-- ❌ 错误：多个根元素 -->
<template>
  <CrudTable>...</CrudTable>
  <a-drawer>...</a-drawer>
  <a-modal>...</a-modal>
</template>

<!-- ✅ 正确：单一根元素包裹 -->
<template>
  <div class="role-page">
    <CrudTable>...</CrudTable>
    <a-drawer>...</a-drawer>
    <a-modal>...</a-modal>
  </div>
</template>
```

---

## 4. API 调用约束

### 4.1 统一 API 封装

```typescript
// ✅ 正确：使用封装的 request
import request from '@/utils/request'

// 所有 API 定义在 api/index.ts
export default {
  getUserList: (params: any = {}) => request.get('/user/list', { params }),
  createUser: (data: any = {}) => request.post('/user/create', data),
  updateUser: (data: any = {}) => request.post('/user/update', data),
  deleteUser: (params: any = {}) => request.delete('/user/delete', { params }),
}
```

### 4.2 请求响应处理

```typescript
// ✅ 正确：统一错误处理在 request.ts 拦截器中
// 组件中只需处理业务逻辑
async function fetchData() {
  loading.value = true
  try {
    const res: any = await api.getUserList(queryParams)
    tableData.value = res.data
    pagination.total = res.total
  } finally {
    loading.value = false
  }
}
```

---

## 5. 样式约束

### 5.1 使用 UnoCSS

```vue
<template>
  <!-- ✅ 正确：使用 UnoCSS 原子类 -->
  <div class="flex items-center justify-between p-4 bg-white rounded">
    <span class="text-lg font-bold text-gray-800">标题</span>
    <a-button type="primary">按钮</a-button>
  </div>
</template>
```

### 5.2 Less 样式规范

```less
// ✅ 正确：使用 scoped + less
<style scoped lang="less">
.user-page {
  padding: 16px;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 16px;
  }
}
</style>
```

---

## 6. 权限指令约束

```vue
<template>
  <!-- ✅ 正确：使用 v-permission 指令 -->
  <a-button v-permission="'post/api/v1/user/create'" type="primary">
    新增用户
  </a-button>
  
  <!-- 权限格式: {method}/{api_path} -->
  <!-- GET -> get, POST -> post, DELETE -> delete -->
</template>
```

---

## 7. 路由约束

### 7.1 静态路由

```typescript
// router/routes.ts
export const routes: RouteRecordRaw[] = [
  {
    path: '/system/user',
    name: '用户管理',
    component: markRaw(Layout),
    meta: { 
      title: '用户管理', 
      icon: 'icon-park-outline:user',
      order: 1 
    },
    children: [
      {
        path: '',
        name: '用户管理Default',
        component: () => import('@/views/system/user/index.vue'),
        meta: { 
          title: '用户管理',
          keepAlive: true 
        },
      },
    ],
  },
]
```

### 7.2 动态路由组件路径

```typescript
// ✅ 正确：组件路径映射规则
// 后端返回: { component: '/system/user' }
// 前端映射: /src/views/system/user/index.vue

const componentPath = `/src/views${child.component}/index.vue`
```

---

## 8. CrudTable 组件规范

> **⚠️ 重要约束**: 所有表格页面必须使用 `CrudTable` 通用组件。

### 8.1 使用 CrudTable 组件

```vue
<template>
  <div class="role-page">
    <CrudTable
      ref="crudTableRef"
      :columns="columns"
      :data-source="tableData"
      :loading="loading"
      :pagination="pagination"
      :filter-model="queryParams"
      :filter-item-count="filterItemCount"
      show-modal
      :modal-title="modalTitle"
      :modal-loading="modalLoading"
      :modal-form="modalForm"
      :modal-rules="modalRules"
      @search="handleSearch"
      @reset="handleReset"
      @table-change="handleTableChange"
      @modal-ok="handleSave"
    >
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6">
          <a-form-item label="角色名">
            <a-input v-model:value="queryParams.role_name" placeholder="请输入角色名" allow-clear />
          </a-form-item>
        </a-col>
      </template>

      <!-- 操作按钮 -->
      <template #actions>
        <a-button v-permission="'post/api/v1/role/create'" type="primary" @click="handleAdd">
          <PlusOutlined /> 新建角色
        </a-button>
      </template>

      <!-- 表格列自定义 -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          <a-tag color="blue">{{ record.name }}</a-tag>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button type="link" @click="handleEdit(record)">编辑</a-button>
            <a-popconfirm title="确定删除吗？" @confirm="handleDelete(record)">
              <a-button type="link" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>

      <!-- 弹窗表单 -->
      <template #modal-form="{ form, action }">
        <a-form-item label="角色名" name="name">
          <a-input v-model:value="form.name" placeholder="请输入角色名称" />
        </a-form-item>
      </template>
    </CrudTable>
  </div>
</template>

<script setup lang="ts">
import CrudTable from '@/components/CrudTable/index.vue'

const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 表格列定义
const columns = computed(() => [
  { title: '角色名', dataIndex: 'name', key: 'name', width: 150 },
  { title: '操作', key: 'action', width: 200, fixed: 'right' as const },
])

// 打开新增弹窗
function handleAdd() {
  modalTitle.value = '新增角色'
  crudTableRef.value?.openAddModal()
}

// 打开编辑弹窗
function handleEdit(record: any) {
  modalTitle.value = '编辑角色'
  crudTableRef.value?.openEditModal(record)
}
</script>
```

### 8.2 禁止事项

```vue
<!-- ❌ 错误：重复编写表格代码 -->
<template>
  <div>
    <a-card>
      <!-- 筛选表单 -->
      <a-form>...</a-form>
      <!-- 表格 -->
      <a-table>...</a-table>
    </a-card>
    <!-- 弹窗 -->
    <a-modal>...</a-modal>
  </div>
</template>
```

---

## 9. 表格列定义规范

```typescript
// ✅ 正确：列定义使用 computed
const columns = computed(() => [
  {
    title: '名称',
    dataIndex: 'name',
    key: 'name',
    width: 120,
    ellipsis: true,
  },
  {
    title: '状态',
    dataIndex: 'is_active',
    key: 'is_active',
    width: 100,
  },
  {
    title: '创建时间',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 180,
  },
  {
    title: '操作',
    key: 'action',
    fixed: 'right',
    width: 200,
  },
])
```

---

## 10. 表单验证规范

```typescript
// ✅ 正确：表单验证规则
const modalRules = {
  name: [
    { required: true, message: '请输入名称', trigger: 'blur' },
    { min: 2, max: 20, message: '长度在 2-20 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  role_ids: [
    { type: 'array', required: true, message: '请选择角色', trigger: 'change' },
  ],
}
```

---

## 11. 错误处理约束

```typescript
// ✅ 正确：统一错误处理在 request.ts
// 组件中只需要处理业务逻辑
async function handleSave() {
  modalLoading.value = true
  try {
    const apiCall = modalAction.value === 'add' 
      ? api.createData 
      : api.updateData
    await apiCall(modalForm)
    
    window.$message?.success(modalAction.value === 'add' ? '创建成功' : '更新成功')
    modalVisible.value = false
    fetchData()
  } finally {
    modalLoading.value = false
  }
}
```

---

## 12. 文件行数约束

> **⚠️ 重要约束**: 单个代码文件最大行数限制为 **600 行**。

### 12.1 Vue 组件拆分策略

```
# ❌ 错误：单个文件过大
views/user/index.vue (1200行)

# ✅ 正确：按功能拆分为 composables
views/user/
├── index.vue              # 主页面 (< 300行)
├── composables/
│   ├── useUserTable.ts    # 表格逻辑
│   ├── useUserForm.ts     # 表单逻辑
│   └── useUserPermission.ts # 权限逻辑
├── components/
│   ├── UserDetail.vue     # 详情组件
│   └── UserImportModal.vue # 导入弹窗
```

### 12.2 Composable 规范

```typescript
// composables/useUserTable.ts
import { ref, computed } from 'vue'
import api from '@/api'

export function useUserTable() {
  const loading = ref(false)
  const tableData = ref([])
  const pagination = ref({ page: 1, pageSize: 10, total: 0 })
  
  const columns = computed(() => [
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '操作', key: 'action', fixed: 'right' },
  ])
  
  async function fetchData(params = {}) {
    loading.value = true
    try {
      const res = await api.getUserList(params)
      tableData.value = res.data
      pagination.value.total = res.total
    } finally {
      loading.value = false
    }
  }
  
  return {
    loading,
    tableData,
    pagination,
    columns,
    fetchData,
  }
}
```

---

## 13. 禁止事项清单

- ❌ 禁止使用 Options API
- ❌ 禁止使用 `any` 类型（除非必要）
- ❌ 禁止直接修改 Pinia State（必须通过 action）
- ❌ 禁止在模板中写复杂表达式
- ❌ 禁止使用未注册的组件
- ❌ 禁止直接操作 DOM（使用 Vue 的 ref）
- ❌ 禁止在组件中直接调用 axios（使用封装的 request）
- ❌ 禁止组件模板有多个根元素（必须使用单一根元素包裹）
- ❌ 禁止表格页面重复编写表格/筛选/分页/弹窗代码（必须使用 CrudTable 组件）
- ❌ 禁止单个文件超过 600 行

---

*详细内容请查看 [tech-constraints-core.md](../tech-constraints-core.md)*
*最后更新: 2026-05-05*
