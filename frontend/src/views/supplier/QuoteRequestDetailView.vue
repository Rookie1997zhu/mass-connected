<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import FilePreviewModal from '../../components/FilePreviewModal.vue'
import TextTranslateBlock from '../../components/TextTranslateBlock.vue'
import FulfillmentHub from '../../components/FulfillmentHub.vue'
import {
  deleteSupplierQuoteAttachment,
  fetchSupplierQuoteRequest,
  fetchSupplierQuoteRequestFulfillment,
  submitSupplierQuote,
  uploadSupplierQuoteAttachment,
} from '../../api'
import { useLocaleCurrency } from '../../composables/useLocaleCurrency'
import { downloadAuthedFile } from '../../utils/downloadAuthedFile'

const { t } = useI18n()
const { formatMoney, displayCurrency } = useLocaleCurrency()
const route = useRoute()
const data = ref(null)
const fulfillment = ref(null)
const fulfillmentLoading = ref(false)
const loading = ref(true)
const error = ref('')
const message = ref('')
const pendingFiles = ref([])
const uploading = ref(false)
const previewFile = ref(null)
const previewOpen = ref(false)
const previewContextType = ref('quote')
const previewContextId = ref(null)
const activeTab = ref('specs')
const form = ref({
  price_amount: '',
  unit_price: '',
  mold_fee: '',
  sample_fee: '',
  moq: '',
  lead_time_days: 7,
  valid_until: '',
  note: '',
})

const tabs = [
  { id: 'specs', labelKey: 'fulfillment.tabSpecs' },
  { id: 'quotes', labelKey: 'fulfillment.tabQuotes' },
  { id: 'contract', labelKey: 'fulfillment.tabContract' },
  { id: 'payment', labelKey: 'fulfillment.tabPayment' },
  { id: 'project', labelKey: 'fulfillment.tabProject' },
  { id: 'files', labelKey: 'fulfillment.tabFiles' },
]

const canEdit = computed(() => {
  if (!data.value) return false
  if (['cancelled', 'expired', 'not_adopted', 'adopted'].includes(data.value.status)) return false
  if (data.value.rfq_detail?.status === 'won') return false
  if (data.value.my_quote?.status === 'accepted') return false
  return true
})

const fillFromQuote = (quote) => {
  if (!quote) return
  form.value = {
    price_amount: quote.price_amount ?? '',
    unit_price: quote.unit_price ?? '',
    mold_fee: quote.mold_fee ?? '',
    sample_fee: quote.sample_fee ?? '',
    moq: quote.moq ?? '',
    lead_time_days: quote.lead_time_days || 7,
    valid_until: quote.valid_until || '',
    note: quote.note || '',
  }
}

const loadFulfillment = async () => {
  fulfillmentLoading.value = true
  try {
    const res = await fetchSupplierQuoteRequestFulfillment(route.params.id)
    fulfillment.value = res.data
  } catch {
    fulfillment.value = null
  } finally {
    fulfillmentLoading.value = false
  }
}

const load = async () => {
  const res = await fetchSupplierQuoteRequest(route.params.id)
  data.value = res.data
  if (res.data.my_quote) fillFromQuote(res.data.my_quote)
  await loadFulfillment()
}

onMounted(async () => {
  try {
    await load()
  } finally {
    loading.value = false
  }
})

const onPickFiles = (e) => {
  const files = Array.from(e.target.files || [])
  pendingFiles.value = [...pendingFiles.value, ...files].slice(0, 10)
  e.target.value = ''
}

const removePending = (idx) => {
  pendingFiles.value = pendingFiles.value.filter((_, i) => i !== idx)
}

