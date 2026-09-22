<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Collection, Reading, Refresh, Search, SwitchButton } from '@element-plus/icons-vue'

import { useAuthStore } from '@/stores'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const courseId = computed(() => String(route.params.courseId || ''))
const currentSection = computed(() => String(route.name || ''))

function go(path: string) {
  void router.push(path)
}

function logout() {
  auth.logout()
  void router.push('/login')
}
</script>

<template>
  <header class="topbar">
    <button class="brand" type="button" @click="go('/courses')">StudyMate</button>
    <nav v-if="courseId" class="topbar__nav">
      <button
        :class="{ active: currentSection === 'course' }"
        type="button"
        @click="go(`/courses/${courseId}`)"
      >
        <Collection />课程
      </button>
      <button
        :class="{ active: currentSection === 'chat' }"
        type="button"
        @click="go(`/courses/${courseId}/chat`)"
      >
        <Search />问答
      </button>
      <button
        :class="{ active: currentSection.startsWith('quiz') }"
        type="button"
        @click="go(`/courses/${courseId}/quiz`)"
      >
        <Reading />练习
      </button>
      <button
        :class="{ active: currentSection === 'wrong-book' }"
        type="button"
        @click="go(`/courses/${courseId}/wrong-book`)"
      >
        错题本
      </button>
      <button
        :class="{ active: currentSection === 'review' }"
        type="button"
        @click="go(`/courses/${courseId}/review`)"
      >
        <Refresh />周复习
      </button>
    </nav>
    <el-dropdown>
      <button class="user-chip" type="button">{{ auth.user?.display_name || '用户' }}</button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item @click="logout">
            <el-icon><SwitchButton /></el-icon>退出登录
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </header>
</template>

<style scoped>
.topbar {
  position: fixed;
  z-index: 30;
  top: 0;
  right: 0;
  left: 0;
  display: flex;
  height: 64px;
  align-items: center;
  gap: 22px;
  padding: 0 22px;
  border-bottom: 1px solid #e6ebf2;
  background: rgb(255 255 255 / 94%);
  backdrop-filter: blur(14px);
}

.brand {
  border: 0;
  color: #2563eb;
  background: none;
  font-size: 21px;
  font-weight: 850;
  cursor: pointer;
}

.topbar__nav {
  display: flex;
  min-width: 0;
  flex: 1;
  gap: 4px;
  overflow-x: auto;
}

.topbar__nav button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 11px;
  border: 0;
  border-radius: 9px;
  color: #475569;
  background: transparent;
  white-space: nowrap;
  cursor: pointer;
}

.topbar__nav button:hover,
.topbar__nav button.active {
  color: #1d4ed8;
  background: #eff6ff;
}

.topbar__nav svg {
  width: 16px;
  height: 16px;
}

.user-chip {
  max-width: 160px;
  overflow: hidden;
  padding: 8px 12px;
  border: 1px solid #dbe3ee;
  border-radius: 999px;
  color: #334155;
  background: #fff;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}
</style>
