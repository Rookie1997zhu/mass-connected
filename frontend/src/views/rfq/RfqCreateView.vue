<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { createRfq, fetchServiceCategories, uploadRfqAttachment } from '../../api'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const step = ref(1)
const categories = ref([])
const files = ref([])
const error = ref('')
const submitting = ref(false)

const form = ref({
  service_category: null,
  scope: 'internal',
  quantity: 1,
  material: '',
  tolerance: '',
  surface_finish: '',
  target_delivery_date: '',
  budget_amount: null,
  remark: '',
  contact_name: '',
  contact_phone: '',
  company: '',
})

const pick = (field) => {
  if (!field || typeof field !== 'object') return field || ''
  return field[locale.value] || field.ko || field.en || Object.values(field)[0] || ''
}

const selectedCategory = computed(() =>
  categories.value.find((c) => c.id === form.value.service_category),
)

onMounted(async () => {
  const res = await fetchServiceCategories()
  categories.value = res.data.items || []
  const preset = route.query.category
  if (preset) {
    const match = categories.value.find(
      (c) => String(c.id) === String(preset) || c.slug === preset,
    )
    if (match) form.value.service_category = match.id
  }
})

const onFileChange = (e) => {
  files.value = Array.from(e.target.files || [])
}

const canNext = computed(() => {
  if (step.value === 1) return Boolean(form.value.service_category)
  if (step.value === 2) return Number(form.value.quantity) > 0
  return true
})

const next = () => {
  if (canNext.value && step.value < 3) step.value += 1
}
const prev = () => {
  if (step.value > 1) step.value -= 1
}

const submit = async () => {
  error.value = ''
  submitting.value = true
  try {
    const payload = { ...form.value }
    if (!payload.target_delivery_date) delete payload.target_delivery_date
    if (!payload.budget_amount) delete payload.budget_amount
    const res = await createRfq(payload)
    const rfqId = res.data.id
    for (const file of files.value) {
      const fd = new FormData()
      fd.append('file', file)
      try {
        await uploadRfqAttachment(rfqId, fd)
      } catch {
        // 单个附件失败不阻塞其余流程
      }
    }
    router.push(`/my/rfqs/${rfqId}`)
  } catch (e) {
    error.value = e.message || t('rfq.submitFailed')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ t('rfq.createTitle') }}</h1>

    <ol class="steps">
      <li :class="{ active: step === 1, done: step > 1 }">1. {{ t('rfq.stepProcess') }}</li>
      <li :class="{ active: step === 2, done: step > 2 }">2. {{ t('rfq.stepSpecs') }}</li>
      <li :class="{ active: step === 3 }">3. {{ t('rfq.stepContact') }}</li>
    </ol>

    <!-- Step 1: process -->
    <section v-show="step === 1" class="rfq-panel">
      <div class="process-grid">
        <button
          v-for="c in categories"
          :key="c.id"
          type="button"
          class="process-card"
          :class="{ selected: form.service_category === c.id }"
          @click="form.service_category = c.id"
        >
          {{ pick(c.name) }}
        </button>
      </div>
    </section>

    <!-- Step 2: specs -->
    <section v-show="step === 2" class="rfq-panel">
      <div class="page-form">
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.quantity') }}</span>
          <input v-model.number="form.quantity" type="number" min="1" required />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.material') }}</span>
          <input v-model="form.material" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.tolerance') }}</span>
          <input v-model="form.tolerance" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.surfaceFinish') }}</span>
          <input v-model="form.surface_finish" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.targetDate') }}</span>
          <input v-model="form.target_delivery_date" type="date" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.budget') }}</span>
          <input v-model.number="form.budget_amount" type="number" min="0" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.remark') }}</span>
          <textarea v-model="form.remark" rows="4" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.attachments') }}</span>
          <input type="file" multiple @change="onFileChange" />
          <small class="hint">{{ t('rfq.attachmentsHint') }}</small>
        </label>
      </div>
    </section>

    <!-- Step 3: contact -->
    <section v-show="step === 3" class="rfq-panel">
      <div class="page-form">
        <p class="summary">{{ t('rfq.stepProcess') }}: <strong>{{ pick(selectedCategory?.name) }}</strong></p>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.contactName') }}</span>
          <input v-model="form.contact_name" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.contactPhone') }}</span>
          <input v-model="form.contact_phone" type="tel" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.company') }}</span>
          <input v-model="form.company" />
        </label>
        <label class="page-form-field scope-toggle">
          <span class="page-form-label">{{ t('rfq.publishPublic') }}</span>
          <label class="checkbox-row">
            <input v-model="form.scope" type="checkbox" true-value="public" false-value="internal" />
            <span>{{ t('rfq.publishPublicHint') }}</span>
          </label>
        </label>
      </div>
    </section>

    <p v-if="error" class="page-message page-message--error">{{ error }}</p>

    <div class="rfq-actions">
      <button v-if="step > 1" type="button" class="btn btn-secondary" @click="prev">
        {{ t('rfq.prev') }}
      </button>
      <button
        v-if="step < 3"
        type="button"
        class="btn btn-primary"
        :disabled="!canNext"
        @click="next"
      >
        {{ t('rfq.next') }}
      </button>
      <button
        v-else
        type="button"
        class="btn btn-primary"
        :disabled="submitting"
        @click="submit"
      >
        {{ t('rfq.submit') }}
      </button>
    </div>
  </PageShell>
</template>

<style scoped lang="scss">
.steps {
  display: flex;
  gap: var(--space-md);
  list-style: none;
  padding: 0;
  margin: 0 0 var(--space-xl);
  flex-wrap: wrap;

  li {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--color-text);
    opacity: 0.5;

    &.active { color: var(--color-steel); opacity: 1; }
    &.done { opacity: 0.8; }
  }
}
.process-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--space-md);
}
.process-card {
  padding: var(--space-lg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  cursor: pointer;
  font-weight: 500;
  transition: border-color 0.15s;

  &.selected { border-color: var(--color-steel); color: var(--color-steel); }
  &:hover { border-color: var(--color-steel); }
}
.rfq-actions {
  display: flex;
  gap: var(--space-md);
  margin-top: var(--space-xl);
}
.hint { color: var(--color-text); opacity: 0.6; font-size: 0.75rem; }
.summary { margin-bottom: var(--space-md); }
</style>
