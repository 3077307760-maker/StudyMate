import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'

import MarkdownBlock from '@/components/MarkdownBlock.vue'
import { useAuthStore, useQuizStore } from '@/stores'
import type { Quiz } from '@/types'

describe('frontend state', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('clears authentication state on logout', () => {
    const auth = useAuthStore()
    localStorage.setItem('studymate_token', 'token')
    localStorage.setItem('studymate_user', JSON.stringify({ id: '1', display_name: 'Tester' }))
    auth.logout()
    expect(auth.token).toBe('')
    expect(localStorage.getItem('studymate_token')).toBeNull()
  })

  it('persists quiz draft answers', () => {
    const quizStore = useQuizStore()
    const quiz: Quiz = {
      id: 'quiz-1',
      course_id: 'course-1',
      title: '测试练习',
      status: 'ready',
      question_count: 1,
      created_at: new Date().toISOString(),
      questions: [
        {
          id: 'q1',
          order_no: 1,
          type: 'single_choice',
          stem: '题目',
          options: ['A', 'B', 'C', 'D'],
          knowledge_tags: ['测试'],
        },
      ],
    }
    quizStore.current = quiz
    quizStore.setAnswer('q1', 'A')
    const draft = JSON.parse(localStorage.getItem('studymate_quiz_draft_quiz-1') || '{}')
    expect(draft.answers.q1).toBe('A')
  })
})

describe('MarkdownBlock', () => {
  it('sanitizes script and event handler HTML', () => {
    const wrapper = mount(MarkdownBlock, {
      props: { content: '<img src=x onerror=alert(1)><script>alert(2)</script>安全内容' },
    })
    expect(wrapper.html()).not.toContain('onerror')
    expect(wrapper.html()).not.toContain('<script')
    expect(wrapper.text()).toContain('安全内容')
  })
})
