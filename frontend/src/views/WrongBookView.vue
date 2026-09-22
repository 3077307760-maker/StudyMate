<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { api, ApiError } from '@/api'
import type { AnswerResult, Question, WrongItem } from '@/types'
import { useWrongBookStore } from '@/stores'

const route = useRoute()
const router = useRouter()
const store = useWrongBookStore()
const courseId = computed(() => String(route.params.courseId))
const practiceVisible = ref(false)
const practiceQuestion = ref<Question | null>(null)
const practiceWrongId = ref('')
const practiceAnswer = ref('')
const practiceResult = ref<AnswerResult | null>(null)
const practicing = ref(false)

onMounted(async () => {
  await store.loadItems(courseId.value)
  const focus = String(route.query.focus || '')
  if (focus) await openPractice(focus)
})

async function openPractice(wrongItemId: string) {
  try {
    const response = await api.practiceWrongItem(wrongItemId)
    practiceWrongId.value = wrongItemId
    practiceQuestion.value = response.question
    practiceAnswer.value = ''
    practiceResult.value = null
    practiceVisible.value = true
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.payload.message : '错题加载失败')
  }
}

async function submitPractice() {
  practicing.value = true
  try {
    practiceResult.value = await api.submitWrongPractice(practiceWrongId.value, practiceAnswer.value)
    await store.loadItems(courseId.value)
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.payload.message : '提交失败')
  } finally {
    practicing.value = false
  }
}

function openOriginal(item: WrongItem) {
  void router.push(`/courses/${courseId.value}/quiz/${item.quiz_id}`)
}
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div>
        <el-button link @click="router.push(`/courses/${courseId}`)">← 返回课程</el-button>
        <h1 class="page-title">错题本</h1>
        <p class="page-subtitle">按知识点、错误次数和最近错误时间整理，连续答对两次会自动掌握。</p>
      </div>
      <el-input
        v-model="store.filter"
        :prefix-icon="Search"
        placeholder="筛选知识点"
        clearable
        style="width: 220px"
      />
    </header>

    <div class="toolbar soft-card">
      <el-switch v-model="store.showMastered" active-text="显示已掌握" />
      <span>当前 {{ store.filteredItems.length }} 条</span>
    </div>

    <el-table v-if="store.filteredItems.length" :data="store.filteredItems" stripe class="table-card">
      <el-table-column prop="knowledge_tag" label="知识点" min-width="130" />
      <el-table-column prop="question.stem" label="题目" min-width="300" />
      <el-table-column prop="wrong_count" label="错误次数" width="100" sortable />
      <el-table-column label="连续答对" width="100">
        <template #default="{ row }">{{ row.consecutive_correct }} / 2</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.mastered ? 'success' : 'warning'">
            {{ row.mastered ? '已掌握' : '待复习' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="190" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" :icon="Refresh" @click="openPractice(row.id)">立即重练</el-button>
          <el-button link @click="openOriginal(row)">原练习</el-button>
        </template>
      </el-table-column>
    </el-table>
    <EmptyState v-else description="还没有错题，完成练习后错误题目会自动进入这里。" />

    <el-dialog v-model="practiceVisible" title="错题重练" width="640px">
      <template v-if="practiceQuestion">
        <el-tag size="small" type="info">{{ practiceQuestion.knowledge_tags.join(' · ') }}</el-tag>
        <h3>{{ practiceQuestion.stem }}</h3>
        <el-radio-group v-if="practiceQuestion.options" v-model="practiceAnswer" :disabled="Boolean(practiceResult)">
          <el-radio
            v-for="(option, index) in practiceQuestion.options"
            :key="option"
            :value="String.fromCharCode(65 + index)"
            class="option-row"
          >
            <strong>{{ String.fromCharCode(65 + index) }}.</strong> {{ option }}
          </el-radio>
        </el-radio-group>
        <el-input
          v-else
          v-model="practiceAnswer"
          type="textarea"
          :rows="4"
          :disabled="Boolean(practiceResult)"
        />
        <div v-if="practiceResult" class="answer-explanation">
          <p>
            <strong>结果：</strong>
            {{ practiceResult.is_correct ? '回答正确' : practiceResult.is_correct === false ? '回答错误' : '请结合参考答案自评' }}
          </p>
          <p><strong>参考答案：</strong>{{ practiceResult.correct_answer }}</p>
          <p><strong>解析：</strong>{{ practiceResult.explanation }}</p>
        </div>
      </template>
      <template #footer>
        <el-button @click="practiceVisible = false">关闭</el-button>
        <el-button
          v-if="!practiceResult"
          type="primary"
          :loading="practicing"
          :disabled="!practiceAnswer.trim()"
          @click="submitPractice"
        >
          提交重练
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding: 14px 18px;
}

.table-card {
  overflow: hidden;
  border-radius: 14px;
}

.option-row {
  display: flex;
  width: 100%;
  height: auto;
  margin: 8px 0;
  padding: 10px;
  white-space: normal;
}
</style>
