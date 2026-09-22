<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Check, RefreshRight } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { ApiError } from '@/api'
import { useCourseStore, useDocumentStore, useQuizStore } from '@/stores'

const route = useRoute()
const router = useRouter()
const courseStore = useCourseStore()
const documentStore = useDocumentStore()
const quizStore = useQuizStore()
const quizId = computed(() => String(route.params.quizId || ''))
const courseId = computed(() => String(route.params.courseId))
const generatingForm = reactive({
  document_ids: [] as string[],
  question_count: 5 as 5 | 10,
  question_types: ['single_choice', 'short_answer'] as Array<'single_choice' | 'short_answer'>,
  chapter: '',
})
const resultMap = computed(
  () => new Map(quizStore.result?.answers.map((answer) => [answer.question_id, answer]) || []),
)

onMounted(async () => {
  if (!quizId.value) {
    await Promise.all([
      courseStore.loadCourse(courseId.value),
      documentStore.fetchDocuments(courseId.value),
    ])
    generatingForm.document_ids = documentStore.documents
      .filter((document) => document.status === 'ready')
      .slice(0, 1)
      .map((document) => document.id)
  } else {
    await quizStore.load(quizId.value)
  }
})

async function generate() {
  try {
    const quiz = await quizStore.generate(courseId.value, {
      document_ids: generatingForm.document_ids,
      question_count: generatingForm.question_count,
      question_types: generatingForm.question_types,
      chapter: generatingForm.chapter || undefined,
    })
    await router.push(`/courses/${courseId.value}/quiz/${quiz.id}`)
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.payload.message : '练习生成失败')
  }
}

async function submit() {
  const unanswered = (quizStore.current?.questions.length || 0) - quizStore.answeredCount
  if (unanswered > 0) {
    await ElMessageBox.confirm(`还有 ${unanswered} 题未作答，仍要提交吗？`, '确认提交', {
      type: 'warning',
    })
  }
  try {
    await quizStore.submit()
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.payload.message : '提交失败')
  }
}

function optionLetter(index: number) {
  return String.fromCharCode(65 + index)
}

function isCorrect(questionId: string) {
  return resultMap.value.get(questionId)?.is_correct
}

