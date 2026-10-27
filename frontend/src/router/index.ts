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
      // 设置页不进入主导航（导航固定五项），从顶栏用户区进入
      { path: 'settings', name: 'settings', component: SettingsView },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const store = useUserStore()

  if (!to.meta.public && !store.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (store.isAuthenticated && (to.name === 'login' || to.name === 'register')) {
    return { name: 'home' }
  }

  return true
})

export default router