const buildQuoteFormData = () => {
  const fd = new FormData()
  fd.append('price_amount', String(Number(form.value.price_amount)))
  if (form.value.unit_price !== '' && form.value.unit_price != null) {
    fd.append('unit_price', String(Number(form.value.unit_price)))
  }
  if (form.value.mold_fee !== '' && form.value.mold_fee != null) {
    fd.append('mold_fee', String(Number(form.value.mold_fee)))
  }
  if (form.value.sample_fee !== '' && form.value.sample_fee != null) {
    fd.append('sample_fee', String(Number(form.value.sample_fee)))
  }
  if (form.value.moq !== '' && form.value.moq != null) {
    fd.append('moq', String(Number(form.value.moq)))
  }
  fd.append('currency', displayCurrency.value || 'CNY')
  fd.append('lead_time_days', String(Number(form.value.lead_time_days) || 7))
  if (form.value.valid_until) fd.append('valid_until', form.value.valid_until)
  fd.append('note', form.value.note || '')
  pendingFiles.value.forEach((file) => fd.append('attachments', file))
  return fd
}

const submit = async () => {
  error.value = ''
  message.value = ''
  uploading.value = true
  try {
    await submitSupplierQuote(route.params.id, buildQuoteFormData())
    message.value = data.value?.my_quote ? t('quoteRequest.updated') : t('quoteRequest.submitted')
    pendingFiles.value = []
    await load()
  } catch (e) {
    error.value = e.message || t('demandHall.quoteFailed')
  } finally {
    uploading.value = false
  }
}

const uploadMore = async (e) => {
  const files = Array.from(e.target.files || [])
  e.target.value = ''
  if (!files.length || !data.value?.my_quote?.id) return
  error.value = ''
  message.value = ''
  uploading.value = true
  try {
    const fd = new FormData()
    files.forEach((f) => fd.append('attachments', f))
    await uploadSupplierQuoteAttachment(data.value.my_quote.id, fd)
    message.value = t('quoteRequest.attachmentUploaded')
    await load()
  } catch (err) {
    error.value = err.message || t('quoteRequest.attachmentUploadFailed')
  } finally {
    uploading.value = false
  }
}

const removeUploaded = async (fileId) => {
  if (!data.value?.my_quote?.id) return
  try {
    await deleteSupplierQuoteAttachment(data.value.my_quote.id, fileId)
    message.value = t('quoteRequest.attachmentRemoved')
    await load()
  } catch (e) {
    error.value = e.message || t('quoteRequest.attachmentUploadFailed')
  }
}

const openPreview = (file, contextType = 'quote', contextId = null) => {
  previewFile.value = file
  previewContextType.value = contextType
  previewContextId.value = contextId ?? data.value?.my_quote?.id ?? null
  previewOpen.value = true
}

const openRfqPreview = (file) => {
  openPreview(file, 'rfq', data.value?.id)
}

const downloadFile = async (file) => {
  const url = file?.file_url || file?.url
  if (!url) return
  try {
    await downloadAuthedFile(url, file.file_name || 'file')
  } catch (e) {
    error.value = e.message || t('quoteRequest.attachmentUploadFailed')
  }
}
</script>

