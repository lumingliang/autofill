<template>
  <n-modal v-model:show="show" :style="modalStyle" preset="card" :title="title" size="huge" :bordered="false"
    :mask-closable="false">
    <slot />
    <template v-if="showFooter" #footer>
      <footer flex justify-end gap-2>
        <slot name="footer">
          <n-button @click="show = false">取消</n-button>
          <n-button :loading="loading" ml-20 type="primary" @click="emit('save')">保存</n-button>
        </slot>
      </footer>
    </template>
  </n-modal>
</template>

<script setup>
const props = defineProps({
  width: {
    type: [String, Number],
    default: null,
  },
  title: {
    type: String,
    default: '',
  },
  showFooter: {
    type: Boolean,
    default: true,
  },
  visible: {
    type: Boolean,
    required: true,
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:visible', 'save'])
const show = computed({
  get() {
    return props.visible
  },
  set(v) {
    emit('update:visible', v)
  },
})

const modalStyle = computed(() => {
  if (props.width) {
    return { width: props.width }
  }
  return { width: 'min(90vw, 600px)' }
})
</script>
