<template>
  <NSelect v-model:value="selectedValue" :options="tenantOptions" :loading="loading" :placeholder="placeholder"
    :clearable="clearable" :multiple="multiple" class="min-w-120px flex-1" consistent-menu-width
    @update:value="handleChange" />
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { NSelect } from 'naive-ui'
import { useUserStore } from '@/store'
import api from '@/api'

const props = defineProps({
  modelValue: {
    type: [String, Number, Array],
    default: null
  },
  placeholder: {
    type: String,
    default: '请选择租户'
  },
  clearable: {
    type: Boolean,
    default: true
  },
  multiple: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const userStore = useUserStore()
const loading = ref(false)
const tenantOptions = ref([])

const selectedValue = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const isRootUser = computed(() => {
  return userStore.userInfo?.username === 'root' || userStore.userInfo?.is_superuser
})

// 加载租户列表
const loadTenantOptions = async () => {
  if (!isRootUser.value) return

  loading.value = true
  try {
    const res = await api.getTenantSelect()
    // 将接口返回的数据转换为 NSelect 需要的格式
    tenantOptions.value = (res.data || []).map(item => ({
      label: item.name,
      value: item.id
    }))
  } catch (error) {
    console.error('加载租户列表失败:', error)
    tenantOptions.value = []
  } finally {
    loading.value = false
  }
}

// 监听用户信息变化
watch(() => userStore.userInfo, (newUserInfo) => {
  if (newUserInfo && isRootUser.value && tenantOptions.value.length === 0) {
    loadTenantOptions()
  }
}, { immediate: true })

onMounted(() => {
  if (isRootUser.value && tenantOptions.value.length === 0) {
    loadTenantOptions()
  }
})

const handleChange = (value) => {
  emit('change', value)
}
</script>
