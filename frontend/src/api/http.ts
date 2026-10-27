import type { AxiosAdapter, AxiosError, InternalAxiosRequestConfig } from 'axios'
import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export interface ApiErrorPayload {
  code: string
  message: string
  trace_id?: string
  details?: Array<{ field: string; message: string }>
}

export class RequestError extends Error {
  readonly code: string
  readonly status: number
  readonly traceId?: string
  readonly details?: ApiErrorPayload['details']

  constructor(status: number, payload: ApiErrorPayload) {
    super(payload.message ?? '请求失败')
    this.name = 'RequestError'
    this.code = payload.code ?? 'UNKNOWN'
    this.status = status
    this.traceId = payload.trace_id
    this.details = payload.details
  }
}

interface AuthBridge {
  getAccessToken: () => string | null
  refresh: () => Promise<string | null>
  onUnauthorized: () => void
}

let bridge: AuthBridge | null = null

export function registerAuthBridge(value: AuthBridge): void {
  bridge = value
}

type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean }

function toRequestError(error: AxiosError): RequestError {
  const status = error.response?.status ?? 0
  const payload = (error.response?.data ?? {}) as ApiErrorPayload
  if (payload && typeof payload === 'object' && 'code' in payload) {
    return new RequestError(status, payload)
  }
  return new RequestError(status, { code: 'NETWORK_ERROR', message: error.message })
}

export function createHttp(adapter?: AxiosAdapter) {
  const client = axios.create({
    baseURL,
    withCredentials: true, // 携带服务端下发的 httpOnly 刷新令牌
    adapter,
  })

  client.interceptors.request.use((config) => {
    const token = bridge?.getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  client.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const original = error.config as RetriableConfig | undefined
      const status = error.response?.status

      const canRetry =
        status === 401 &&
        !!original &&
        !original._retry &&
        !!bridge &&
        !(original.url ?? '').includes('/auth/refresh') &&
        !(original.url ?? '').includes('/auth/login')

      if (!canRetry) {
        throw toRequestError(error)
      }

      original._retry = true
      const token = await bridge!.refresh()
      if (!token) {
        bridge!.onUnauthorized()
        throw toRequestError(error)
      }

      original.headers.Authorization = `Bearer ${token}`
      return client.request(original)
    },
  )

  return client
}

export const http = createHttp()
