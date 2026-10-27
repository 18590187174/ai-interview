import { http } from './http'

export type DictType = 'target_role' | 'programming_language'

export interface DictItem {
  id: string
  type: DictType
  label: string
  value: string
  sort_order: number
  enabled: boolean
  created_at: string
}

export async function listByType(type: DictType): Promise<DictItem[]> {
  const { data } = await http.get<DictItem[]>(`/dictionaries/${type}`)
  return data
}

export async function listAll(): Promise<DictItem[]> {
  const { data } = await http.get<DictItem[]>('/dictionaries')
  return data
}

export async function createItem(payload: {
  type: DictType
  label: string
  value?: string
}): Promise<DictItem> {
  const { data } = await http.post<DictItem>('/dictionaries', payload)
  return data
}

export async function deleteItem(id: string): Promise<void> {
  await http.delete(`/dictionaries/${id}`)
}
