<template>
  <div class="tenant-selector mr-4">
    <n-dropdown :options="tenantOptions" @select="handleSelectTenant">
      <n-button text>
        <template #icon>
          <TheIcon icon="material-symbols:domain" :size="18" />
        </template>
        <span class="ml-1">{{ currentTenantName }}</span>
        <TheIcon icon="material-symbols:arrow-drop-down" :size="18" />
      </n-button>
    </n-dropdown>
  </div>
</template>

<script setup>
import { computed, h } from 'vue'
import { useUserStore } from '@/store'
import TheIcon from '@/components/icon/TheIcon.vue'

const userStore = useUserStore()

const currentTenantName = computed(() => {
  return userStore.currentTenant?.name || '选择租户'
})

const tenantOptions = computed(() => {
  return userStore.tenants.map(tenant => ({
    key: tenant.id,
    label: tenant.name,
    icon: () => h('span', { class: 'mr-2' }, tenant.id === userStore.currentTenantId ? '✓' : ''),
  }))
})

async function handleSelectTenant(tenantId) {
  if (tenantId === userStore.currentTenantId) {
    return
  }

  const success = await userStore.selectTenant(tenantId)
  if (success) {
    // 刷新页面以加载新租户的菜单和权限
    window.location.reload()
  }
}
</script>

<style scoped>
.tenant-selector {
  display: flex;
  align-items: center;
}
</style>
