<template>
  <a-breadcrumb>
    <a-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
      <router-link v-if="item.path" :to="item.path">{{ item.title }}</router-link>
      <span v-else>{{ item.title }}</span>
    </a-breadcrumb-item>
  </a-breadcrumb>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const breadcrumbs = ref<any[]>([])

watch(
  () => route.matched,
  (matched) => {
    const list: any[] = []
    matched.forEach((item) => {
      if (item.meta?.title) {
        list.push({
          title: item.meta.title,
          path: item.path,
        })
      }
    })
    breadcrumbs.value = list
  },
  { immediate: true }
)
</script>
