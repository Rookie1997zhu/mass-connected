<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { createRfq, fetchServiceCategories, uploadRfqAttachment } from '../../api'
import { resolveApiMessage } from '../../utils/apiErrors'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const step = ref(1)
const categories = ref([])
const error = ref('')
const submitting = ref(false)
const createdRfqId = ref(null)
const idempotencyKey = ref(
  typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `rfq-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
)

/** @type {import('vue').Ref<Array<{ id: string, file: File, status: 'pending'|'uploading'|'done'|'failed', message: string }>>} */
const fileItems = ref([])

const form = ref({
  service_category: null,
  scope: 'public',
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

const failedFiles = computed(() => fileItems.value.filter((item) => item.status === 'failed'))
const pendingOrFailed = computed(() =>
  fileItems.value.filter((item) => item.status === 'pending' || item.status === 'failed'),
)
const hasPartialUploadFailure = computed(() => Boolean(createdRfqId.value && failedFiles.value.length))

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
  const selected = Array.from(e.target.files || [])
  const existingNames = new Set(fileItems.value.map((item) => `${item.file.name}:${item.file.size}`))
  selected.forEach((file) => {
    const key = `${file.name}:${file.size}`
    if (existingNames.has(key)) return
    fileItems.value.push({
      id: `${key}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      file,
      status: 'pending',
      message: '',
    })
  })
  e.target.value = ''
}

