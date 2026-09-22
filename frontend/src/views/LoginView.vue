<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'

import { useAuthStore } from '@/stores'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const form = reactive({ email: '', password: '' })
const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [{ required: true, min: 8, message: '密码至少 8 位', trigger: 'blur' }],
}

async function submit() {
  await formRef.value?.validate()
  await auth.login(form.email, form.password)
  await router.push(String(route.query.redirect || '/courses'))
}
</script>

<template>
  <div class="auth-page">
    <section class="auth-card">
      <h1 class="auth-brand">StudyMate</h1>
      <p class="page-subtitle">用课程资料获得有依据的回答，并形成练习复习闭环。</p>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" autocomplete="email" placeholder="student@example.com" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            autocomplete="current-password"
            placeholder="至少 8 位"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-alert v-if="auth.error" :title="auth.error" type="error" :closable="false" />
        <el-button class="submit-button" type="primary" :loading="auth.loading" @click="submit">
          登录
        </el-button>
      </el-form>
      <div class="auth-switch">
        还没有账号？
        <RouterLink to="/register">立即注册</RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.submit-button {
  width: 100%;
  margin-top: 18px;
}
</style>
