import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { TokenPair, UserInfo } from '@/api/auth'
import { useUserStore } from '@/stores/user'

vi.mock('@/api/auth', () => ({
  register: vi.fn(),
  login: vi.fn(),
  refresh: vi.fn(),
  logout: vi.fn(),
  fetchMe: vi.fn(),
}))

const authApi = await import('@/api/auth')
const mocked = vi.mocked(authApi)

const userInfo: UserInfo = {
  id: 'user-1',
  email: 'candidate@example.com',
  email_verified: false,
  is_admin: false,
  created_at: '2026-10-26T05:00:00Z',
}

function tokenPair(access: string): TokenPair {
  return {
    access_token: access,
    refresh_token: `refresh-${access}`,
    token_type: 'bearer',
    expires_in: 1800,
    refresh_expires_in: 2592000,
  }
}

describe('用户状态仓库', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('登录成功后写入访问令牌与用户信息', async () => {
    mocked.login.mockResolvedValue(tokenPair('access-1'))
    mocked.fetchMe.mockResolvedValue(userInfo)

    const store = useUserStore()
    await store.login({ email: userInfo.email, password: 'Passw0rd1' })

    expect(store.accessToken).toBe('access-1')
    expect(store.isAuthenticated).toBe(true)
    expect(store.user?.email).toBe(userInfo.email)
  })

  it('刷新令牌成功后更新访问令牌', async () => {
    mocked.refresh.mockResolvedValue(tokenPair('access-2'))

    const store = useUserStore()
    store.accessToken = 'access-1'
    const token = await store.refreshAccessToken()

    expect(token).toBe('access-2')
    expect(store.accessToken).toBe('access-2')
  })

  it('刷新失败时清空登录态', async () => {
    mocked.refresh.mockRejectedValue(new Error('token expired'))

    const store = useUserStore()
    store.accessToken = 'access-1'
    store.user = userInfo

    const token = await store.refreshAccessToken()

    expect(token).toBeNull()
    expect(store.accessToken).toBeNull()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it('并发刷新只发起一次请求', async () => {
    mocked.refresh.mockResolvedValue(tokenPair('access-3'))

    const store = useUserStore()
    const [first, second] = await Promise.all([
      store.refreshAccessToken(),
      store.refreshAccessToken(),
    ])

    expect(first).toBe('access-3')
    expect(second).toBe('access-3')
    expect(mocked.refresh).toHaveBeenCalledTimes(1)
  })

  it('登出后清空登录态', async () => {
    mocked.login.mockResolvedValue(tokenPair('access-1'))
    mocked.fetchMe.mockResolvedValue(userInfo)
    mocked.logout.mockResolvedValue(undefined)

    const store = useUserStore()
    await store.login({ email: userInfo.email, password: 'Passw0rd1' })
    await store.logout()

    expect(store.accessToken).toBeNull()
    expect(store.user).toBeNull()
  })
})
