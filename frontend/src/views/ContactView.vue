<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import PageShell from '../components/PageShell.vue'
import { submitInquiry } from '../api'

const { t } = useI18n()
const form = ref({ name: '', company: '', email: '', phone: '', product_interest: '', message: '' })
const message = ref('')
const loading = ref(false)

const onSubmit = async () => {
  loading.value = true
  message.value = ''
  try {
    await submitInquiry(form.value)
    message.value = 'success'
    form.value = { name: '', company: '', email: '', phone: '', product_interest: '', message: '' }
  } catch (e) {
    message.value = e.message || t('contact.submitFailed')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <PageShell centered wide>
    <h1 class="page-title" style="text-align: center">{{ t('nav.contact') }}</h1>
    <form class="page-form" @submit.prevent="onSubmit">
      <label class="page-form-field">
        <span class="page-form-label">{{ t('contact.name') }}</span>
        <input v-model="form.name" required />
      </label>
      <label class="page-form-field">
        <span class="page-form-label">{{ t('contact.company') }}</span>
        <input v-model="form.company" />
      </label>
      <label class="page-form-field">
        <span class="page-form-label">{{ t('contact.email') }}</span>
        <input v-model="form.email" type="email" required />
      </label>
      <label class="page-form-field">
        <span class="page-form-label">{{ t('contact.phone') }}</span>
        <input v-model="form.phone" />
      </label>
      <label class="page-form-field">
        <span class="page-form-label">{{ t('contact.productInterest') }}</span>
        <input v-model="form.product_interest" />
      </label>
      <label class="page-form-field">
        <span class="page-form-label">{{ t('contact.message') }}</span>
        <textarea v-model="form.message" rows="4" required />
      </label>
      <button type="submit" class="btn btn-primary btn-submit" :disabled="loading">
        {{ t('common.submit') }}
      </button>
    </form>
    <p v-if="message === 'success'" class="page-message page-message--success">{{ t('contact.submitSuccess') }}</p>
    <p v-else-if="message" class="page-message page-message--error">{{ message }}</p>
  </PageShell>
</template>
