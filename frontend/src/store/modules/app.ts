import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useDark } from '@vueuse/core'

export const useAppStore = defineStore('app', () => {
  const isDark = useDark()
  const collapsed = ref(false)
  const reloadFlag = ref(true)
  const aliveKeys = ref<Record<string, number>>({})

  const switchCollapsed = () => {
    collapsed.value = !collapsed.value
  }

  const setCollapsed = (val: boolean) => {
    collapsed.value = val
  }

  const reloadPage = async () => {
    reloadFlag.value = false
    await new Promise((resolve) => setTimeout(resolve, 0))
    reloadFlag.value = true
  }

  const setAliveKeys = (key: string, val: number) => {
    aliveKeys.value[key] = val
  }

  return {
    isDark,
    collapsed,
    reloadFlag,
    aliveKeys,
    switchCollapsed,
    setCollapsed,
    reloadPage,
    setAliveKeys,
  }
})
