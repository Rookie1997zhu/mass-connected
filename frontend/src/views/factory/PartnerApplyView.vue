<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import PageShell from '../../components/PageShell.vue'
import { fetchServiceCategories } from '../../api'
import { useAuthStore } from '../../stores/auth'

const { t, locale } = useI18n()
const router = useRouter()
const auth = useAuthStore()

const categories = ref([])
const form = ref({
  email: '',
  password: '',
  name: '',
  phone: '',
  company_name: '',
  region: '',
  intro: '',
  contact_phone: '',
  process_ids: [],
})
const error = ref('')
const success = ref('')
const submitting = ref(false)

const pick = (field) => {
  if (!field || typeof field !== 'object') return field || ''
  return field[locale.value] || field.ko || field.en || Object.values(field)[0] || ''
}

onMounted(async () => {
  const res = await fetchServiceCategories()
  categories.value = res.data.items || []
})

const toggleProcess = (id) => {
  const idx = form.value.process_ids.indexOf(id)
  if (idx >= 0) form.value.process_ids.splice(idx, 1)
  else form.value.process_ids.push(id)
}

const submit = async () => {
  error.value = ''
  success.value = ''
  submitting.value = true
  try {
    await auth.registerFactory(form.value)
    success.value = t('partners.submitSuccess')
    setTimeout(() => router.push('/login'), 2000)
  } catch (e) {
    error.value = e.message || t('partners.submitFailed')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ t('partners.title') }}</h1>
    <p class="page-lead">{{ t('partners.desc') }}</p>

    <div class="partner-grid">
      <section class="partner-info card">
        <h2>{{ t('partners.benefitsTitle') }}</h2>
        <ul>
          <li>{{ t('partners.benefit1') }}</li>
          <li>{{ t('partners.benefit2') }}</li>
          <li>{{ t('partners.benefit3') }}</li>
        </ul>
      </section>

      <form class="partner-form card" @submit.prevent="submit">
        <h2>{{ t('partners.formTitle') }}</h2>
        <p v-if="error" class="page-message page-message--error">{{ error }}</p>
        <p v-if="success" class="page-message page-message--success">{{ success }}</p>

        <label>{{ t('account.email') }}<input v-model="form.email" type="email" required /></label>
        <label>{{ t('account.password') }}<input v-model="form.password" type="password" required minlength="8" /></label>
        <label>{{ t('account.name') }}<input v-model="form.name" required /></label>
        <label>{{ t('partners.companyName') }}<input v-model="form.company_name" required /></label>
        <label>{{ t('partners.region') }}<input v-model="form.region" /></label>
        <label>{{ t('account.phone') }}<input v-model="form.phone" /></label>
        <label>{{ t('partners.intro') }}<textarea v-model="form.intro" rows="3" /></label>

        <fieldset>
          <legend>{{ t('partners.processes') }}</legend>
          <label v-for="c in categories" :key="c.id" class="process-check">
            <input type="checkbox" :checked="form.process_ids.includes(c.id)" @change="toggleProcess(c.id)" />
            {{ pick(c.name) }}
          </label>
        </fieldset>

        <button type="submit" class="btn btn-primary" :disabled="submitting">
          {{ submitting ? t('common.loading') : t('partners.submit') }}
        </button>
      </form>
    </div>
  </PageShell>
</template>

<style scoped lang="scss">
.page-lead {
  color: var(--color-text-muted);
  margin-bottom: var(--space-xl);
}

.partner-grid {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: var(--space-xl);
}

.partner-info ul {
  padding-left: 1.25rem;
  line-height: 1.8;
}

.partner-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);

  label {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
    font-size: 0.875rem;
    font-weight: 500;
  }

  input,
  textarea {
    padding: 0.625rem 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
  }
}

.process-check {
  display: flex;
  flex-direction: row !important;
  align-items: center;
  gap: 0.5rem !important;
  margin-bottom: 0.375rem;
}

@media (max-width: 768px) {
  .partner-grid {
    grid-template-columns: 1fr;
  }
}
</style>
