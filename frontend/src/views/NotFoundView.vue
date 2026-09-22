<template>
  <div class="auth-page">
    <el-result icon="warning" title="404" sub-title="页面不存在或链接已失效">
      <template #extra>
        <el-button type="primary" @click="$router.push('/courses')">返回课程</el-button>
      </template>
    </el-result>
  </div>
</template>
