<template>
  <n-dropdown :options="options" @select="handleSelect">
    <div flex cursor-pointer items-center>
      <img :src="avatarUrl" mr10 h-35 w-35 rounded-full />
      <span>{{ userStore.name }}</span>
    </div>
  </n-dropdown>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useUserStore } from '@/store'
import { renderIcon } from '@/utils'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const router = useRouter()

const userStore = useUserStore()

// 头像 URL，添加时间戳防止缓存
const avatarUrl = ref('')

// 监听 avatar 变化，更新 URL 时添加时间戳
watch(() => userStore.avatar, (newAvatar) => {
  if (!newAvatar) {
    avatarUrl.value = ''
    return
  }
  // 移除旧的时间戳
  const baseUrl = newAvatar.split('?')[0]
  // 添加新的时间戳
  const timestamp = new Date().getTime()
  avatarUrl.value = `${baseUrl}?t=${timestamp}`
}, { immediate: true })

const options = [
  {
    label: t('header.label_profile'),
    key: 'profile',
    icon: renderIcon('mdi-account-arrow-right-outline', { size: '14px' }),
  },
  {
    label: t('header.label_logout'),
    key: 'logout',
    icon: renderIcon('mdi:exit-to-app', { size: '14px' }),
  },
]

function handleSelect(key) {
  if (key === 'profile') {
    router.push('/profile')
  } else if (key === 'logout') {
    $dialog.confirm({
      title: t('header.label_logout_dialog_title'),
      type: 'warning',
      content: t('header.text_logout_confirm'),
      confirm() {
        userStore.logout()
        $message.success(t('header.text_logout_success'))
      },
    })
  }
}
</script>
