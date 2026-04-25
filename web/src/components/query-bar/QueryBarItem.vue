<template>
  <div flex items-center gap-3>
    <label v-if="!isNullOrWhitespace(label)" flex-shrink-0 w-80px text-right text-14px text-gray-700 dark:text-gray-200>
      {{ label }}
    </label>
    <div flex-1 min-w-0>
      <slot />
    </div>
  </div>
</template>

<script setup>
import { isNullOrWhitespace } from '@/utils'
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    default: '',
  },
  labelWidth: {
    type: [Number, String],
    default: null,
  },
  contentWidth: {
    type: [Number, String],
    default: null,
  },
})

const labelStyle = computed(() => {
  if (props.labelWidth) {
    return { width: typeof props.labelWidth === 'number' ? `${props.labelWidth}px` : props.labelWidth }
  }
  // 默认自适应宽度，但设置最小宽度确保中文显示正常
  return { minWidth: '3.5rem' }
})
</script>
