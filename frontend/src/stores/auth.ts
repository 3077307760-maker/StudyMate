import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { api, ApiError } from '@/api'
import type { User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('studymate_token') || '')
  const storedUser = localStorage.getItem('studymate_user')
  const user = ref<User | null>(storedUser ? (JSON.parse(storedUser) as User) : null)
  const loading = ref(false)
  const error = ref('')

  const isAuthenticated = computed(() => Boolean(token.value))

  function persist(nextToken: string, nextUser: User) {
    token.value = nextToken
    user.value = nextUser
    localStorage.setItem('studymate_token', nextToken)
    localStorage.setItem('studymate_user', JSON.stringify(nextUser))
  }

  async function login(email: string, password: string) {
    loading.value = true
    error.value = ''
    try {
      const response = await api.login({ email, password })
      persist(response.access_token, response.user)
    } catch (err) {
      error.value = err instanceof ApiError ? err.payload.message : '登录失败，请稍后重试。'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function register(email: string, password: string, displayName: string) {
    loading.value = true
    error.value = ''
    try {
      const response = await api.register({
        email,
        password,
        display_name: displayName,
      })
      persist(response.access_token, response.user)
    } catch (err) {
      error.value = err instanceof ApiError ? err.payload.message : '注册失败，请稍后重试。'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function refreshProfile() {
    if (!token.value) return
    try {
      user.value = await api.me()
      localStorage.setItem('studymate_user', JSON.stringify(user.value))
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('studymate_token')
    localStorage.removeItem('studymate_user')
  }

  return { token, user, loading, error, isAuthenticated, login, register, refreshProfile, logout }
})
