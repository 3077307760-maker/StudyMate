<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { ApiError } from '@/api'
import EmptyState from '@/components/EmptyState.vue'
import { useCourseStore } from '@/stores'

const store = useCourseStore()
const router = useRouter()
const createVisible = ref(false)
const joinVisible = ref(false)
const createForm = reactive({ name: '' })
const joinForm = reactive({ invite_code: '' })

onMounted(async () => {
  try {
    await store.fetchCourses()
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.payload.message : '课程加载失败')
  }
})

async function createCourse() {
  try {
    const course = await store.createCourse(createForm.name)
    createVisible.value = false
    createForm.name = ''
    await router.push(`/courses/${course.id}`)
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.payload.message : '创建失败')
  }
}

async function joinCourse() {
  try {
    const course = await store.joinCourse(joinForm.invite_code)
    joinVisible.value = false
    joinForm.invite_code = ''
    await router.push(`/courses/${course.id}`)
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.payload.message : '加入失败')
  }
}
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">我的课程</h1>
        <p class="page-subtitle">上传课程资料，与同学共享有依据的问答和复习记录。</p>
      </div>
      <div class="actions">
        <el-button :icon="Search" @click="joinVisible = true">邀请码加入</el-button>
        <el-button type="primary" :icon="Plus" @click="createVisible = true">创建课程</el-button>
      </div>
    </header>

    <div v-loading="store.loading">
      <div v-if="store.courses.length" class="card-grid">
        <button
          v-for="course in store.courses"
          :key="course.id"
          class="course-card soft-card"
          type="button"
          @click="router.push(`/courses/${course.id}`)"
        >
          <div class="course-card__top">
            <span class="course-avatar">{{ course.name.slice(0, 1) }}</span>
            <el-tag size="small" :type="course.role === 'owner' ? 'primary' : 'info'">
              {{ course.role === 'owner' ? '创建者' : '成员' }}
            </el-tag>
          </div>
          <h2>{{ course.name }}</h2>
          <div class="course-card__footer">
            <span>邀请码 {{ course.invite_code }}</span>
            <span>进入课程 →</span>
          </div>
        </button>
      </div>
      <EmptyState v-else description="还没有课程，先创建一门课程或输入邀请码加入。" />
    </div>

    <el-dialog v-model="createVisible" title="创建课程" width="420px">
      <el-input v-model="createForm.name" maxlength="100" placeholder="例如：操作系统" @keyup.enter="createCourse" />
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!createForm.name.trim()" @click="createCourse">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="joinVisible" title="通过邀请码加入" width="420px">
      <el-input
        v-model="joinForm.invite_code"
        maxlength="6"
        placeholder="6 位邀请码"
        @keyup.enter="joinCourse"
      />
      <template #footer>
        <el-button @click="joinVisible = false">取消</el-button>
        <el-button type="primary" :disabled="joinForm.invite_code.length !== 6" @click="joinCourse">
          加入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>


<style scoped>
.actions {
  display: flex;
  gap: 10px;
}

.course-card {
  padding: 22px;
  border: 1px solid #e5eaf1;
  text-align: left;
  cursor: pointer;
  transition: 180ms ease;
}

.course-card:hover {
  border-color: #bfdbfe;
  box-shadow: 0 16px 42px rgb(37 99 235 / 13%);
  transform: translateY(-3px);
}

.course-card__top,
.course-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.course-avatar {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border-radius: 13px;
  color: #1d4ed8;
  background: #dbeafe;
  font-size: 20px;
  font-weight: 800;
}

.course-card h2 {
  margin: 22px 0 24px;
  font-size: 21px;
}

.course-card__footer {
  color: #64748b;
  font-size: 13px;
}
</style>
