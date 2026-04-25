# CRUD 组件响应式改造文档

## 改造概述

本次改造针对前端 CRUD 公共组件进行响应式优化，移除硬编码像素值，改用 UnoCSS 原子类进行布局，确保在不同屏幕尺寸下都能良好展示。

## 技术栈

- Vue 3
- Naive UI
- UnoCSS (原子化 CSS)

## 改造组件清单

### 1. CrudTable.vue

**改造前问题：**
- 使用 `mb-30` 固定下边距
- `scrollX` 默认值为 450px 固定像素

**改造内容：**
```vue
<!-- 改造前 -->
<QueryBar v-if="$slots.queryBar" mb-30 @search="handleSearch" @reset="handleReset">
<n-data-table :scroll-x="scrollX" ... />

<!-- 改造后 -->
<div v-bind="$attrs" flex flex-col gap-4>
  <QueryBar v-if="$slots.queryBar" @search="handleSearch" @reset="handleReset">
  <n-data-table :scroll-x="scrollX" flex-1 ... />
</div>
```

**Props 变更：**
- `scrollX`: 默认值从 `450` 改为 `'auto'`，支持自适应或传入具体值

---

### 2. CrudModal.vue

**改造前问题：**
- `width: '600px'` 固定像素宽度
- 按钮间距使用 `ml-20` 固定值

**改造内容：**
```vue
<!-- 改造前 -->
<n-modal :style="{ width }" ...>
  <footer flex justify-end>
    <n-button ml-20 type="primary">保存</n-button>
  </footer>
</n-modal>

<!-- 改造后 -->
<n-modal :style="modalStyle" ...>
  <footer flex justify-end gap-2>
    <n-button type="primary">保存</n-button>
  </footer>
</n-modal>
```

**Props 变更：**
- `width`: 默认值从 `'600px'` 改为 `null`
- 新增计算属性 `modalStyle`: 默认使用 `min(90vw, 600px)` 响应式宽度

**使用方式：**
```vue
<!-- 默认响应式宽度 (90vw, 最大600px) -->
<CrudModal v-model:visible="visible" title="标题">

<!-- 自定义固定宽度 -->
<CrudModal v-model:visible="visible" title="标题" width="800px">
```

---

### 3. QueryBar.vue

**改造前问题：**
- `min-h-60` 固定最小高度
- `rounded-8` 固定圆角
- `p-15` 固定内边距
- 按钮间距 `ml-20`

**改造内容：**
```vue
<!-- 改造前 -->
<div bg="#fafafc" min-h-60 flex items-start justify-between b-1 rounded-8 p-15 ...>
  <n-space wrap :size="[35, 15]">
    <n-button ml-20 type="primary">搜索</n-button>
  </n-space>
</div>

<!-- 改造后 -->
<div bg="#fafafc" flex flex-wrap items-start justify-between gap-4 b-1 rounded-2 p-4 ...>
  <n-space wrap :size="[16, 12]">
    <div flex gap-2>
      <n-button type="primary">搜索</n-button>
    </div>
  </n-space>
</div>
```

---

### 4. QueryBarItem.vue

**改造前问题：**
- `labelWidth: 80` 固定像素宽度
- `contentWidth: 220` 固定像素宽度
- 使用 `:style="{ width: labelWidth + 'px' }"` 内联样式

**改造内容：**
```vue
<!-- 改造前 -->
<div flex items-center>
  <label w-80 flex-shrink-0 :style="{ width: labelWidth + 'px' }">{{ label }}</label>
  <div><slot /></div>
</div>

<!-- 改造后 -->
<div flex items-center gap-2>
  <label flex-shrink-0 text-sm text-gray-600 dark:text-gray-300 :class="labelClass">{{ label }}</label>
  <div flex-1 min-w-0><slot /></div>
</div>
```

**Props 变更：**
- `labelWidth`: 默认值从 `80` 改为 `null`，使用响应式类 `w-16 sm:w-18 md:w-20`
- `contentWidth`: 默认值从 `220` 改为 `null`

**响应式规则：**
- 小屏幕: `w-16` (64px)
- 中屏幕: `sm:w-18` (72px)
- 大屏幕: `md:w-20` (80px)

---

### 5. CommonPage.vue

**改造前问题：**
- `mb-15` 固定下边距
- `min-h-45` 固定最小高度
- `px-15` 固定水平内边距
- `text-22` 固定字体大小
- `rounded-10` 固定圆角

**改造内容：**
```vue
<!-- 改造前 -->
<header v-if="showHeader" mb-15 min-h-45 flex items-center justify-between px-15>
  <h2 text-22 font-normal ...>{{ title }}</h2>
</header>
<n-card flex-1 rounded-10>

<!-- 改造后 -->
<header v-if="showHeader" mb-4 flex flex-wrap items-center justify-between gap-4 px-4>
  <h2 text-xl font-normal ...>{{ title }}</h2>
</header>
<n-card flex-1 rounded-2>
```

---

## UnoCSS 常用响应式类参考

### 间距
```
gap-2     → 0.5rem (8px)
gap-4     → 1rem (16px)
px-4      → padding-left/right: 1rem
py-2      → padding-top/bottom: 0.5rem
```

### 响应式断点
```
sm:   → 640px
md:   → 768px
lg:   → 1024px
xl:   → 1280px
```

### 宽度
```
w-full    → 100%
w-16      → 4rem (64px)
w-20      → 5rem (80px)
min-w-0   → min-width: 0 (防止flex子项溢出)
```

### 字体大小
```
text-sm   → 0.875rem (14px)
text-base → 1rem (16px)
text-lg   → 1.125rem (18px)
text-xl   → 1.25rem (20px)
```

---

## 使用示例

### 基础 CRUD 页面
```vue
<template>
  <CommonPage title="用户管理">
    <template #action>
      <n-button type="primary" @click="handleAdd">新增</n-button>
    </template>
    
    <CrudTable ref="$table" :columns="columns" :get-data="api.getList">
      <template #queryBar>
        <QueryBarItem label="用户名">
          <n-input v-model:value="queryItems.username" />
        </QueryBarItem>
        <QueryBarItem label="状态">
          <n-select v-model:value="queryItems.status" :options="statusOptions" />
        </QueryBarItem>
      </template>
    </CrudTable>
    
    <CrudModal v-model:visible="modalVisible" title="编辑用户" @save="handleSave">
      <n-form>
        <n-form-item label="用户名">
          <n-input v-model:value="form.username" />
        </n-form-item>
      </n-form>
    </CrudModal>
  </CommonPage>
</template>
```

### 自定义模态框宽度
```vue
<!-- 宽屏模态框 -->
<CrudModal v-model:visible="visible" title="详情" width="800px">

<!-- 全屏模态框 -->
<CrudModal v-model:visible="visible" title="预览" width="90vw">
```

---

## 注意事项

1. **避免使用固定像素值**：优先使用 UnoCSS 提供的原子类
2. **响应式优先**：使用 `flex-wrap` 让内容在小屏幕自动换行
3. **间距使用 gap**：替代 margin-left/right，更易于维护
4. **字体使用相对单位**：使用 `text-sm`、`text-xl` 等替代固定像素
5. **表格列宽**：使用 `min-width` 或百分比，避免固定像素

---

## 后续优化建议

1. 考虑为表格添加横向滚动提示
2. 移动端可隐藏部分非关键列
3. 考虑使用 Naive UI 的 `n-grid` 进行更复杂的布局
4. 表单可考虑使用 `n-grid` 实现响应式栅格布局
