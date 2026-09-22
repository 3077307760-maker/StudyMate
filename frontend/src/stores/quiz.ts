import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { api, ApiError } from '@/api'
import type { Quiz, QuizResult } from '@/types'

interface QuizDraft {
  answers: Record<string, string>
  savedAt: string
}

export const useQuizStore = defineStore('quiz', () => {
  const current = ref<Quiz | null>(null)
  const result = ref<QuizResult | null>(null)
  const answers = ref<Record<string, string>>({})
  const generating = ref(false)
  const submitting = ref(false)
  const error = ref('')

  const answeredCount = computed(() =>
    current.value
      ? current.value.questions.filter((question) => Boolean(answers.value[question.id]?.trim())).length
      : 0,
  )

  async function generate(
    courseId: string,
    payload: {
      document_ids: string[]
      question_count: 5 | 10
      question_types: Array<'single_choice' | 'short_answer'>
      chapter?: string
    },
  ) {
    generating.value = true
    error.value = ''
    result.value = null
    try {
      current.value = await api.quizzes(courseId, payload)
      answers.value = {}
      persistDraft()
      return current.value
    } catch (err) {
      error.value = err instanceof ApiError ? err.payload.message : '练习生成失败，请保留参数后重试。'
      throw err
    } finally {
      generating.value = false
    }
  }

  async function load(quizId: string) {
    current.value = await api.quiz(quizId)
    const saved = localStorage.getItem(`studymate_quiz_draft_${quizId}`)
    answers.value = saved ? (JSON.parse(saved) as QuizDraft).answers : {}
  }

  function setAnswer(questionId: string, answer: string) {
    answers.value[questionId] = answer
    persistDraft()
  }

  function persistDraft() {
    if (!current.value) return
    localStorage.setItem(
      `studymate_quiz_draft_${current.value.id}`,
      JSON.stringify({ answers: answers.value, savedAt: new Date().toISOString() } satisfies QuizDraft),
    )
  }

  async function submit() {
    if (!current.value) return
    submitting.value = true
    error.value = ''
    try {
      result.value = await api.submitQuiz(
        current.value.id,
        current.value.questions.map((question) => ({
          question_id: question.id,
          answer: answers.value[question.id] || '',
        })),
      )
      localStorage.removeItem(`studymate_quiz_draft_${current.value.id}`)
      return result.value
    } catch (err) {
      error.value = err instanceof ApiError ? err.payload.message : '提交失败，请稍后重试。'
      throw err
    } finally {
      submitting.value = false
    }
  }

  function clearCurrent() {
    current.value = null
    result.value = null
    answers.value = {}
    error.value = ''
  }

  return {
    current,
    result,
    answers,
    generating,
    submitting,
    error,
    answeredCount,
    generate,
    load,
    setAnswer,
    submit,
    clearCurrent,
  }
})
