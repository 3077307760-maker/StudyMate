<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChatDotRound, CircleClose, Plus, Promotion } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { api, ApiError } from '@/api'
import CitationCard from '@/components/CitationCard.vue'
import MarkdownBlock from '@/components/MarkdownBlock.vue'
import { useChatStore } from '@/stores'

const route = useRoute()
const router = useRouter()
const chat = useChatStore()
const courseId = computed(() => String(route.params.courseId))
const conversationId = computed(() => String(route.params.conversationId || ''))
const question = ref('')
const messageList = ref<HTMLElement | null>(null)
const feedbackGiven = ref<Record<string, string>>({})

onMounted(load)
watch(conversationId, load)

async function load() {
  if (!chat.conversations.length || chat.conversations[0]?.course_id !== courseId.value) {
    await chat.loadConversations(courseId.value)
  }
  if (conversationId.value) {
    await chat.openConversation(conversationId.value)
    await scrollToBottom()
  }
}

async function newConversation() {
  const conversation = await chat.createConversation(courseId.value)
  await router.push(`/courses/${courseId.value}/chat/${conversation.id}`)
}

async function send() {
  const text = question.value.trim()
  if (!text || chat.streaming) return
  question.value = ''
  await chat.sendQuestion(courseId.value, text)
  if (chat.current) {
    await router.replace(`/courses/${courseId.value}/chat/${chat.current.id}`)
  }
  await scrollToBottom()
}

async function scrollToBottom() {
  await nextTick()
  if (messageList.value) messageList.value.scrollTop = messageList.value.scrollHeight
}

async function feedback(messageId: string, rating: 'helpful' | 'inaccurate') {
  try {
    await api.feedback(messageId, rating)
    feedbackGiven.value[messageId] = rating
    ElMessage.success('反馈已记录')
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.payload.message : '反馈失败')
  }
}

</script>

<template>
  <div class="chat-layout">
    <aside class="chat-sidebar">
      <div class="sidebar-inner">
        <el-button class="new-chat" type="primary" plain :icon="Plus" @click="newConversation">
          新建会话
        </el-button>
        <button
          v-for="conversation in chat.conversations"
          :key="conversation.id"
          :class="['session-item', { active: conversation.id === conversationId }]"
          type="button"
          @click="router.push(`/courses/${courseId}/chat/${conversation.id}`)"
        >
          <ChatDotRound />
          <span>{{ conversation.title }}</span>
        </button>
      </div>
    </aside>

    <section class="chat-main">
      <header class="chat-header">
        <div>
          <strong>{{ chat.current?.title || '课程资料问答' }}</strong>
          <div class="chat-header__hint">回答只引用本课程已就绪资料</div>
        </div>
        <el-button v-if="chat.streaming" text type="danger" :icon="CircleClose" @click="chat.cancelStream">
          停止
        </el-button>
      </header>

      <div ref="messageList" class="message-list">
        <div v-if="!chat.messages.length" class="chat-welcome">
          <div class="chat-welcome__icon">AI</div>
          <h2>从课程资料中找答案</h2>
          <p>例如：“进程和线程有什么区别？” 系统会先检索资料，无法找到依据时会直接拒答。</p>
        </div>
        <div
          v-for="message in chat.messages"
          :key="message.id"
          :class="['message-row', { 'message-row--user': message.role === 'user' }]"
        >
          <div class="message-bubble">
            <MarkdownBlock v-if="message.role === 'assistant'" :content="message.content || '正在生成…'" />
            <span v-else>{{ message.content }}</span>
            <div v-if="message.role === 'assistant' && !message.id.startsWith('assistant-')" class="message-meta">
              <span v-if="message.input_tokens">
                Token {{ message.input_tokens + (message.output_tokens || 0) }}
              </span>
              <el-button
                link
                size="small"
                :type="feedbackGiven[message.id] === 'helpful' ? 'primary' : ''"
                @click="feedback(message.id, 'helpful')"
              >
                有帮助
              </el-button>
              <el-button
                link
                size="small"
                :type="feedbackGiven[message.id] === 'inaccurate' ? 'danger' : ''"
                @click="feedback(message.id, 'inaccurate')"
              >
                不准确
              </el-button>
            </div>
          </div>
        </div>
        <div v-if="chat.retrievalStatus" class="retrieval-state">
          <span class="pulse-dot" />{{ chat.retrievalStatus }}
        </div>
        <el-alert
          v-if="chat.error"
          class="chat-error"
          :title="chat.errorCode === 'INSUFFICIENT_CONTEXT' ? '资料不足' : '回答失败'"
          :description="chat.error"
          :type="chat.errorCode === 'INSUFFICIENT_CONTEXT' ? 'warning' : 'error'"
          show-icon
          :closable="false"
        />
      </div>

      <footer class="chat-composer">
        <el-input
          v-model="question"
          type="textarea"
          :rows="3"
          maxlength="2000"
          resize="none"
          placeholder="针对课程资料提问，Ctrl/⌘ + Enter 发送"
          @keydown.ctrl.enter.prevent="send"
          @keydown.meta.enter.prevent="send"
        />
        <div class="composer-actions">
          <span>回答可能不完整，请核对引用原文</span>
          <el-button
            type="primary"
            :icon="Promotion"
            :loading="chat.streaming"
            :disabled="!question.trim()"
            @click="send"
          >
            发送
          </el-button>
        </div>
      </footer>
    </section>

    <aside class="citation-sidebar">
      <div class="citation-header">
        <strong>本次引用</strong>
        <el-tag size="small" type="info">{{ chat.citations.length }} 条</el-tag>
      </div>
      <CitationCard v-for="citation in chat.citations" :key="citation.chunk_id" :citation="citation" />
      <div v-if="!chat.citations.length" class="citation-empty">
        检索到资料后，这里会展示文件名、页码和原文片段。
      </div>
    </aside>
  </div>
</template>

<style scoped>
.sidebar-inner {
  padding: 14px;
}

.new-chat {
  width: 100%;
  margin-bottom: 12px;
}

.session-item {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  padding: 10px;
  overflow: hidden;
  border: 0;
  border-radius: 9px;
  color: #475569;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.session-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-item svg {
  width: 15px;
  flex: 0 0 auto;
}

.session-item:hover,
.session-item.active {
  color: #1d4ed8;
  background: #eaf2ff;
}

.chat-header__hint,
.citation-empty {
  margin-top: 3px;
  color: #94a3b8;
  font-size: 12px;
}

.chat-welcome {
  max-width: 620px;
  margin: 10vh auto 0;
  text-align: center;
}

.chat-welcome__icon {
  display: grid;
  width: 62px;
  height: 62px;
  margin: 0 auto 16px;
  place-items: center;
  border-radius: 20px;
  color: #fff;
  background: linear-gradient(135deg, #2563eb, #38bdf8);
  font-weight: 850;
}

.chat-welcome h2 {
  margin: 0 0 8px;
}

.chat-welcome p {
  color: #64748b;
  line-height: 1.7;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  color: #94a3b8;
  font-size: 12px;
}

.retrieval-state {
  display: flex;
  align-items: center;
  margin-bottom: 14px;
  color: #2563eb;
  font-size: 13px;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  margin-right: 8px;
  border-radius: 50%;
  background: #3b82f6;
  animation: pulse 1s infinite;
}

.chat-error {
  margin-top: 12px;
}

.composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  color: #94a3b8;
  font-size: 12px;
}

.citation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

@keyframes pulse {
  50% {
    opacity: 0.35;
    transform: scale(1.35);
  }
}
</style>
