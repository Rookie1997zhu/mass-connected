<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../components/PageShell.vue'
import { fetchServiceCategories } from '../api'
import { useAuthStore } from '../stores/auth'
import { resolveApiMessage } from '../utils/apiErrors'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()

const memberType = ref('individual')
const categories = ref([])
const error = ref('')
const submitting = ref(false)

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

const pick = (field) => {
  if (!field || typeof field !== 'object') return field || ''
  return field[locale.value] || field.ko || field.en || Object.values(field)[0] || ''
}

onMounted(async () => {
  if (route.query.type === 'enterprise') memberType.value = 'enterprise'
  try {
    const res = await fetchServiceCategories()
    categories.value = res.data.items || []
  } catch {
    categories.value = []
  }
})

const toggleProcess = (id) => {
  const idx = form.value.process_ids.indexOf(id)
  if (idx >= 0) form.value.process_ids.splice(idx, 1)
  else form.value.process_ids.push(id)
}

const onSubmit = async () => {
  error.value = ''
  submitting.value = true
  try {
    const payload = {
      member_type: memberType.value,
      email: form.value.email,
      password: form.value.password,
      name: form.value.name,
      phone: form.value.phone,
    }
    if (memberType.value === 'enterprise') {
      Object.assign(payload, {
        company_name: form.value.company_name,
        region: form.value.region,
        intro: form.value.intro,
        contact_phone: form.value.contact_phone || form.value.phone,
        process_ids: form.value.process_ids,
      })
    }
    await auth.register(payload)
    router.push('/verify-email/sent')
  } catch (e) {
    error.value = resolveApiMessage(e, t, 'register.failed')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <PageShell centered>
    <h1 class="page-title" style="text-align: center">{{ t('nav.register') }}</h1>

    <div class="type-tabs">
      <button
        type="button"
        class="type-tab"
        :class="{ active: memberType === 'individual' }"
        @click="memberType = 'individual'"
      >
        {{ t('register.individual') }}
      </button>
      <button
        type="button"
        class="type-tab"
        :class="{ active: memberType === 'enterprise' }"
        @click="memberType = 'enterprise'"
      >
        {{ t('register.enterprise') }}
      </button>
    </div>

    <p class="type-desc">{{ memberType === 'individual' ? t('register.individualDesc') : t('register.enterpriseDesc') }}</p>

    <form class="page-form" @submit.prevent="onSubmit">
      <label class="page-form-field">
        <span class="page-form-label">{{ t('account.name') }}</span>
        <input v-model="form.name" autocomplete="name" required />
      </label>
      <label class="page-form-field">
        <span class="page-form-label">{{ t('account.email') }}</span>
        <input v-model="form.email" type="email" autocomplete="email" required />
      </label>
      <label class="page-form-field">
        <span class="page-form-label">{{ t('account.phone') }}</span>
        <input v-model="form.phone" type="tel" autocomplete="tel" />
      </label>
      <label class="page-form-field">
        <span class="page-form-label">{{ t('account.password') }}</span>
        <input v-model="form.password" type="password" autocomplete="new-password" required minlength="8" />
      </label>

      <template v-if="memberType === 'enterprise'">
        <label class="page-form-field">
          <span class="page-form-label">{{ t('partners.companyName') }}</span>
          <input v-model="form.company_name" required />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('partners.region') }}</span>
          <input v-model="form.region" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('partners.intro') }}</span>
          <textarea v-model="form.intro" rows="3" />
        </label>
        <fieldset v-if="categories.length" class="process-fieldset">
          <legend>{{ t('partners.processes') }}</legend>
          <label v-for="c in categories" :key="c.id" class="process-check">
            <input type="checkbox" :checked="form.process_ids.includes(c.id)" @change="toggleProcess(c.id)" />
            {{ pick(c.name) }}
          </label>
        </fieldset>
      </template>

      <button type="submit" class="btn btn-primary btn-submit" :disabled="submitting">
        {{ memberType === 'enterprise' ? t('register.enterpriseSubmit') : t('nav.register') }}
      </button>
    </form>

    <p v-if="error" class="page-message page-message--error">{{ error }}</p>
    <p class="page-message">
      <RouterLink to="/login">{{ t('nav.login') }}</RouterLink>
    </p>
  </PageShell>
</template>

<style scoped lang="scss">
.type-tabs {
  display: flex;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
  justify-content: center;
}
.type-tab {
  padding: 0.5rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: transparent;
  cursor: pointer;
  &.active {
    border-color: var(--color-steel);
    background: var(--color-steel-muted);
    font-weight: 600;
  }
}
.type-desc {
  text-align: center;
  color: var(--color-text-muted);
  font-size: 0.875rem;
  margin-bottom: var(--space-lg);
}
.process-fieldset {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-md);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.process-check {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}
.page-message a {
  color: var(--color-steel);
  font-weight: 600;
  text-decoration: none;
}
</style>
