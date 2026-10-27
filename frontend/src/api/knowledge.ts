import { http } from './http'

export interface KnowledgeDocument {
  id: string
  name: string
  size_bytes: number
  content_type: string
  is_public: boolean
  retrievable: boolean
  parse_error: string | null
  parse_error_code: string | null
  created_at: string
}

export async function uploadDocument(file: File, isPublic: boolean): Promise<KnowledgeDocument> {
  const form = new FormData()
  form.append('file', file)
  form.append('is_public', String(isPublic))
  const { data } = await http.post<KnowledgeDocument>('/knowledge/documents', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function listDocuments(): Promise<KnowledgeDocument[]> {
  const { data } = await http.get<KnowledgeDocument[]>('/knowledge/documents')
  return data
}

export async function getDocument(id: string): Promise<KnowledgeDocument> {
  const { data } = await http.get<KnowledgeDocument>(`/knowledge/documents/${id}`)
  return data
}

export async function deleteDocument(id: string): Promise<void> {
  await http.delete(`/knowledge/documents/${id}`)
}
