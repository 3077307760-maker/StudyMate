<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import { useAuthStore } from '@/stores'

const auth = useAuthStore()
const router = useRouter()

onMounted(() => {
  window.addEventListener('studymate:auth-required', () => {
    auth.logout()
    void router.push('/login')
  })
})
</script>

<template>
  <div class="app-shell">
    <AppHeader v-if="auth.isAuthenticated" />
    <main :class="['app-main', { 'app-main--auth': auth.isAuthenticated }]">
      <RouterView />
    </main>
  </div>
</template>
