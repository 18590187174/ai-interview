import { http } from './http'

export interface Resume {
  id: string
  original_name: string
  size_bytes: number
  content_type: string
  parse_status: 'pending' | 'succeeded' | 'failed'
  parse_error: string | null
  parse_error_code: string | null
  created_at: string
}

export async function uploadResume(file: File): Promise<Resume> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await http.post<Resume>('/resumes', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function listResumes(): Promise<Resume[]> {
  const { data } = await http.get<Resume[]>('/resumes')
  return data
}

export interface ResumePreview {
  id: string
  original_name: string
  parsed_text: string
}

export async function previewResume(id: string): Promise<ResumePreview> {
  const { data } = await http.get<ResumePreview>(`/resumes/${id}/preview`)
  return data
}

export async function deleteResume(id: string): Promise<void> {
  await http.delete(`/resumes/${id}`)
}
