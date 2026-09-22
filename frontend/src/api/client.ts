import type {
  ApiErrorPayload,
  AnswerResult,
  AuthResponse,
  Citation,
  Conversation,
  Course,
  CourseStats,
  Document,
  Member,
  Message,
  Quiz,
  QuizResult,
  ReviewPlan,
  SseEvent,
  User,
  WrongItem,
  WrongPracticeResponse,
} from '@/types'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export class ApiError extends Error {
  status: number
  payload: ApiErrorPayload

  constructor(status: number, payload: ApiErrorPayload) {
    super(payload.message)
    this.status = status
    this.payload = payload
  }
}

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('studymate_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  Object.entries(authHeaders()).forEach(([key, value]) => headers.set(key, value))
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (!response.ok) {
    let payload: ApiErrorPayload = {
      code: 'REQUEST_FAILED',
      message: `请求失败（${response.status}）`,
      request_id: response.headers.get('X-Request-ID') || '',
    }
    try {
      payload = (await response.json()) as ApiErrorPayload
    } catch {
      // Keep the transport-level fallback message.
    }
    if (response.status === 401) {
      localStorage.removeItem('studymate_token')
      localStorage.removeItem('studymate_user')
      window.dispatchEvent(new CustomEvent('studymate:auth-required'))
    }
    throw new ApiError(response.status, payload)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  register: (data: { email: string; password: string; display_name: string }) =>
    request<AuthResponse>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  login: (data: { email: string; password: string }) =>
    request<AuthResponse>('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  me: () => request<User>('/me'),
  updateMe: (display_name: string) =>
    request<User>('/me', { method: 'PATCH', body: JSON.stringify({ display_name }) }),
  courses: () => request<Course[]>('/courses'),
  createCourse: (name: string) =>
    request<Course>('/courses', { method: 'POST', body: JSON.stringify({ name }) }),
  joinCourse: (invite_code: string) =>
    request<Course>('/courses/join', {
      method: 'POST',
      body: JSON.stringify({ invite_code }),
    }),
  course: (courseId: string) => request<Course>(`/courses/${courseId}`),
  members: (courseId: string) => request<Member[]>(`/courses/${courseId}/members`),
  courseStats: (courseId: string) => request<CourseStats>(`/courses/${courseId}/stats`),
  documents: (courseId: string) => request<Document[]>(`/courses/${courseId}/documents`),
  document: (documentId: string) => request<Document>(`/documents/${documentId}`),
  deleteDocument: (documentId: string) =>
    request<void>(`/documents/${documentId}`, { method: 'DELETE' }),
  reindexDocument: (documentId: string) =>
    request<Document>(`/documents/${documentId}/reindex`, { method: 'POST' }),
  uploadDocument: (courseId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<Document>(`/courses/${courseId}/documents`, { method: 'POST', body: form })
  },
  conversations: (courseId: string) => request<Conversation[]>(`/courses/${courseId}/conversations`),
  createConversation: (courseId: string, title = '新会话') =>
    request<Conversation>(`/courses/${courseId}/conversations`, {
      method: 'POST',
      body: JSON.stringify({ title }),
    }),
  messages: (conversationId: string) =>
    request<Message[]>(`/conversations/${conversationId}/messages`),
  feedback: (messageId: string, rating: 'helpful' | 'inaccurate', reason?: string) =>
    request(`/messages/${messageId}/feedback`, {
      method: 'POST',
      body: JSON.stringify({ rating, reason }),
    }),
  quizzes: (courseId: string, payload: {
    document_ids: string[]
    question_count: 5 | 10
    question_types: Array<'single_choice' | 'short_answer'>
    chapter?: string
  }) => request<Quiz>(`/courses/${courseId}/quizzes`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  quiz: (quizId: string) => request<Quiz>(`/quizzes/${quizId}`),
  submitQuiz: (quizId: string, answers: Array<{ question_id: string; answer: string }>) =>
    request<QuizResult>(`/quizzes/${quizId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ answers }),
    }),
  wrongItems: (courseId: string) => request<WrongItem[]>(`/courses/${courseId}/wrong-items`),
  practiceWrongItem: (wrongItemId: string) =>
    request<WrongPracticeResponse>(`/wrong-items/${wrongItemId}/practice`, { method: 'POST' }),
  submitWrongPractice: (wrongItemId: string, answer: string) =>
    request<AnswerResult>(`/wrong-items/${wrongItemId}/answer`, {
      method: 'POST',
      body: JSON.stringify({ answer }),
    }),
  completeReviewItem: (wrongItemId: string) =>
    request(`/review-items/${wrongItemId}/complete`, { method: 'POST' }),  reviewPlan: (courseId: string) => request<ReviewPlan>(`/courses/${courseId}/review-plan`),
}

export async function streamChat(
  conversationId: string,
  question: string,
  onEvent: (event: SseEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE}/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify({ question }),
    signal,
  })
  if (!response.ok || !response.body) {
    let payload: ApiErrorPayload = {
      code: 'STREAM_FAILED',
      message: '无法建立流式回答连接。',
      request_id: response.headers.get('X-Request-ID') || '',
    }
    try {
      payload = (await response.json()) as ApiErrorPayload
    } catch {
      // Keep the transport-level fallback.
    }
    throw new ApiError(response.status, payload)
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() || ''
    for (const block of blocks) {
      const eventLine = block.split('\n').find((line) => line.startsWith('event: '))
      const dataLine = block.split('\n').find((line) => line.startsWith('data: '))
      if (!eventLine || !dataLine) continue
      onEvent({
        event: eventLine.slice(7) as SseEvent['event'],
        data: JSON.parse(dataLine.slice(6)) as Record<string, unknown>,
      })
    }
  }
}

export function citationFromMessage(message: Message): Citation[] {
  return message.citations_json || []
}
