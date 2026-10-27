import { http } from './http'

export interface UserInfo {
  id: string
  email: string
  email_verified: boolean
  is_admin: boolean
  created_at: string
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  refresh_expires_in: number
}

export interface Credentials {
  email: string
  password: string
}

export async function register(payload: Credentials): Promise<UserInfo> {
  const { data } = await http.post<UserInfo>('/auth/register', payload)
  return data
}

export async function login(payload: Credentials): Promise<TokenPair> {
  const { data } = await http.post<TokenPair>('/auth/login', payload)
  return data
}

export async function refresh(): Promise<TokenPair> {
  const { data } = await http.post<TokenPair>('/auth/refresh', {})
  return data
}

export async function logout(): Promise<void> {
  await http.post('/auth/logout', {})
}

export async function fetchMe(): Promise<UserInfo> {
  const { data } = await http.get<UserInfo>('/users/me')
  return data
}