function resetQuiz() {
  quizStore.clearCurrent()
  void router.push(`/courses/${courseId.value}/quiz`)
}
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div>
        <el-button link @click="router.push(`/courses/${courseId}`)">← 返回课程</el-button>
        <h1 class="page-title">{{ quizStore.current?.title || '生成课程练习' }}</h1>
        <p class="page-subtitle">题目与解析必须来自所选课程资料。</p>
      </div>
      <el-button v-if="quizStore.result" :icon="RefreshRight" @click="resetQuiz">再生成一套</el-button>
    </header>

    <el-alert
      v-if="quizStore.error && !quizStore.current"
      :title="quizStore.error"
      type="error"
      :closable="false"
      show-icon
    />

    <section v-if="!quizId" class="generator-card soft-card">
      <h2>选择生成参数</h2>
      <el-form label-position="top">
        <el-form-item label="资料">
          <el-checkbox-group v-model="generatingForm.document_ids">
            <el-checkbox
              v-for="document in documentStore.documents.filter((item) => item.status === 'ready')"
              :key="document.id"
              :value="document.id"
            >
              {{ document.original_name }}
            </el-checkbox>
          </el-checkbox-group>
          <el-text v-if="!documentStore.documents.some((item) => item.status === 'ready')" type="warning">
            当前没有已就绪资料，请先上传并等待索引完成。
          </el-text>
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="章节 / 知识点">
            <el-input v-model="generatingForm.chapter" maxlength="100" placeholder="留空则覆盖整份资料" />
          </el-form-item>
          <el-form-item label="题量">
            <el-radio-group v-model="generatingForm.question_count">
              <el-radio-button :value="5">5 题</el-radio-button>
              <el-radio-button :value="10">10 题</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="题型">
            <el-checkbox-group v-model="generatingForm.question_types">
              <el-checkbox value="single_choice">单选题</el-checkbox>
              <el-checkbox value="short_answer">简答题</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
        </div>
        <el-button
          type="primary"
          size="large"
          :loading="quizStore.generating"
          :disabled="!generatingForm.document_ids.length || !generatingForm.question_types.length"
          @click="generate"
        >
          生成练习
        </el-button>
      </el-form>
    </section>

    <section v-else-if="quizStore.current" class="quiz-shell">
      <div>
        <article
          v-for="question in quizStore.current.questions"
          :key="question.id"
          class="question-card"
        >
          <div class="question-head">
            <strong>{{ question.order_no }}.</strong>
            <el-tag size="small" type="info">
              {{ question.type === 'single_choice' ? '单选题' : '简答题' }}
            </el-tag>
            <el-tag
              v-if="quizStore.result"
              size="small"
              :type="isCorrect(question.id) ? 'success' : isCorrect(question.id) === false ? 'danger' : 'warning'"
            >
              {{ isCorrect(question.id) ? '正确' : isCorrect(question.id) === false ? '错误' : '待自评' }}
            </el-tag>
          </div>
          <p class="question-card__stem">{{ question.stem }}</p>

          <el-radio-group
            v-if="question.options && !quizStore.result"
            v-model="quizStore.answers[question.id]"
            @change="(value: string | number | boolean | undefined) => quizStore.setAnswer(question.id, String(value ?? ''))"
          >
            <el-radio
              v-for="(option, index) in question.options"
              :key="option"
              :value="optionLetter(index)"
              class="option-row"
            >
              <strong>{{ optionLetter(index) }}.</strong> {{ option }}
            </el-radio>
          </el-radio-group>
          <el-input
            v-else-if="!quizStore.result"
            v-model="quizStore.answers[question.id]"
            type="textarea"
            :rows="4"
            placeholder="请输入你的回答"
            @input="quizStore.setAnswer(question.id, String($event))"
          />
          <div v-else class="submitted-answer">
            <div><strong>你的答案：</strong>{{ resultMap.get(question.id)?.user_answer || '未作答' }}</div>
            <div><strong>参考答案：</strong>{{ resultMap.get(question.id)?.correct_answer }}</div>
            <div class="answer-explanation">
              <strong>解析：</strong>{{ resultMap.get(question.id)?.explanation }}
            </div>
          </div>
        </article>
      </div>

      <aside class="quiz-aside soft-card">
        <h3>答题进度</h3>
        <el-progress
          type="circle"
          :percentage="Math.round((quizStore.answeredCount / quizStore.current.questions.length) * 100)"
        />
        <p>{{ quizStore.answeredCount }} / {{ quizStore.current.questions.length }} 已作答</p>
        <el-button
          v-if="!quizStore.result"
          type="primary"
          size="large"
          :loading="quizStore.submitting"
          @click="submit"
        >
          <el-icon><Check /></el-icon>提交练习
        </el-button>
        <template v-else>
          <div class="score">{{ quizStore.result.score }}<span>分</span></div>
          <el-button type="warning" @click="router.push(`/courses/${courseId}/wrong-book`)">
            查看错题本
          </el-button>
        </template>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.generator-card {
  max-width: 820px;
  padding: 26px;
}

.generator-card h2 {
  margin-top: 0;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 20px;
  align-items: end;
}

.question-head {
  display: flex;
  align-items: center;
  gap: 9px;
}

.option-row {
  display: flex;
  width: 100%;
  height: auto;
  margin: 8px 0;
  padding: 11px 13px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  white-space: normal;
}

.submitted-answer {
  display: grid;
  gap: 10px;
  line-height: 1.7;
}

.quiz-aside {
  position: sticky;
  top: 84px;
  align-self: start;
  padding: 22px;
  text-align: center;
}

.quiz-aside p {
  color: #64748b;
}

.quiz-aside .el-button {
  width: 100%;
}

.score {
  margin: 14px 0;
  color: #16a34a;
  font-size: 42px;
  font-weight: 850;
}

.score span {
  margin-left: 4px;
  font-size: 16px;
}

@media (max-width: 760px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
