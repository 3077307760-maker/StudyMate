import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { api, ApiError, streamChat } from '@/api'
import type { Citation, Conversation, Message, SseEvent } from '@/types'

function draftId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<Conversation[]>([])
  const current = ref<Conversation | null>(null)
  const messages = ref<Message[]>([])
  const citations = ref<Citation[]>([])
  const loading = ref(false)
  const streaming = ref(false)
  const retrievalStatus = ref('')
  const error = ref('')
  const errorCode = ref('')
  let controller: AbortController | null = null

  const sortedCitations = computed(() => [...citations.value].sort((a, b) => a.index - b.index))

  async function loadConversations(courseId: string) {
    conversations.value = await api.conversations(courseId)
    return conversations.value
  }

  async function createConversation(courseId: string, title = '新会话') {
    const conversation = await api.createConversation(courseId, title)
    conversations.value.unshift(conversation)
    current.value = conversation
    messages.value = []
    citations.value = []
    return conversation
  }

  async function openConversation(conversationId: string) {
    loading.value = true
    error.value = ''
    try {
      current.value =
        conversations.value.find((item) => item.id === conversationId) || current.value
      messages.value = await api.messages(conversationId)
      const assistant = [...messages.value].reverse().find((message) => message.role === 'assistant')
      citations.value = assistant?.citations_json || []
    } catch (err) {
      error.value = err instanceof ApiError ? err.payload.message : '会话加载失败。'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function sendQuestion(courseId: string, question: string) {
    if (!current.value || current.value.course_id !== courseId) {
      await createConversation(courseId, question.slice(0, 30) || '新会话')
    }
    const conversation = current.value
    if (!conversation) throw new Error('conversation not initialized')

    const userMessage: Message = {
      id: draftId('user'),
      conversation_id: conversation.id,
      role: 'user',
      content: question,
      citations_json: null,
      model_name: null,
      prompt_version: null,
      input_tokens: null,
      output_tokens: null,
      latency_ms: null,
      created_at: new Date().toISOString(),
    }
    const assistantDraft: Message = {
      id: draftId('assistant'),
      conversation_id: conversation.id,
      role: 'assistant',
      content: '',
      citations_json: [],
      model_name: null,
      prompt_version: 'chat-v1',
      input_tokens: null,
      output_tokens: null,
      latency_ms: null,
      created_at: new Date().toISOString(),
    }
    messages.value.push(userMessage, assistantDraft)
    citations.value = []
    streaming.value = true
    retrievalStatus.value = '正在检索课程资料…'
    error.value = ''
    errorCode.value = ''
    controller = new AbortController()

    try {
      await streamChat(
        conversation.id,
        question,
        (event: SseEvent) => {
          const message = messages.value.find((item) => item.id === assistantDraft.id)
          const conversationItem = conversations.value.find((item) => item.id === conversation.id)
          if (event.event === 'retrieval') {
            retrievalStatus.value = `已检索 ${event.data.hit_count || 0} 条资料`
          }
          if (event.event === 'citation' && message) {
            const citation = event.data as unknown as Citation
            if (!citations.value.some((item) => item.chunk_id === citation.chunk_id)) {
              citations.value.push(citation)
              message.citations_json = [...citations.value]
            }
          }
          if (event.event === 'token' && message) {
            retrievalStatus.value = ''
            message.content += String(event.data.text || '')
          }
          if (event.event === 'error') {
            errorCode.value = String(event.data.code || '')
            error.value = String(event.data.message || '回答失败。')
            if (message && !message.content) message.content = error.value
            if (event.data.message_id && message) message.id = String(event.data.message_id)
            streaming.value = false
          }
          if (event.event === 'done') {
            if (event.data.message_id && message) message.id = String(event.data.message_id)
            const usage = (event.data.usage || {}) as Record<string, number>
            if (message) {
              message.input_tokens = usage.input_tokens ?? null
              message.output_tokens = usage.output_tokens ?? null
              message.model_name = 'configured-model'
            }
            streaming.value = false
            retrievalStatus.value = ''
            if (conversationItem) conversationItem.updated_at = new Date().toISOString()
          }
        },
        controller.signal,
      )
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        error.value = err instanceof ApiError ? err.payload.message : '流式回答中断，请重试。'
        streaming.value = false
      }
    } finally {
      controller = null
    }
  }

  function cancelStream() {
    controller?.abort()
    streaming.value = false
    retrievalStatus.value = ''
  }

  return {
    conversations,
    current,
    messages,
    citations: sortedCitations,
    loading,
    streaming,
    retrievalStatus,
    error,
    errorCode,
    loadConversations,
    createConversation,
    openConversation,
    sendQuestion,
    cancelStream,
  }
})
