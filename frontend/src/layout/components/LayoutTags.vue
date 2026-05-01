<template>
  <div class="tags-wrapper">
    <a-tabs v-model:activeKey="activeKey" type="editable-card" hide-add @change="handleChange" @edit="handleEdit">
      <a-tab-pane v-for="tag in tagsStore.tags" :key="tag.path" :tab="tag.title"
        :closable="tagsStore.tags.length > 1" />
    </a-tabs>
    <a-dropdown class="tags-extra">
      <MoreOutlined />
      <template #overlay>
        <a-menu @click="handleExtraClick">
          <a-menu-item key="closeOther">关闭其他</a-menu-item>
          <a-menu-item key="closeLeft">关闭左侧</a-menu-item>
          <a-menu-item key="closeRight">关闭右侧</a-menu-item>
        </a-menu>
      </template>
    </a-dropdown>
  </div>
</template>

<script setup lang="ts">
import { useTagsStore } from '@/store'
import { MoreOutlined } from '@ant-design/icons-vue'
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const tagsStore = useTagsStore()

const activeKey = ref(route.path)

watch(
  () => route.path,
  (path) => {
    activeKey.value = path
    tagsStore.addTag({
      title: route.meta.title || '未命名',
      path,
    })
  },
  { immediate: true }
)

function handleChange(key: string) {
  router.push(key)
}

function handleEdit(targetKey: string) {
  tagsStore.removeTag(targetKey)
}

function handleExtraClick({ key }: { key: string }) {
  if (key === 'closeOther') {
    tagsStore.removeOther(activeKey.value)
  } else if (key === 'closeLeft') {
    tagsStore.removeLeft(activeKey.value)
  } else if (key === 'closeRight') {
    tagsStore.removeRight(activeKey.value)
  }
}
</script>

<style scoped lang="less">
.tags-wrapper {
  display: flex;
  align-items: center;
  background: #fff;
  padding: 0;
  border-bottom: 1px solid #f0f0f0;

  :deep(.ant-tabs) {
    flex: 1;

    .ant-tabs-nav {
      margin-bottom: 0;
    }

    .ant-tabs-tab {
      border-radius: 0;
      border-top: none;
    }
  }

  .tags-extra {
    padding: 0 12px;
    cursor: pointer;
    font-size: 16px;
  }
}
</style>