const removeFile = (id) => {
  fileItems.value = fileItems.value.filter((item) => item.id !== id)
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

const uploadOne = async (item) => {
  if (!createdRfqId.value) return
  item.status = 'uploading'
  item.message = ''
  const fd = new FormData()
  fd.append('file', item.file)
  try {
    await uploadRfqAttachment(createdRfqId.value, fd)
    item.status = 'done'
    item.message = ''
  } catch (e) {
    item.status = 'failed'
    item.message = resolveApiMessage(e, t, 'rfq.attachmentUploadFailed')
  }
}

const uploadPendingFiles = async () => {
  for (const item of pendingOrFailed.value) {
    await uploadOne(item)
  }
}

const goToCreatedRfq = () => {
  if (createdRfqId.value) router.push(`/my/rfqs/${createdRfqId.value}`)
}

const submit = async () => {
  error.value = ''
  submitting.value = true
  try {
    if (!createdRfqId.value) {
      const payload = {
        ...form.value,
        idempotency_key: idempotencyKey.value,
      }
      if (!payload.target_delivery_date) delete payload.target_delivery_date
      if (!payload.budget_amount) delete payload.budget_amount
      const res = await createRfq(payload, {
        headers: { 'Idempotency-Key': idempotencyKey.value },
      })
      createdRfqId.value = res.data.id
    }
    if (fileItems.value.length) {
      await uploadPendingFiles()
    }
    if (failedFiles.value.length) {
      error.value = t('rfq.attachmentPartialFailed')
      return
    }
    goToCreatedRfq()
  } catch (e) {
    error.value = resolveApiMessage(e, t, 'rfq.submitFailed')
  } finally {
    submitting.value = false
  }
}

const retryFailed = async () => {
  error.value = ''
  submitting.value = true
  try {
    await uploadPendingFiles()
    if (failedFiles.value.length) {
      error.value = t('rfq.attachmentPartialFailed')
      return
    }
    goToCreatedRfq()
  } finally {
    submitting.value = false
  }
}

const fileStatusLabel = (status) => {
  if (status === 'done') return t('rfq.attachmentStatusDone')
  if (status === 'uploading') return t('rfq.attachmentStatusUploading')
  if (status === 'failed') return t('rfq.attachmentStatusFailed')
  return t('rfq.attachmentStatusPending')
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
          :disabled="Boolean(createdRfqId)"
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
          <input v-model.number="form.quantity" type="number" min="1" required :disabled="Boolean(createdRfqId)" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.material') }}</span>
          <input v-model="form.material" :disabled="Boolean(createdRfqId)" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.tolerance') }}</span>
          <input v-model="form.tolerance" :disabled="Boolean(createdRfqId)" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.surfaceFinish') }}</span>
          <input v-model="form.surface_finish" :disabled="Boolean(createdRfqId)" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.targetDate') }}</span>
          <input v-model="form.target_delivery_date" type="date" :disabled="Boolean(createdRfqId)" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.budget') }}</span>
          <input v-model.number="form.budget_amount" type="number" min="0" :disabled="Boolean(createdRfqId)" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.remark') }}</span>
          <textarea v-model="form.remark" rows="4" :disabled="Boolean(createdRfqId)" />
        </label>
        <div class="page-form-field">
          <span class="page-form-label">{{ t('rfq.attachments') }}</span>
          <input type="file" multiple @change="onFileChange" />
          <small class="hint">{{ t('rfq.attachmentsHint') }}</small>
          <p class="hint refresh-hint">{{ t('rfq.attachmentReselectHint') }}</p>
          <ul v-if="fileItems.length" class="file-status-list">
            <li v-for="item in fileItems" :key="item.id" class="file-status-item" :data-status="item.status">
              <div class="file-status-main">
                <span class="file-name">{{ item.file.name }}</span>
                <span class="file-status">{{ fileStatusLabel(item.status) }}</span>
              </div>
              <p v-if="item.message" class="file-error">{{ item.message }}</p>
              <button
                v-if="item.status !== 'done' && item.status !== 'uploading'"
                type="button"
                class="btn btn-sm btn-secondary"
                @click="removeFile(item.id)"
              >
                {{ t('common.close') }}
              </button>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Step 3: contact -->
    <section v-show="step === 3" class="rfq-panel">
      <div class="page-form">
        <p class="summary">{{ t('rfq.stepProcess') }}: <strong>{{ pick(selectedCategory?.name) }}</strong></p>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.contactName') }}</span>
          <input v-model="form.contact_name" :disabled="Boolean(createdRfqId)" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.contactPhone') }}</span>
          <input v-model="form.contact_phone" type="tel" :disabled="Boolean(createdRfqId)" />
        </label>
        <label class="page-form-field">
          <span class="page-form-label">{{ t('rfq.company') }}</span>
          <input v-model="form.company" :disabled="Boolean(createdRfqId)" />
        </label>
        <label class="page-form-field scope-toggle">
          <span class="page-form-label">{{ t('rfq.publishPublic') }}</span>
          <label class="checkbox-row">
            <input
              v-model="form.scope"
              type="checkbox"
              true-value="public"
              false-value="internal"
              :disabled="Boolean(createdRfqId)"
            />
            <span>{{ t('rfq.publishPublicHint') }}</span>
          </label>
        </label>
      </div>
    </section>

    <p v-if="createdRfqId" class="page-message">{{ t('rfq.createdKeepUploading', { id: createdRfqId }) }}</p>
    <p v-if="error" class="page-message page-message--error">{{ error }}</p>

    <div class="rfq-actions">
      <button v-if="step > 1 && !createdRfqId" type="button" class="btn btn-secondary" @click="prev">
        {{ t('rfq.prev') }}
      </button>
      <button
        v-if="step < 3 && !createdRfqId"
        type="button"
        class="btn btn-primary"
        :disabled="!canNext"
        @click="next"
      >
        {{ t('rfq.next') }}
      </button>
      <template v-else>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="submitting"
          @click="hasPartialUploadFailure ? retryFailed() : submit()"
        >
          {{ hasPartialUploadFailure ? t('rfq.retryFailedAttachments') : t('rfq.submit') }}
        </button>
        <button
          v-if="hasPartialUploadFailure"
          type="button"
          class="btn btn-secondary"
          :disabled="submitting"
          @click="goToCreatedRfq"
        >
          {{ t('rfq.continueWithoutFailedAttachments') }}
        </button>
      </template>
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
  &:disabled { opacity: 0.7; cursor: not-allowed; }
}
.rfq-actions {
  display: flex;
  gap: var(--space-md);
  margin-top: var(--space-xl);
  flex-wrap: wrap;
}
.hint { color: var(--color-text); opacity: 0.6; font-size: 0.75rem; }
.refresh-hint { margin-top: var(--space-xs); }
.summary { margin-bottom: var(--space-md); }
.file-status-list {
  list-style: none;
  padding: 0;
  margin: var(--space-md) 0 0;
  display: grid;
  gap: var(--space-sm);
}
.file-status-item {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
  background: var(--color-surface);

  &[data-status='failed'] { border-color: #c45c5c; }
  &[data-status='done'] { border-color: #5a8f6c; }
}
.file-status-main {
  display: flex;
  justify-content: space-between;
  gap: var(--space-md);
  flex-wrap: wrap;
}
.file-name { font-size: 0.875rem; word-break: break-all; }
.file-status { font-size: 0.75rem; opacity: 0.75; }
.file-error {
  margin: var(--space-xs) 0;
  color: #b42318;
  font-size: 0.8125rem;
}
</style>