<template>
  <PageShell>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <template v-else-if="data">
      <h1 class="page-title">{{ data.request_no }}</h1>
      <p class="page-lead">{{ data.rfq_no }} · {{ data.service_category_name }}</p>

      <nav class="deal-tabs" role="tablist">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          role="tab"
          class="deal-tab"
          :class="{ active: activeTab === tab.id }"
          :aria-selected="activeTab === tab.id"
          @click="activeTab = tab.id"
        >
          {{ t(tab.labelKey) }}
        </button>
      </nav>

      <div v-show="activeTab === 'specs'" class="tab-panel">
        <dl class="detail-grid">
          <div><dt>{{ t('rfq.quantity') }}</dt><dd>{{ data.rfq_detail?.quantity }}</dd></div>
          <div><dt>{{ t('rfq.material') }}</dt><dd>{{ data.rfq_detail?.material || '—' }}</dd></div>
          <div><dt>{{ t('quoteRequest.deadline') }}</dt><dd>{{ data.deadline || '—' }}</dd></div>
          <div class="full">
            <dt>{{ t('quoteRequest.adminNote') }}</dt>
            <dd>
              {{ data.admin_note || '—' }}
              <TextTranslateBlock
                v-if="data.admin_note"
                context-type="quoteRequest"
                :context-id="data.id"
                role="supplier"
                :text="data.admin_note"
              />
            </dd>
          </div>
          <div class="full">
            <dt>{{ t('rfq.remark') }}</dt>
            <dd>
              {{ data.rfq_detail?.remark || '—' }}
              <TextTranslateBlock
                v-if="data.rfq_detail?.remark"
                context-type="quoteRequest"
                :context-id="data.id"
                role="supplier"
                :text="data.rfq_detail.remark"
              />
            </dd>
          </div>
        </dl>

        <h2 class="section-sub">{{ t('rfq.attachments') }}</h2>
        <ul v-if="data.rfq_detail?.attachments?.length" class="att-list">
          <li v-for="a in data.rfq_detail.attachments" :key="a.id">
            <span>{{ a.file_name }}</span>
            <button
              v-if="a.is_previewable"
              type="button"
              class="btn btn-secondary btn-sm"
              @click="openRfqPreview(a)"
            >
              {{ t('filePreview.preview') }}
            </button>
            <button type="button" class="btn btn-secondary btn-sm" @click="downloadFile(a)">
              {{ t('filePreview.download') }}
            </button>
          </li>
        </ul>
        <p v-else class="page-empty">—</p>
      </div>

      <div v-show="activeTab === 'quotes'" class="tab-panel">
        <p v-if="error" class="page-message page-message--error">{{ error }}</p>
        <p v-if="message" class="page-message page-message--success">{{ message }}</p>

        <section v-if="data.my_quote" class="card quote-existing">
          <h2>{{ t('demandHall.myQuote') }}</h2>
          <p>
            {{ t('rfq.price') }}:
            {{ formatMoney({ amount: data.my_quote.price_amount, currency: data.my_quote.currency || 'KRW' }) }}
          </p>
          <p>{{ t('mypage.status') }}: {{ data.my_quote.status }}</p>
          <p v-if="data.my_quote.revision_version">
            {{ t('quoteRequest.revision') }}: v{{ data.my_quote.revision_version }}
          </p>
          <p>
            {{ t('myRfqs.paymentTerms') }}: {{ data.my_quote.payment_terms || t('myRfqs.paymentTermsPlatform') }}
          </p>
          <p v-if="data.my_quote.note">
            {{ t('rfq.note') }}: {{ data.my_quote.note }}
            <TextTranslateBlock
              context-type="quote"
              :context-id="data.my_quote.id"
              role="supplier"
              :text="data.my_quote.note"
            />
          </p>
          <h3 class="sub">{{ t('quoteRequest.attachments') }}</h3>
          <ul v-if="data.my_quote.attachments?.length" class="file-list">
            <li v-for="a in data.my_quote.attachments" :key="a.id">
              <span>{{ a.file_name }}</span>
              <button
                v-if="a.is_previewable"
                type="button"
                class="btn btn-secondary btn-sm"
                @click="openPreview(a, 'quote', data.my_quote.id)"
              >
                {{ t('filePreview.preview') }}
              </button>
              <button type="button" class="btn btn-secondary btn-sm" @click="downloadFile(a)">
                {{ t('filePreview.download') }}
              </button>
              <button
                v-if="canEdit"
                type="button"
                class="btn btn-secondary btn-sm"
                @click="removeUploaded(a.id)"
              >
                {{ t('quoteRequest.removeAttachment') }}
              </button>
            </li>
          </ul>
          <p v-else class="page-empty">{{ t('quoteDetail.noAttachments') }}</p>
          <label v-if="canEdit" class="upload-more">
            {{ t('quoteRequest.uploadAttachment') }}
            <input type="file" multiple @change="uploadMore" />
          </label>
        </section>

        <section v-if="canEdit" class="card quote-form">
          <h2>{{ data.my_quote ? t('quoteRequest.updateQuote') : t('quoteRequest.submitQuote') }}</h2>
          <label>
            {{ t('rfq.price') }} ({{ displayCurrency }})
            <input v-model="form.price_amount" type="number" min="1" />
          </label>
          <label>{{ t('myRfqs.unitPrice') }}<input v-model="form.unit_price" type="number" min="0" /></label>
          <label>{{ t('myRfqs.moldFee') }}<input v-model="form.mold_fee" type="number" min="0" /></label>
          <label>{{ t('myRfqs.sampleFee') }}<input v-model="form.sample_fee" type="number" min="0" /></label>
          <label>{{ t('myRfqs.moq') }}<input v-model="form.moq" type="number" min="1" /></label>
          <p class="hint">{{ t('myRfqs.paymentTerms') }}: {{ t('myRfqs.paymentTermsPlatform') }}</p>
          <label>{{ t('rfq.leadTime') }}<input v-model="form.lead_time_days" type="number" min="1" /></label>
          <label>{{ t('rfq.validUntil') }}<input v-model="form.valid_until" type="date" /></label>
          <label>{{ t('rfq.note') }}<textarea v-model="form.note" rows="3" /></label>

          <div class="attach-box">
            <h3>{{ t('quoteRequest.attachments') }}</h3>
            <p class="hint">{{ t('quoteRequest.attachmentsHint') }}</p>
            <input type="file" multiple @change="onPickFiles" />
            <ul v-if="pendingFiles.length" class="file-list">
              <li v-for="(f, idx) in pendingFiles" :key="`${f.name}-${idx}`">
                <span>{{ f.name }}</span>
                <button type="button" class="btn btn-secondary btn-sm" @click="removePending(idx)">
                  {{ t('quoteRequest.removeAttachment') }}
                </button>
              </li>
            </ul>
          </div>

          <button type="button" class="btn btn-primary" :disabled="uploading" @click="submit">
            {{ data.my_quote ? t('quoteRequest.updateQuote') : t('quoteRequest.submitQuote') }}
          </button>
        </section>
        <p v-else-if="data.my_quote" class="page-empty">{{ t('quoteRequest.locked') }}</p>
      </div>

      <FulfillmentHub
        v-if="activeTab === 'contract' || activeTab === 'payment' || activeTab === 'project' || activeTab === 'files'"
        role="supplier"
        :section="activeTab"
        :fulfillment="fulfillment"
        :loading="fulfillmentLoading"
        @refresh="load"
        @payment-confirmed="activeTab = 'project'"
      />
    </template>

    <FilePreviewModal
      :open="previewOpen"
      :file="previewFile"
      :context-type="previewContextType"
      :context-id="previewContextId"
      role="supplier"
      @close="previewOpen = false"
    />
  </PageShell>
