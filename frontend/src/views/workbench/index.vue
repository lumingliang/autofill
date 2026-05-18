<template>
  <div class="workbench-page">
    <a-row :gutter="[16, 16]">
      <a-col :span="24">
        <a-card>
          <div class="welcome">
            <a-avatar :src="userStore.avatar" :size="64">
              <template #icon><UserOutlined /></template>
            </a-avatar>
            <div class="welcome-info">
              <h2>早安，{{ userStore.name }}，开始您一天的工作吧！</h2>
              <p>今日晴，20℃ - 25℃</p>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[16, 16]" class="mt-4">
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card>
          <a-statistic title="用户总数" :value="stats.userCount">
            <template #prefix>
              <TeamOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card>
          <a-statistic title="角色数量" :value="stats.roleCount">
            <template #prefix>
              <SafetyOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card>
          <a-statistic title="菜单数量" :value="stats.menuCount">
            <template #prefix>
              <MenuOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card>
          <a-statistic title="部门数量" :value="stats.deptCount">
            <template #prefix>
              <ApartmentOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[16, 16]" class="mt-4">
      <a-col :span="24">
        <a-card title="系统公告">
          <a-list :data-source="notices">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta :title="item.title" :description="item.content" />
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useUserStore } from '@/store'
import {
  UserOutlined,
  TeamOutlined,
  SafetyOutlined,
  MenuOutlined,
  ApartmentOutlined,
} from '@ant-design/icons-vue'

const userStore = useUserStore()

const stats = reactive({
  userCount: 0,
  roleCount: 0,
  menuCount: 0,
  deptCount: 0,
})

const notices = [
  { title: '系统升级通知', content: '系统将于今晚 22:00 进行例行维护升级' },
  { title: '新功能上线', content: '新增租户管理功能，欢迎体验' },
  { title: '安全提醒', content: '请定期修改密码，确保账号安全' },
]
</script>

<style scoped lang="less">
.workbench-page {
  .welcome {
    display: flex;
    align-items: center;
    gap: 16px;

    .welcome-info {
      h2 {
        font-size: 20px;
        margin-bottom: 8px;
      }

      p {
        color: #999;
      }
    }
  }

  .mt-4 {
    margin-top: 16px;
  }
}
</style>
