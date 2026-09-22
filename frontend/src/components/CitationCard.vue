<script setup lang="ts">
import type { Citation } from '@/types'

defineProps<{ citation: Citation }>()

function location(citation: Citation) {
  if (citation.page) return `第 ${citation.page} 页`
  if (citation.slide) return `第 ${citation.slide} 张幻灯片`
  if (citation.section) return citation.section
  return '正文片段'
}
</script>

<template>
  <article class="citation-card">
    <div class="citation-card__head">
      <span>[{{ citation.index }}] {{ citation.file_name }}</span>
      <el-tag size="small" type="info">{{ location(citation) }}</el-tag>
    </div>
    <div class="citation-card__snippet">{{ citation.snippet }}</div>
  </article>
</template>
