import { ref } from 'vue'
import { defineStore } from 'pinia'

import { api, ApiError } from '@/api'
import type { Course, CourseStats, Member } from '@/types'

export const useCourseStore = defineStore('course', () => {
  const courses = ref<Course[]>([])
  const current = ref<Course | null>(null)
  const members = ref<Member[]>([])
  const stats = ref<CourseStats | null>(null)
  const loading = ref(false)
  const error = ref('')

  async function fetchCourses() {
    loading.value = true
    try {
      courses.value = await api.courses()
    } finally {
      loading.value = false
    }
  }

  async function createCourse(name: string) {
    const course = await api.createCourse(name)
    courses.value.unshift(course)
    return course
  }

  async function joinCourse(inviteCode: string) {
    const course = await api.joinCourse(inviteCode)
    const index = courses.value.findIndex((item) => item.id === course.id)
    if (index >= 0) courses.value[index] = course
    else courses.value.unshift(course)
    return course
  }

  async function loadCourse(courseId: string) {
    loading.value = true
    error.value = ''
    try {
      const [course, memberList, summary] = await Promise.all([
        api.course(courseId),
        api.members(courseId),
        api.courseStats(courseId),
      ])
      current.value = course
      members.value = memberList
      stats.value = summary
    } catch (err) {
      error.value = err instanceof ApiError ? err.payload.message : '课程加载失败。'
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearCurrent() {
    current.value = null
    members.value = []
    stats.value = null
  }

  return {
    courses,
    current,
    members,
    stats,
    loading,
    error,
    fetchCourses,
    createCourse,
    joinCourse,
    loadCourse,
    clearCurrent,
  }
})
