import { http } from './http'

export interface Evidence {
  source: 'resume' | 'job_description' | 'knowledge'
  ref: string
  ref_id: string | null
  excerpt: string
}

export interface PredictedQuestion {
  position: number
  question: string
  difficulty: 'easy' | 'medium' | 'hard' | string
  reference_answer: string | null
  evidence: Evidence[]
}

export interface Prediction {
  id: string
  status: string
  target_role: string
  years_of_experience: string
  job_description: string
  programming_language: string | null
  model_name: string
  prompt_version: string
  generated_at: string
  questions: PredictedQuestion[]
}

export interface PredictionSummary {
  id: string
  target_role: string
  years_of_experience: string
  model_name: string
  prompt_version: string
  generated_at: string
  question_count: number
}

export interface PredictionPayload {
  resume_id: string
  target_role: string
  years_of_experience: string
  job_description: string
  programming_language?: string
}

export async function createPrediction(payload: PredictionPayload): Promise<Prediction> {
  const { data } = await http.post<Prediction>('/predictions', payload, {
    timeout: 150_000, // 押题同步生成可能持续数十秒
  })
  return data
}

export async function listPredictions(): Promise<PredictionSummary[]> {
  const { data } = await http.get<PredictionSummary[]>('/predictions')
  return data
}

export async function getPrediction(id: string): Promise<Prediction> {
  const { data } = await http.get<Prediction>(`/predictions/${id}`)
  return data
}
