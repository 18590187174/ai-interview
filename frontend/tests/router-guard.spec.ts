import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import router, { navItems } from '@/router'
import { useUserStore } from '@/stores/user'

describe('路由守卫', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    await router.replace('/')
  })

  it('未登录访问受保护页面时被拦截到登录页并记录目标地址', async () => {
    await router.push('/profile')

    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.redirect).toBe('/profile')
  })

  it('未登录可以访问登录页与注册页', async () => {
    await router.push('/login')
    expect(router.currentRoute.value.name).toBe('login')

    await router.push('/register')
    expect(router.currentRoute.value.name).toBe('register')
  })

  it('已登录访问登录页或注册页时跳转首页', async () => {
    const store = useUserStore()
    store.accessToken = 'access-token'

    await router.push('/login')
    expect(router.currentRoute.value.name).toBe('home')

    await router.push('/register')
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('已登录可以正常进入受保护页面', async () => {
    const store = useUserStore()
    store.accessToken = 'access-token'

    await router.push('/resume-quiz')
    expect(router.currentRoute.value.name).toBe('resume-quiz')
  })

  it('导航项顺序固定为首页、开始面试、简历押题、知识库、我的', () => {
    expect(navItems.map((item) => item.label)).toEqual([
      '首页',
      '开始面试',
      '简历押题',
      '知识库',
      '我的',
    ])
  })
})
