<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Delete, Refresh, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type UploadRequestOptions } from 'element-plus'

import { ApiError } from '@/api'
import EmptyState from '@/components/EmptyState.vue'
import { useCourseStore, useDocumentStore } from '@/stores'
import type { Document } from '@/types'

const route = useRoute()
const router = useRouter()
const courseStore = useCourseStore()
const documentStore = useDocumentStore()
const courseId = computed(() => String(route.params.courseId))
const polling = ref<number | null>(null)
const isOwner = computed(() => courseStore.current?.role === 'owner')

onMounted(async () => {
  try {
    await Promise.all([
      courseStore.loadCourse(courseId.value),
      documentStore.fetchDocuments(courseId.value),
    ])
    startPolling()
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.payload.message : '课程加载失败')
  }
})

onBeforeUnmount(stopPolling)

function startPolling() {
  stopPolling()
  polling.value = window.setInterval(async () => {
    const processing = documentStore.documents.filter((item) =>
      ['pending', 'processing'].includes(item.status),
    )
    if (!processing.length) return
    await Promise.all(processing.map((item) => documentStore.refreshOne(item.id).catch(() => null)))
  }, 1800)
}

function stopPolling() {
  if (polling.value) window.clearInterval(polling.value)
  polling.value = null
}

async function onUpload(options: UploadRequestOptions) {
  try {
    await documentStore.upload(courseId.value, options.file)
    ElMessage.success('文件已上传，正在后台建立索引。')
    startPolling()
  } catch (error) {
    const message = error instanceof ApiError ? error.payload.message : '上传失败'
    ElMessage.error(message)
  }
}

async function removeDocument(document: Document) {
  await ElMessageBox.confirm(`确定删除“${document.original_name}”及其索引吗？`, '删除资料', {
    type: 'warning',
  })
  await documentStore.remove(document.id)
  ElMessage.success('资料已删除')
}

async function reindex(document: Document) {
  await documentStore.reindex(document.id)
  ElMessage.info('已重新提交索引任务')
  startPolling()
}

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div>
        <el-button link @click="router.push('/courses')">← 返回课程列表</el-button>
        <h1 class="page-title">{{ courseStore.current?.name || '课程详情' }}</h1>
        <p class="page-subtitle">
          {{ courseStore.members.length }} 位成员 · 邀请码 {{ courseStore.current?.invite_code }}
        </p>
      </div>
      <el-upload
        v-if="isOwner"
        :show-file-list="false"
        :http-request="onUpload"
        accept=".pdf,.pptx,.md"
      >
        <el-button type="primary" :icon="UploadFilled" :loading="documentStore.uploading">
          上传资料
        </el-button>
      </el-upload>
    </header>

    <section class="stats-row">
      <div class="stat-card soft-card">
        <strong>{{ courseStore.stats?.ready_document_count || 0 }}</strong>
        <span>已就绪资料</span>
      </div>
      <div class="stat-card soft-card">
        <strong>{{ courseStore.stats?.conversation_count || 0 }}</strong>
        <span>问答会话</span>
      </div>
      <div class="stat-card soft-card">
        <strong>{{ courseStore.stats?.quiz_count || 0 }}</strong>
        <span>练习次数</span>
      </div>
      <div class="stat-card soft-card">
        <strong>{{ courseStore.stats?.wrong_item_count || 0 }}</strong>
        <span>待复习错题</span>
      </div>
    </section>

    <section class="content-card soft-card">
      <div class="section-title">
        <div>
          <h2>课程资料</h2>
          <p>支持 PDF、PPTX 和 Markdown，单文件不超过 20 MB。</p>
        </div>
      </div>

      <el-table v-if="documentStore.documents.length" :data="documentStore.documents" stripe>
        <el-table-column prop="original_name" label="文件名" min-width="220" />
        <el-table-column label="大小" width="110">
          <template #default="{ row }">{{ formatSize(row.size_bytes) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="135">
          <template #default="{ row }">
            <span><i :class="['status-dot', `status-dot--${row.status}`]" />{{ row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="分片" width="80" />
        <el-table-column label="错误信息" min-width="180">
          <template #default="{ row }">
            <span class="error-text">{{ row.error_message || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="isOwner" label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'failed'"
              link
              type="primary"
              :icon="Refresh"
              @click="reindex(row)"
            >
              重试
            </el-button>
            <el-button link type="danger" :icon="Delete" @click="removeDocument(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState
        v-else
        :description="isOwner ? '上传第一份课程资料，系统将自动解析并建立检索索引。' : '课程创建者还没有上传资料。'"
      />
    </section>

    <section class="content-card soft-card members-card">
      <h2>课程成员</h2>
      <el-table :data="courseStore.members">
        <el-table-column prop="display_name" label="昵称" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.role === 'owner' ? 'primary' : 'info'">
              {{ row.role === 'owner' ? '创建者' : '成员' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  padding: 18px;
}

.stat-card strong {
  color: #1d4ed8;
  font-size: 27px;
}

.stat-card span {
  margin-top: 4px;
  color: #64748b;
}

.content-card {
  margin-bottom: 20px;
  padding: 22px;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.section-title h2,
.members-card h2 {
  margin: 0;
  font-size: 19px;
}

.section-title p {
  margin: 5px 0 0;
  color: #64748b;
  font-size: 13px;
}

.error-text {
  color: #dc2626;
  font-size: 13px;
}

@media (max-width: 720px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
