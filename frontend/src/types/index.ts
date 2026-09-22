export interface User {
  id: string
  email: string
  display_name: string
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface Course {
  id: string
  name: string
  invite_code: string
  owner_id: string
  role: 'owner' | 'member'
  created_at: string
}

export interface Member {
  id: string
  display_name: string
  email: string
  role: string
  joined_at: string
}

export interface CourseStats {
  document_count: number
  ready_document_count: number
  member_count: number
  conversation_count: number
  quiz_count: number
  wrong_item_count: number
}

export interface Document {
  id: string
  course_id: string
  original_name: string
  mime_type: string
  size_bytes: number
  checksum: string
  status: 'pending' | 'processing' | 'ready' | 'failed'
  error_message: string | null
  chunk_count: number
  created_by: string
  created_at: string
  processed_at: string | null
}

export interface Citation {
  index: number
  chunk_id: string
  document_id: string
  file_name: string
  page?: number | null
  slide?: number | null
  section?: string | null
  snippet: string
}

export interface Conversation {
  id: string
  course_id: string
  title: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  citations_json: Citation[] | null
  model_name: string | null
  prompt_version: string | null
  input_tokens: number | null
  output_tokens: number | null
  latency_ms: number | null
  created_at: string
}

export interface Question {
  id: string
  order_no: number
  type: 'single_choice' | 'short_answer'
  stem: string
  options: string[] | null
  knowledge_tags: string[]
}

export interface Quiz {
  id: string
  course_id: string
  title: string
  status: string
  question_count: number
  created_at: string
  questions: Question[]
}

export interface AnswerResult {
  question_id: string
  user_answer: string
  is_correct: boolean | null
  score: number
  correct_answer: string
  explanation: string
  citations: Citation[]
}

export interface QuizResult {
  attempt_id: string
  score: number
  max_score: number
  answers: AnswerResult[]
}

export interface WrongPracticeResponse {
  wrong_item_id: string
  question: Question
  answer_count: number
}

export interface WrongItem {
  id: string
  course_id: string
  question_id: string
  quiz_id: string
  knowledge_tag: string
  wrong_count: number
  consecutive_correct: number
  mastered: boolean
  last_wrong_at: string
  question: Question
}

export interface ReviewTask {
  wrong_item_id: string
  knowledge_tag: string
  question: Question
  wrong_count: number
  priority: number
  completed: boolean
}

export interface ReviewPlan {
  week_start: string
  tasks: ReviewTask[]
  total: number
  completed: number
}

export interface ApiErrorPayload {
  code: string
  message: string
  request_id: string
  details?: Record<string, unknown>
}

export interface SseEvent {
  event: 'retrieval' | 'citation' | 'token' | 'error' | 'done'
  data: Record<string, unknown>
}
