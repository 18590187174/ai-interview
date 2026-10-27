import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as authApi from '@/api/auth'
import type { Credentials, UserInfo } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  // 访问令牌仅存内存，刷新页面需重新登录（刷新令牌由服务端 httpOnly Cookie 持有）
  const accessToken = ref<string | null>(null)
  const user = ref<UserInfo | null>(null)
  let refreshInFlight: Promise<string | null> | null = null
  // 每个页面会话只尝试一次会话恢复（刷新令牌在 httpOnly Cookie 中）
  const restoreAttempted = ref(false)

  const isAuthenticated = computed(() => accessToken.value !== null)
  const isAdmin = computed(() => user.value?.is_admin === true)

  /**
   * 页面刷新后用 httpOnly Cookie 中的刷新令牌静默恢复登录态，
   * 避免内存令牌丢失导致被守卫踢到登录页。
   */
  async function restoreSession(): Promise<boolean> {
    if (accessToken.value) {
      return true
    }
    if (restoreAttempted.value) {
      return false
    }
    restoreAttempted.value = true
    try {
      const tokens = await authApi.refresh()
      accessToken.value = tokens.access_token
      user.value = await authApi.fetchMe()
      return true
    } catch {
      clearSession()
      return false
    }
  }

  async function login(payload: Credentials): Promise<void> {
    const tokens = await authApi.login(payload)
    accessToken.value = tokens.access_token
    // 不使用响应体中的 refresh_token：它由服务端以 httpOnly Cookie 下发
    user.value = await authApi.fetchMe()
  }

  async function registerAccount(payload: Credentials): Promise<void> {
    await authApi.register(payload)
  }

  async function loadProfile(): Promise<void> {
    user.value = await authApi.fetchMe()
  }

  async function refreshAccessToken(): Promise<string | null> {
    if (!refreshInFlight) {
      refreshInFlight = authApi
        .refresh()
        .then((tokens) => {
          accessToken.value = tokens.access_token
          return tokens.access_token
        })
        .catch(() => {
          clearSession()
          return null
        })
        .finally(() => {
          refreshInFlight = null
        })
    }
    return refreshInFlight
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } finally {
      clearSession()
    }
  }

  function clearSession(): void {
    accessToken.value = null
    user.value = null
  }

  return {
    accessToken,
    user,
    isAuthenticated,
    isAdmin,
    restoreSession,
    login,
    registerAccount,
    loadProfile,
    refreshAccessToken,
    logout,
    clearSession,
  }
})
