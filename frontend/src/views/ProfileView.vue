<template>
  <div class="profile">
    <el-card shadow="never">
      <template #header>
        <span class="card-title">我的</span>
      </template>

      <el-descriptions :column="1" border>
        <el-descriptions-item label="邮箱">{{ store.user?.email ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="邮箱验证">
          <el-tag :type="store.user?.email_verified ? 'success' : 'info'" size="small">
            {{ store.user?.email_verified ? '已验证' : '未验证' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="注册时间">
          {{ formattedCreatedAt }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" class="history">
      <template #header>
        <span class="card-title">我的面试记录</span>
      </template>
      <el-empty description="还没有面试记录，完成一次模拟面试后可在此回看评分与建议" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import { useUserStore } from '@/stores/user'

const store = useUserStore()

const formattedCreatedAt = computed(() => {
  if (!store.user?.created_at) return '-'
  const date = new Date(store.user.created_at)
  return Number.isNaN(date.getTime()) ? store.user.created_at : date.toLocaleString('zh-CN')
})
</script>

<style scoped>
.profile {
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-title {
  font-weight: 600;
}
</style>
