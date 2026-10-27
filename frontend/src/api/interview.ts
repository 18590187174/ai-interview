import { http } from './http'

export type InterviewStatus = 'ongoing' | 'completed' | 'abandoned'

export interface InterviewMessage {
  role: 'interviewer' | 'answerer'
  position: number
  content: string | null
  skipped: boolean
  created_at: string
}

export interface InterviewSession {
  id: string
  status: InterviewStatus
  prediction_id: string
  total_questions: number
  current_position: number
  target_role: string
  years_of_experience: string
  programming_language: string | null
  started_at: string
  finished_at: string | null
  messages: InterviewMessage[]
}

export interface QuestionItem {
  position: number
  question: string
  difficulty: string
  reference_answer: string | null
}

export interface InterviewSummary {
  id: string
  status: InterviewStatus
  target_role: string
  total_questions: number
  current_position: number
  started_at: string
  finished_at: string | null
  answered_count: number
}

export interface InterviewStartResult {
  interview: InterviewSession
  questions: QuestionItem[]
}

export interface AnswerResult {
  interview: InterviewSession
  questions: QuestionItem[]
  finished: boolean
}

export async function startInterview(predictionId: string): Promise<InterviewStartResult> {
  const { data } = await http.post<InterviewStartResult>('/interviews', {
    prediction_id: predictionId,
  })
  return data
}

export async function listInterviews(): Promise<InterviewSummary[]> {
  const { data } = await http.get<InterviewSummary[]>('/interviews')
  return data
}

export async function getInterview(id: string): Promise<InterviewSession> {
  const { data } = await http.get<InterviewSession>(`/interviews/${id}`)
  return data
}

export async function submitAnswer(id: string, content: string): Promise<AnswerResult> {
  const { data } = await http.post<AnswerResult>(`/interviews/${id}/answer`, { content })
  return data
}

export async function skipQuestion(id: string): Promise<AnswerResult> {
  const { data } = await http.post<AnswerResult>(`/interviews/${id}/skip`, {})
  return data
}

export async function abandonInterview(id: string): Promise<void> {
  await http.post(`/interviews/${id}/abandon`)
}
