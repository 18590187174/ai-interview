import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { AxiosError } from 'axios'
import { beforeEach, describe, expect, it } from 'vitest'

import { RequestError, createHttp, registerAuthBridge } from '@/api/http'

interface AdapterOptions {
  refreshStatus?: number
  protectedRequiresToken?: string
  protectedStatus?: number
}

interface AdapterLog {
  urls: string[]
  authorizations: string[]
}

function makeResponse(
  config: InternalAxiosRequestConfig,
  status: number,
  data: unknown,
): AxiosResponse {
  return {
    data,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    headers: {},
    config,
  }
}

/** 自定义 adapter 需自行判定状态码：非 2xx 必须 reject，否则 axios 视为成功。 */
function settle(config: InternalAxiosRequestConfig, response: AxiosResponse): AxiosResponse {
  const validateStatus = config.validateStatus
  if (!validateStatus || validateStatus(response.status)) {
    return response
  }
  throw new AxiosError(
    `Request failed with status code ${response.status}`,
    undefined,
    config,
    undefined,
    response,
  )
}

function buildAdapter(options: AdapterOptions, log: AdapterLog): AxiosAdapter {
  return async (config) => {
    const url = String(config.url ?? '')
    const authorization = String(config.headers?.Authorization ?? '')
    log.urls.push(url)
    log.authorizations.push(authorization)

    if (url.includes('/auth/refresh')) {
      const status = options.refreshStatus ?? 200
      if (status !== 200) {
        return settle(
          config,
          makeResponse(config, status, { code: 'TOKEN_INVALID', message: '刷新令牌无效' }),
        )
      }
      return settle(
        config,
        makeResponse(config, 200, {
          access_token: 'fresh',
          refresh_token: 'refresh-2',
          token_type: 'bearer',
          expires_in: 1800,
          refresh_expires_in: 2592000,
        }),
      )
    }

    const required = options.protectedRequiresToken
    if (required && authorization === `Bearer ${required}`) {
      return settle(config, makeResponse(config, 200, { email: 'candidate@example.com' }))
    }

    return settle(
      config,
      makeResponse(config, options.protectedStatus ?? 401, {
        code: 'TOKEN_EXPIRED',
        message: '访问令牌已过期',
      }),
    )
  }
}

function emptyLog(): AdapterLog {
  return { urls: [], authorizations: [] }
}

describe('Axios 静默续期拦截器', () => {
  let token: string | null
  let unauthorizedCalled: boolean
  let refreshShouldFail: boolean

  beforeEach(() => {
    token = 'stale'
    unauthorizedCalled = false
    refreshShouldFail = false
    registerAuthBridge({
      getAccessToken: () => token,
      refresh: async () => {
        if (refreshShouldFail) {
          return null
        }
        token = 'fresh'
        return 'fresh'
      },
      onUnauthorized: () => {
        unauthorizedCalled = true
      },
    })
  })

  it('令牌过期时自动续期并重试原请求', async () => {
    const log = emptyLog()
    const client = createHttp(buildAdapter({ protectedRequiresToken: 'fresh' }, log))

    const response = await client.get('/users/me')

    expect(response.data.email).toBe('candidate@example.com')
    expect(log.urls).toEqual(['/users/me', '/users/me'])
    expect(log.authorizations[0]).toBe('Bearer stale')
    expect(log.authorizations[1]).toBe('Bearer fresh')
    expect(unauthorizedCalled).toBe(false)
  })

  it('续期失败时结束登录态并抛出统一错误', async () => {
    refreshShouldFail = true
    const log = emptyLog()
    const client = createHttp(buildAdapter({ protectedRequiresToken: 'fresh' }, log))

    await expect(client.get('/users/me')).rejects.toMatchObject({ code: 'TOKEN_EXPIRED' })
    expect(unauthorizedCalled).toBe(true)
    expect(log.urls).toEqual(['/users/me'])
  })

  it('刷新接口自身失败时不重试，避免死循环', async () => {
    const log = emptyLog()
    const client = createHttp(buildAdapter({ refreshStatus: 401 }, log))

    await expect(client.post('/auth/refresh', {})).rejects.toBeInstanceOf(RequestError)
    expect(log.urls).toEqual(['/auth/refresh'])
  })

  it('非 401 错误不触发续期', async () => {
    const log = emptyLog()
    const client = createHttp(
      buildAdapter({ protectedRequiresToken: 'fresh', protectedStatus: 500 }, log),
    )

    await expect(client.get('/users/me')).rejects.toMatchObject({ status: 500 })
    expect(log.urls).toEqual(['/users/me'])
  })

  it('请求会自动携带当前访问令牌', async () => {
    const log = emptyLog()
    const client = createHttp(buildAdapter({ protectedRequiresToken: 'stale' }, log))

    await client.get('/users/me')

    expect(log.authorizations).toEqual(['Bearer stale'])
  })
})
