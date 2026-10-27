import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

import MainLayout from '@/layouts/MainLayout.vue'
import HomeView from '@/views/HomeView.vue'
import InterviewView from '@/views/InterviewView.vue'
import KnowledgeView from '@/views/KnowledgeView.vue'
import LoginView from '@/views/LoginView.vue'
import ProfileView from '@/views/ProfileView.vue'
import RegisterView from '@/views/RegisterView.vue'
import ResumeQuizView from '@/views/ResumeQuizView.vue'
import SettingsView from '@/views/SettingsView.vue'

import { useUserStore } from '@/stores/user'

/** 导航项顺序固定：首页、开始面试、简历押题、知识库、我的 */
export const navItems = [
  { name: 'home', label: '首页' },
  { name: 'interview', label: '开始面试' },
  { name: 'resume-quiz', label: '简历押题' },
  { name: 'knowledge', label: '知识库' },
  { name: 'profile', label: '我的' },
] as const

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { public: true },
  },
  {
    path: '/register',
    name: 'register',
    component: RegisterView,
    meta: { public: true },
  },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', name: 'home', component: HomeView },
      { path: 'interview', name: 'interview', component: InterviewView },
      { path: 'resume-quiz', name: 'resume-quiz', component: ResumeQuizView },
      { path: 'knowledge', name: 'knowledge', component: KnowledgeView },
      { path: 'profile', name: 'profile', component: ProfileView },
      // 设置页不进入主导航（导航固定五项），从顶栏用户区进入，仅管理员可见
      {
        path: 'settings',
        name: 'settings',
        component: SettingsView,
        meta: { requiresAdmin: true },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

let restoreInFlight: Promise<void> | null = null

router.beforeEach(async (to) => {
  const store = useUserStore()

  // 内存令牌丢失（页面刷新）时，先用 Cookie 中的刷新令牌静默恢复会话
  if (!store.isAuthenticated && !restoreInFlight) {
    restoreInFlight = store
      .restoreSession()
      .then(() => undefined)
      .catch(() => undefined)
      .finally(() => {
        restoreInFlight = null
      })
  }
  if (!store.isAuthenticated && restoreInFlight) {
    await restoreInFlight
  }

  if (!to.meta.public && !store.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (store.isAuthenticated && (to.name === 'login' || to.name === 'register')) {
    return { name: 'home' }
  }

  // 管理员页面：非管理员重定向首页
  if (to.meta.requiresAdmin && !store.isAdmin) {
    return { name: 'home' }
  }

  return true
})

export default router
