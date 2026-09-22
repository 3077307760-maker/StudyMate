<script setup lang="ts">
defineProps<{ title?: string; description?: string }>()
</script>

<template>
  <div class="empty-state soft-card">
    <el-empty :description="description || '暂无数据'">
      <template #image>
        <div class="empty-symbol">S</div>
      </template>
      <strong v-if="title">{{ title }}</strong>
    </el-empty>
  </div>
</template>

<style scoped>
.empty-symbol {
  display: grid;
  width: 84px;
  height: 84px;
  margin: 0 auto;
  place-items: center;
  border-radius: 24px;
  color: #2563eb;
  background: #eff6ff;
  font-size: 34px;
  font-weight: 900;
}
</style>
