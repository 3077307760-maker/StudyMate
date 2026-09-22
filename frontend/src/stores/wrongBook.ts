import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'
import type { ReviewPlan, WrongItem } from '@/types'

export const useWrongBookStore = defineStore('wrongBook', () => {
  const items = ref<WrongItem[]>([])
  const plan = ref<ReviewPlan | null>(null)
  const loading = ref(false)
  const filter = ref('')
  const showMastered = ref(false)

  const filteredItems = computed(() =>
    items.value.filter((item) => {
      if (!showMastered.value && item.mastered) return false
      if (filter.value && !item.knowledge_tag.includes(filter.value)) return false
      return true
    }),
  )

  async function loadItems(courseId: string) {
    loading.value = true
    try {
      items.value = await api.wrongItems(courseId)
    } finally {
      loading.value = false
    }
  }

  async function loadPlan(courseId: string) {
    loading.value = true
    try {
      plan.value = await api.reviewPlan(courseId)
    } finally {
      loading.value = false
    }
  }

  return { items, plan, loading, filter, showMastered, filteredItems, loadItems, loadPlan }
})