</template>

<style scoped lang="scss">
.deal-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: var(--space-md) 0 var(--space-xl);
}
.deal-tab {
  padding: 0.45rem 0.85rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  &.active {
    background: var(--color-steel-muted);
    border-color: var(--color-steel);
    color: var(--color-steel);
  }
}
.tab-panel { min-height: 8rem; }
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md) var(--space-xl);
  margin: 0 0 var(--space-lg);
  .full { grid-column: 1 / -1; }
  dt { font-size: 0.75rem; text-transform: uppercase; opacity: 0.6; }
  dd { margin: 0.25rem 0 0; font-weight: 500; }
}
.section-sub { font-size: 1.125rem; margin: var(--space-xl) 0 var(--space-md); }
.att-list { padding-left: 1.2rem; a { color: var(--color-steel); } }
.card {
  margin-top: var(--space-lg);
  padding: var(--space-lg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}
.quote-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.875rem; }
  input, textarea { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
}
.attach-box {
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-md);
  h3 { margin: 0 0 0.35rem; font-size: 0.95rem; }
  .hint { margin: 0 0 0.65rem; font-size: 0.8rem; opacity: 0.65; }
}
.file-list {
  list-style: none;
  margin: 0.75rem 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  li {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    flex-wrap: wrap;
    padding: 0.45rem 0.6rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
  }
  a { color: var(--color-steel); font-size: 0.85rem; }
}
.sub { margin: 1rem 0 0.5rem; font-size: 0.95rem; }
.upload-more {
  display: inline-flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-top: 0.75rem;
  font-size: 0.85rem;
}
</style>
