<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Calendar, Clock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { api, ApiError } from '@/api'
import EmptyState from '@/components/EmptyState.vue'
import { useWrongBookStore } from '@/stores'

const route = useRoute()
const router = useRouter()
const store = useWrongBookStore()
const courseId = computed(() => String(route.params.courseId))

onMounted(async () => {
  await store.loadPlan(courseId.value)
})

async function complete(wrongItemId: string) {
  try {
    await api.completeReviewItem(wrongItemId)
    await store.loadPlan(courseId.value)
    ElMessage.success('本周复习任务已完成')
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.payload.message : '更新失败')
  }
}

function practice(wrongItemId: string) {
  void router.push({ path: `/courses/${courseId.value}/wrong-book`, query: { focus: wrongItemId } })
}
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div>
        <el-button link @click="router.push(`/courses/${courseId}`)">← 返回课程</el-button>
        <h1 class="page-title">每周复习</h1>
        <p class="page-subtitle">按错误次数排序的规则清单，不依赖模型自由生成。</p>
      </div>
      <div class="progress-pill soft-card">
        <Calendar />
        {{ store.plan?.week_start || '本周' }} · {{ store.plan?.completed || 0 }}/{{ store.plan?.total || 0 }}
      </div>
    </header>

    <div v-if="store.plan?.tasks.length" class="review-list">
      <article
        v-for="task in store.plan.tasks"
        :key="task.wrong_item_id"
        :class="['review-card', 'soft-card', { completed: task.completed }]"
      >
        <div class="priority" :data-level="task.priority">P{{ task.priority }}</div>
        <div class="review-card__body">
          <div class="review-meta">
            <el-tag size="small">{{ task.knowledge_tag }}</el-tag>
            <span><Clock />错误 {{ task.wrong_count }} 次</span>
          </div>
          <h2>{{ task.question.stem }}</h2>
        </div>
        <div class="review-actions">
          <el-button type="primary" plain @click="practice(task.wrong_item_id)">开始重练</el-button>
          <el-button v-if="!task.completed" @click="complete(task.wrong_item_id)">标记完成</el-button>
          <el-tag v-else type="success">已完成</el-tag>
        </div>
      </article>
    </div>
    <EmptyState v-else description="本周没有待复习错题，继续保持。" />
  </div>
</template>

<style scoped>
.progress-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  color: #1d4ed8;
}

.progress-pill svg {
  width: 18px;
}

.review-list {
  display: grid;
  gap: 14px;
}

.review-card {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) auto;
  align-items: center;
  gap: 18px;
  padding: 20px;
}

.review-card.completed {
  opacity: 0.62;
}

.priority {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  border-radius: 14px;
  color: #92400e;
  background: #fef3c7;
  font-weight: 800;
}

.priority[data-level='3'] {
  color: #991b1b;
  background: #fee2e2;
}

.review-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #64748b;
  font-size: 13px;
}

.review-meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.review-meta svg {
  width: 14px;
}

.review-card h2 {
  margin: 10px 0 0;
  font-size: 17px;
  line-height: 1.6;
}

.review-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

@media (max-width: 760px) {
  .review-card {
    grid-template-columns: 46px 1fr;
  }

  .review-actions {
    grid-column: 1 / -1;
    justify-content: flex-end;
  }
}
</style>
