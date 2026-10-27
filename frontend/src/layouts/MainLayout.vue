<template>
  <el-container class="app-shell" direction="vertical">
    <header class="app-header">
      <router-link :to="{ name: 'home' }" class="brand">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2l2.4 5.2L20 8.4l-4 4 .9 5.6L12 15.4 7.1 18l.9-5.6-4-4 5.6-1.2z" />
          </svg>
        </span>
        <span class="brand-name">AI 模拟面试平台</span>
      </router-link>

      <nav class="nav-menu" aria-label="主导航">
        <router-link
          v-for="item in navItems"
          :key="item.name"
          :to="pathOf(item.name)"
          class="nav-link"
          :class="{ active: isActive(item) }"
        >
          {{ item.label }}
        </router-link>
      </nav>

      <div class="user-area">
        <router-link
          v-if="store.isAdmin"
          :to="{ name: 'settings' }"
          class="settings-link"
          :class="{ active: route.name === 'settings' }"
          aria-label="设置"
          title="设置"
        >
          <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.01a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </router-link>
        <span class="user-email" :title="store.user?.email ?? ''">
          {{ store.user?.email ?? '未登录' }}
        </span>
        <el-button link class="logout-link" @click="onLogout">退出登录</el-button>
      </div>
    </header>

    <el-main class="app-main">
      <router-view v-slot="{ Component }">
        <keep-alive :include="keepAliveViews">
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useUserStore } from '@/stores/user'
import { navItems } from '@/router'

const route = useRoute()
const router = useRouter()
const store = useUserStore()

// KeepAlive 缓存的多步流程页面（登出时清空以重置状态）
const keepAliveViews = ref<string[]>(['ResumeQuizView', 'InterviewView'])

function pathOf(name: string): string {
  return name === 'home' ? '/' : `/${name}`
}

function isActive(item: { name: string }): boolean {
  return route.name === item.name
}

async function onLogout(): Promise<void> {
  await store.logout()
  // 卸载缓存的多步流程组件，避免串号；下一 tick 恢复缓存列表
  keepAliveViews.value = []
  nextTick(() => {
    keepAliveViews.value = ['ResumeQuizView', 'InterviewView']
  })
  router.push({ name: 'login' })
}
</script>

<style scoped>
.app-shell {
  min-height: 100dvh;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 28px;
  height: 60px;
  padding: 0 28px;
  background: rgba(255, 255, 255, 0.8);
  border-bottom: 1px solid var(--surface-border);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
}

.brand-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  color: #fff;
  background: var(--brand-gradient);
  box-shadow: 0 2px 12px var(--glow-blue);
}

.brand-name {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: var(--text-primary);
}

.nav-menu {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
}

.nav-link {
  position: relative;
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 14px;
  color: var(--text-secondary);
  transition:
    color var(--transition-ui),
    background-color var(--transition-ui);
}

.nav-link:hover {
  color: var(--text-primary);
  background: rgba(148, 163, 184, 0.1);
}

.nav-link.active {
  color: var(--brand-blue);
  font-weight: 600;
  background: var(--brand-gradient-soft);
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.35);
}

.nav-link.active::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 2px;
  width: 18px;
  height: 2px;
  border-radius: 2px;
  transform: translateX(-50%);
  background: var(--brand-gradient);
}

.user-area {
  display: flex;
  align-items: center;
  gap: 12px;
  white-space: nowrap;
}

.settings-link {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  color: var(--text-secondary);
  transition:
    color var(--transition-ui),
    background-color var(--transition-ui);
}

.settings-link:hover,
.settings-link.active {
  color: var(--brand-cyan);
  background: rgba(34, 211, 238, 0.1);
}

.user-email {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-secondary);
  font-size: 13px;
}

.logout-link {
  color: var(--text-secondary);
}

.logout-link:hover {
  color: var(--brand-cyan);
}

.app-main {
  padding: 32px 24px 48px;
}
</style>
