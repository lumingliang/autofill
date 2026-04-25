<template>
  <div class="profile-page">
    <a-row :gutter="[16, 16]">
      <a-col :span="8">
        <a-card title="个人信息">
          <div class="avatar-wrapper">
            <a-avatar :src="userStore.avatar" :size="100">
              <template #icon><UserOutlined /></template>
            </a-avatar>
            <a-upload
              :show-upload-list="false"
              :before-upload="beforeUpload"
              accept="image/*"
            >
              <a-button type="link">更换头像</a-button>
            </a-upload>
          </div>
          <a-descriptions :column="1" bordered>
            <a-descriptions-item label="用户名">{{ userStore.name }}</a-descriptions-item>
            <a-descriptions-item label="邮箱">{{ userStore.email }}</a-descriptions-item>
            <a-descriptions-item label="角色">
              <a-tag v-for="role in userStore.userInfo.roles" :key="role.id" color="blue">
                {{ role.name }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="超级用户">
              {{ userStore.isSuperUser ? '是' : '否' }}
            </a-descriptions-item>
          </a-descriptions>
        </a-card>
      </a-col>
      <a-col :span="16">
        <a-tabs type="line" animated>
          <a-tab-pane key="info" tab="修改信息">
            <a-form
              ref="infoFormRef"
              :model="infoForm"
              :rules="infoRules"
              :label-col="{ span: 4 }"
              :wrapper-col="{ span: 16 }"
              @finish="updateProfile"
            >
              <a-form-item label="头像" name="avatar">
                <a-avatar :src="infoForm.avatar" :size="64" />
                <a-upload
                  :show-upload-list="false"
                  :before-upload="beforeUploadInfo"
                  accept="image/*"
                >
                  <a-button type="link">更换头像</a-button>
                </a-upload>
              </a-form-item>
              <a-form-item label="用户名" name="username">
                <a-input v-model:value="infoForm.username" placeholder="请输入用户名" />
              </a-form-item>
              <a-form-item label="邮箱" name="email">
                <a-input v-model:value="infoForm.email" placeholder="请输入邮箱" />
              </a-form-item>
              <a-form-item :wrapper-col="{ offset: 4, span: 16 }">
                <a-button type="primary" html-type="submit" :loading="isLoading">更新</a-button>
              </a-form-item>
            </a-form>
          </a-tab-pane>
          <a-tab-pane key="password" tab="修改密码">
            <a-form
              ref="passwordFormRef"
              :model="passwordForm"
              :rules="passwordRules"
              :label-col="{ span: 4 }"
              :wrapper-col="{ span: 16 }"
              @finish="updatePassword"
            >
              <a-form-item label="原密码" name="old_password">
                <a-input-password v-model:value="passwordForm.old_password" placeholder="请输入原密码" />
              </a-form-item>
              <a-form-item label="新密码" name="new_password">
                <a-input-password v-model:value="passwordForm.new_password" placeholder="请输入新密码" />
              </a-form-item>
              <a-form-item label="确认密码" name="confirm_password">
                <a-input-password v-model:value="passwordForm.confirm_password" placeholder="请再次输入新密码" />
              </a-form-item>
              <a-form-item :wrapper-col="{ offset: 4, span: 16 }">
                <a-button type="primary" html-type="submit" :loading="isLoading">更新</a-button>
              </a-form-item>
            </a-form>
          </a-tab-pane>
        </a-tabs>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useUserStore } from '@/store'
import { UserOutlined } from '@ant-design/icons-vue'
import api from '@/api'

const userStore = useUserStore()
const isLoading = ref(false)

// 用户信息的表单
const infoFormRef = ref()
const infoForm = reactive({
  avatar: userStore.avatar,
  username: userStore.name,
  email: userStore.email,
})

// 监听 store 中头像变化，同步到表单
watch(() => userStore.avatar, (newAvatar) => {
  infoForm.avatar = newAvatar
}, { immediate: true })

// 头像变更处理
function handleAvatarChange(newAvatarUrl: string) {
  infoForm.avatar = newAvatarUrl
  // 同时更新 store 中的头像
  userStore.setUserInfo({ avatar: newAvatarUrl })
}

async function updateProfile() {
  isLoading.value = true
  try {
    const res: any = await api.updateUser({
      id: userStore.userId,
      avatar: infoForm.avatar,
      username: infoForm.username,
      email: infoForm.email,
    })
    if (res.code === 200) {
      userStore.setUserInfo({
        avatar: infoForm.avatar,
        username: infoForm.username,
        email: infoForm.email,
      })
      window.$message?.success('更新成功')
    }
  } catch (error) {
    console.error('更新失败', error)
  } finally {
    isLoading.value = false
  }
}

const infoRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
}

// 修改密码的表单
const passwordFormRef = ref()
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

async function updatePassword() {
  isLoading.value = true
  try {
    const res: any = await api.updatePassword({
      ...passwordForm,
      id: userStore.userId,
    })
    if (res.code === 200) {
      window.$message?.success(res.msg || '密码修改成功')
      passwordFormRef.value.resetFields()
    }
  } catch (error) {
    console.error('修改密码失败', error)
  } finally {
    isLoading.value = false
  }
}

const passwordRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }],
  confirm_password: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (_rule: any, value: string) => {
        if (value !== passwordForm.new_password) {
          return Promise.reject('两次输入的密码不一致')
        }
        return Promise.resolve()
      },
      trigger: 'blur',
    },
  ],
}

function beforeUpload(file: File) {
  const isJpgOrPng = file.type === 'image/jpeg' || file.type === 'image/png'
  if (!isJpgOrPng) {
    window.$message?.error('只支持 JPG/PNG 格式!')
    return false
  }
  const isLt2M = file.size / 1024 / 1024 < 2
  if (!isLt2M) {
    window.$message?.error('图片大小不能超过 2MB!')
    return false
  }
  api.uploadAvatar(file).then((res: any) => {
    if (res.code === 200) {
      userStore.setUserInfo({ avatar: res.data.url })
      window.$message?.success('头像上传成功')
    }
  })
  return false
}

function beforeUploadInfo(file: File) {
  const isJpgOrPng = file.type === 'image/jpeg' || file.type === 'image/png'
  if (!isJpgOrPng) {
    window.$message?.error('只支持 JPG/PNG 格式!')
    return false
  }
  const isLt2M = file.size / 1024 / 1024 < 2
  if (!isLt2M) {
    window.$message?.error('图片大小不能超过 2MB!')
    return false
  }
  api.uploadAvatar(file).then((res: any) => {
    if (res.code === 200) {
      handleAvatarChange(res.data.url)
    }
  })
  return false
}
</script>

<style scoped lang="less">
.profile-page {
  .avatar-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-bottom: 24px;
  }
}
</style>
