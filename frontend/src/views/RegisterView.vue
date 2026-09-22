<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'

import { useAuthStore } from '@/stores'

const auth = useAuthStore()
const router = useRouter()
const formRef = ref<FormInstance>()
const form = reactive({ display_name: '', email: '', password: '' })
const rules: FormRules = {
  display_name: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [{ required: true, min: 8, message: '密码至少 8 位', trigger: 'blur' }],
}

async function submit() {
  await formRef.value?.validate()
  await auth.register(form.email, form.password, form.display_name)
  await router.push('/courses')
}
</script>

<template>
  <div class="auth-page">
    <section class="auth-card">
      <h1 class="auth-brand">创建账号</h1>
      <p class="page-subtitle">注册后即可创建课程，或通过邀请码加入同学课程。</p>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
        <el-form-item label="昵称" prop="display_name">
          <el-input v-model="form.display_name" maxlength="50" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" autocomplete="email" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password autocomplete="new-password" />
        </el-form-item>
        <el-alert v-if="auth.error" :title="auth.error" type="error" :closable="false" />
        <el-button class="submit-button" type="primary" :loading="auth.loading" @click="submit">
          注册并登录
        </el-button>
      </el-form>
      <div class="auth-switch">
        已有账号？
        <RouterLink to="/login">返回登录</RouterLink>
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
