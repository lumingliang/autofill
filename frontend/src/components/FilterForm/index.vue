<template>
  <a-form :model="model" class="crud-filter-form filter-form">
    <a-row :gutter="16" class="filter-row">
      <!-- 表单项插槽 -->
      <slot name="items" />
      
      <!-- 操作按钮区域 -->
      <a-col 
        :xs="24" 
        :sm="12" 
        :md="actionColSpan.md" 
        :lg="actionColSpan.lg" 
        :xl="actionColSpan.xl"
        class="filter-actions-col"
        :class="{ 'align-right': shouldAlignRight }"
      >
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
            <slot name="extra-actions" />
          </a-space>
        </a-form-item>
      </a-col>
    </a-row>
  </a-form>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons-vue'

interface Props {
  model: Record<string, any>
  itemCount: number // 表单项数量
}

const props = defineProps<Props>()

const emit = defineEmits<{
  search: []
  reset: []
}>()

// 计算操作按钮是否应该右对齐
// 当表单项+按钮不能在一行显示时，按钮右对齐
const shouldAlignRight = computed(() => {
  // 基础逻辑：如果表单项超过3个，大概率需要多行，按钮右对齐
  // 实际可以根据窗口宽度做更复杂的计算
  return props.itemCount >= 3
})

// 操作按钮的列宽配置
// 当表单项较少时，按钮占据剩余空间
// 当表单项较多时，按钮占据标准宽度
const actionColSpan = computed(() => {
  const count = props.itemCount
  // 根据表单项数量动态调整按钮列宽
  if (count <= 2) {
    // 表单项少，按钮紧跟
    return { md: 8, lg: 6, xl: 6 }
  } else if (count === 3) {
    // 中等数量
    return { md: 8, lg: 6, xl: 6 }
  } else {
    // 表单项多，按钮占据整行或部分
    return { md: 8, lg: 6, xl: 6 }
  }
})

function handleSearch() {
  emit('search')
}

function handleReset() {
  emit('reset')
}
</script>

<style scoped lang="less">
.filter-form {
  .filter-row {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
  }
  
  .filter-actions-col {
    display: flex;
    
    &.align-right {
      justify-content: flex-end;
      
      :deep(.filter-actions) {
        justify-content: flex-end;
      }
    }
    
    :deep(.filter-actions) {
      display: flex;
      align-items: center;
      margin-bottom: 16px;
      justify-content: flex-start;
    }
  }
}
</style>
