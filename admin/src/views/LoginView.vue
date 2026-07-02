<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const { t, locale } = useI18n()
const auth = useAuthStore()
const router = useRouter()
const form = ref({ email: '', password: '' })
const error = ref('')

const setLocale = (value) => {
  locale.value = value
  localStorage.setItem('admin_locale', value)
  document.title = t('app.title')
}

const onSubmit = async () => {
  error.value = ''
  try {
    await auth.login(form.value)
    router.push('/')
  } catch (e) {
    error.value = e.message || t('common.loginFailed')
  }
}
</script>

<template>
  <div class="login-page">
    <el-card class="card">
      <div class="card-header">
        <h2>{{ t('login.title') }}</h2>
        <el-select :model-value="locale" class="locale-select" @change="setLocale">
          <el-option label="한국어" value="ko" />
          <el-option label="中文" value="zh" />
          <el-option label="English" value="en" />
        </el-select>
      </div>
      <el-form @submit.prevent="onSubmit">
        <el-form-item :label="t('common.email')"><el-input v-model="form.email" /></el-form-item>
        <el-form-item :label="t('common.password')"><el-input v-model="form.password" type="password" show-password /></el-form-item>
        <el-button type="primary" native-type="submit">{{ t('common.login') }}</el-button>
      </el-form>
      <p v-if="error" class="error">{{ error }}</p>
    </el-card>
  </div>
</template>

<style scoped>
.login-page { min-height: 100vh; display: grid; place-items: center; background: #f3f4f6; }
.card { width: 420px; }
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-bottom: 1rem; }
.card-header h2 { margin: 0; }
.locale-select { width: 120px; }
.error { color: #dc2626; margin-top: 1rem; }
</style>
