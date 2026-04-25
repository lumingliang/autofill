<template>
  <AppPage :show-footer="showFooter">
    <header v-if="showHeader" mb-4 flex flex-wrap items-center justify-between gap-4 px-4>
      <slot v-if="$slots.header" name="header" />
      <template v-else>
        <h2 text-16px font-normal text-hex-333 dark:text-hex-ccc>{{ title || route.meta?.title }}</h2>
        <slot name="action" />
      </template>
    </header>

    <n-card flex-1 rounded-2>
      <slot />
    </n-card>
  </AppPage>
</template>

<script setup>
defineProps({
  showFooter: {
    type: Boolean,
    default: false,
  },
  showHeader: {
    type: Boolean,
    default: true,
  },
  title: {
    type: String,
    default: undefined,
  },
})
const route = useRoute()
</script>
