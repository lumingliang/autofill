<template>
  <div class="top-menu-page">
    <a-card>
      <a-result title="一级菜单页面" sub-title="这是一个顶级菜单示例页面">
        <template #icon>
          <smile-outlined />
        </template>
        <template #extra>
          <a-button type="primary" @click="$router.push('/workbench')">
            返回工作台
          </a-button>
        </template>
      </a-result>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { SmileOutlined } from '@ant-design/icons-vue'

defineOptions({ name: '一级菜单' })
</script>

<style scoped lang="less">
.top-menu-page {
  padding: 24px;
}
</style>
