<template>
  <div bg="#fafafc" flex flex-wrap items-start justify-between gap-4 b-1 rounded-2 p-4 bc-ccc dark:bg-black>
    <n-space wrap :size="[16, 12]">
      <slot />
      <div flex gap-2>
        <n-button secondary type="primary" @click="emit('reset')">重置</n-button>
        <n-button type="primary" @click="emit('search')">搜索</n-button>
      </div>
    </n-space>
  </div>
</template>

<script setup>
const emit = defineEmits(['search', 'reset'])
</script>
