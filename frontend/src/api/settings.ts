import { http } from './http'

export interface LLMSettings {
  has_api_key: boolean
  api_key_masked: string | null
  base_url: string
  model: string
  source: 'database' | 'environment' | 'none'
}

export interface LLMSettingsUpdate {
  api_key?: string
  base_url?: string
  model?: string
}

export interface LLMSettingsSaveResult {
  has_api_key: boolean
  api_key_masked: string | null
  message: string
}

export async function getLLMSettings(): Promise<LLMSettings> {
  const { data } = await http.get<LLMSettings>('/settings/llm')
  return data
}

export async function updateLLMSettings(payload: LLMSettingsUpdate): Promise<LLMSettingsSaveResult> {
  const { data } = await http.put<LLMSettingsSaveResult>('/settings/llm', payload)
  return data
}
