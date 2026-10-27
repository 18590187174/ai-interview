<template>
  <div class="auth-page">
    <el-card class="auth-card" shadow="always">
      <template #header>
        <h2 class="title">登录</h2>
      </template>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="you@example.com" autocomplete="email" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            autocomplete="current-password"
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-button type="primary" class="submit" :loading="loading" @click="onSubmit">
          登录
        </el-button>
      </el-form>

      <div class="footer">
        还没有账号？
        <router-link :to="{ name: 'register' }">立即注册</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { RequestError } from '@/api/http'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const store = useUserStore()

const formRef = ref()
const loading = ref(false)
const form = reactive({ email: '', password: '' })

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: ['blur', 'change'] },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
  ],
}

async function onSubmit(): Promise<void> {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  loading.value = true
  try {
    await store.login({ email: form.email.trim(), password: form.password })
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.push(redirect)
  } catch (error) {
    const message = error instanceof RequestError ? error.message : '登录失败，请稍后重试'
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.auth-card {
  width: 400px;
}

.title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.submit {
  width: 100%;
}

.footer {
  margin-top: 16px;
  font-size: 13px;
  color: var(--text-secondary);
  text-align: center;
}
</style>
