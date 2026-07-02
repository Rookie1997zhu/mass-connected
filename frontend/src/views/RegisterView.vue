<script setup>
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import PageShell from '../components/PageShell.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const form = ref({ email: '', password: '', name: '', phone: '' })
const error = ref('')

const onSubmit = async () => {
  error.value = ''
  try {
    await auth.register(form.value)
    router.push(route.query.redirect || '/my/rfqs')
  } catch (e) {
    error.value = e.message || 'Register failed'
  }
}
</script>

<template>
  <PageShell centered>
    <h1 class="page-title" style="text-align: center">{{ $t('nav.register') }}</h1>
    <form class="page-form" @submit.prevent="onSubmit">
      <label class="page-form-field">
        <span class="page-form-label">{{ $t('account.name') }}</span>
        <input v-model="form.name" autocomplete="name" required />
      </label>
      <label class="page-form-field">
        <span class="page-form-label">{{ $t('account.email') }}</span>
        <input v-model="form.email" type="email" autocomplete="email" required />
      </label>
      <label class="page-form-field">
        <span class="page-form-label">{{ $t('account.phone') }}</span>
        <input v-model="form.phone" type="tel" autocomplete="tel" />
      </label>
      <label class="page-form-field">
        <span class="page-form-label">{{ $t('account.password') }}</span>
        <input v-model="form.password" type="password" autocomplete="new-password" required />
      </label>
      <button type="submit" class="btn btn-primary btn-submit">{{ $t('nav.register') }}</button>
    </form>
    <p v-if="error" class="page-message page-message--error">{{ error }}</p>
    <p class="page-message">
      <RouterLink to="/login">{{ $t('nav.login') }}</RouterLink>
    </p>
  </PageShell>
</template>

<style scoped>
.page-message a {
  color: var(--color-steel);
  font-weight: 600;
  text-decoration: none;
}
.page-message a:hover {
  color: var(--color-steel-light);
}
</style>
