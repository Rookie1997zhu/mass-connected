<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import QuoteDetailModal from '../../components/QuoteDetailModal.vue'
import FulfillmentHub from '../../components/FulfillmentHub.vue'
import FilePreviewModal from '../../components/FilePreviewModal.vue'
import TextTranslateBlock from '../../components/TextTranslateBlock.vue'
import {
  acceptQuote,
  createQuoteCounterOffer,
  downloadRfqQuotePdf,
  fetchMyQuoteDetail,
  fetchMyRfq,
  fetchMyRfqFulfillment,
  fetchQuoteCounterOffers,
  updateMyRfq,
  uploadRfqAttachment,
  withdrawQuoteCounterOffer,
} from '../../api'
import { useLocaleCurrency } from '../../composables/useLocaleCurrency'
import { downloadAuthedFile } from '../../utils/downloadAuthedFile'
import { resolveApiMessage } from '../../utils/apiErrors'

const { t } = useI18n()
const { formatMoney } = useLocaleCurrency()
const route = useRoute()
const rfq = ref(null)

const windowOpenChat = (quoteRequestId) => {
  window.__openPlatformChat?.(quoteRequestId)
}
const fulfillment = ref(null)
const fulfillmentLoading = ref(false)
const loading = ref(true)
const message = ref('')
const successMessage = ref('')
const saving = ref(false)
const detailOpen = ref(false)
const detailLoading = ref(false)
const detailError = ref('')
const quoteDetail = ref(null)
const activeTab = ref(
  ['specs', 'quotes', 'contract', 'payment', 'project', 'files'].includes(route.query.tab)
    ? route.query.tab
    : 'specs',
)
const previewFile = ref(null)
const previewOpen = ref(false)
const editForm = ref({
  quantity: 1,
  material: '',
  tolerance: '',
  surface_finish: '',
  target_delivery_date: '',
  budget_amount: null,
  remark: '',
})
const uploadItems = ref([])
const uploading = ref(false)
const canReattach = computed(
  () => rfq.value && !['won', 'closed'].includes(rfq.value.status),
)
const participants = computed(() => rfq.value?.participants || [])

const tabs = [
  { id: 'specs', labelKey: 'fulfillment.tabSpecs' },
  { id: 'quotes', labelKey: 'fulfillment.tabQuotes' },
  { id: 'contract', labelKey: 'fulfillment.tabContract' },
  { id: 'payment', labelKey: 'fulfillment.tabPayment' },
  { id: 'project', labelKey: 'fulfillment.tabProject' },
  { id: 'files', labelKey: 'fulfillment.tabFiles' },
]

const loadFulfillment = async () => {
  if (!rfq.value?.id) return
  fulfillmentLoading.value = true
  try {
    const res = await fetchMyRfqFulfillment(rfq.value.id)
    fulfillment.value = res.data
  } catch {
    fulfillment.value = null
  } finally {
    fulfillmentLoading.value = false
  }
}

const load = async () => {
  const res = await fetchMyRfq(route.params.id)
  rfq.value = res.data
  editForm.value = {
    quantity: res.data.quantity || 1,
    material: res.data.material || '',
    tolerance: res.data.tolerance || '',
    surface_finish: res.data.surface_finish || '',
    target_delivery_date: res.data.target_delivery_date || '',
    budget_amount: res.data.budget_amount,
    remark: res.data.remark || '',
  }
  await loadFulfillment()
}

onMounted(async () => {
  try {
    await load()
  } finally {
    loading.value = false
  }
})

const onDownloadPdf = async () => {
  const res = await downloadRfqQuotePdf(rfq.value.id)
  const blob = new Blob([res], { type: 'application/pdf' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${rfq.value.rfq_no}-comparison.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

const onSaveRfq = async () => {
  message.value = ''
  successMessage.value = ''
  saving.value = true
  try {
    const payload = { ...editForm.value }
    if (!payload.target_delivery_date) delete payload.target_delivery_date
    if (!payload.budget_amount) delete payload.budget_amount
    await updateMyRfq(rfq.value.id, payload)
    successMessage.value = t('myRfqs.rfqUpdated')
    await load()
  } catch (e) {
    message.value = resolveApiMessage(e, t, 'myRfqs.rfqUpdateFailed')
  } finally {
    saving.value = false
  }
}

const openRfqPreview = (file) => {
  previewFile.value = file
  previewOpen.value = true
}

const downloadRfqFile = async (file) => {
  const url = file?.file_url || file?.url
  if (!url) return
  try {
    await downloadAuthedFile(url, file.file_name || 'file')
  } catch (e) {
    console.error(e)
  }
}

const onReattachFiles = (e) => {
  const selected = Array.from(e.target.files || [])
  const existing = new Set(uploadItems.value.map((i) => `${i.file.name}:${i.file.size}`))
  selected.forEach((file) => {
    const key = `${file.name}:${file.size}`
    if (existing.has(key)) return
    uploadItems.value.push({
      id: `${key}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      file,
      status: 'pending',
      message: '',
    })
  })
  e.target.value = ''
}

const uploadOneAttachment = async (item) => {
  item.status = 'uploading'
  item.message = ''
  const fd = new FormData()
  fd.append('file', item.file)
  try {
    await uploadRfqAttachment(rfq.value.id, fd)
    item.status = 'done'
  } catch (e) {
    item.status = 'failed'
    item.message = resolveApiMessage(e, t, 'rfq.attachmentUploadFailed')
  }
}

const uploadPendingAttachments = async () => {
  if (!canReattach.value || uploading.value) return
  uploading.value = true
  message.value = ''
  try {
    for (const item of uploadItems.value.filter((i) => i.status === 'pending' || i.status === 'failed')) {
      await uploadOneAttachment(item)
    }
    if (uploadItems.value.some((i) => i.status === 'failed')) {
      message.value = t('rfq.attachmentPartialFailed')
    } else {
      uploadItems.value = []
      await load()
    }
  } finally {
    uploading.value = false
  }
}

const openDetail = async (quoteId) => {
  detailOpen.value = true
  detailLoading.value = true
  detailError.value = ''
  quoteDetail.value = null
  try {
    const res = await fetchMyQuoteDetail(rfq.value.id, quoteId)
    quoteDetail.value = res.data
    await openCounterForm(quoteId)
  } catch (e) {
    detailError.value = resolveApiMessage(e, t, 'quoteDetail.loadFailed')
  } finally {
    detailLoading.value = false
  }
}

const closeDetail = () => {
  detailOpen.value = false
  quoteDetail.value = null
  detailError.value = ''
  counterOffers.value = []
  counterForm.value.quoteId = null
}

const onAccept = async (quoteId) => {
  message.value = ''
  successMessage.value = ''
  try {
    const idempotencyKey = `accept-${rfq.value.id}-${quoteId}-${Date.now()}`
    const res = await acceptQuote(rfq.value.id, quoteId, { idempotencyKey })
    const orderNo = res.data?.production_order?.order_no
    successMessage.value = orderNo
      ? t('productionOrder.created', { orderNo })
      : t('myRfqs.acceptSuccess')
    closeDetail()
    await load()
    activeTab.value = 'contract'
  } catch (e) {
    message.value = resolveApiMessage(e, t, 'rfq.acceptFailed')
  }
}

const counterForm = ref({
  quoteId: null,
  target_total_amount: '',
  lead_time_days: '',
  quantity: '',
  note: '',
})
const counterOffers = ref([])
const counterLoading = ref(false)
const counterSubmitting = ref(false)

const openCounterForm = async (quoteId) => {
  counterForm.value = {
    quoteId,
    target_total_amount: '',
    lead_time_days: '',
    quantity: rfq.value?.quantity || '',
    note: '',
  }
  counterLoading.value = true
  try {
    const res = await fetchQuoteCounterOffers(rfq.value.id, quoteId)
    counterOffers.value = res.data || []
  } catch {
    counterOffers.value = []
  } finally {
    counterLoading.value = false
  }
}

const submitCounterOffer = async () => {
  if (!counterForm.value.quoteId || counterSubmitting.value) return
  counterSubmitting.value = true
  message.value = ''
  try {
    const payload = {
      target_total_amount: Number(counterForm.value.target_total_amount),
      note: counterForm.value.note || '',
    }
    if (counterForm.value.quantity) payload.quantity = Number(counterForm.value.quantity)
    if (counterForm.value.lead_time_days !== '') {
      payload.lead_time_days = Number(counterForm.value.lead_time_days)
    }
    await createQuoteCounterOffer(rfq.value.id, counterForm.value.quoteId, payload)
    successMessage.value = t('myRfqs.counterOfferSubmitted')
    await openCounterForm(counterForm.value.quoteId)
  } catch (e) {
    message.value = resolveApiMessage(e, t, 'myRfqs.counterOfferFailed')
  } finally {
    counterSubmitting.value = false
  }
}

const onWithdrawCounter = async (coId) => {
  try {
    await withdrawQuoteCounterOffer(rfq.value.id, coId)
    if (counterForm.value.quoteId) await openCounterForm(counterForm.value.quoteId)
  } catch (e) {
    message.value = resolveApiMessage(e, t, 'myRfqs.counterOfferFailed')
  }
}
</script>

<template>
  <PageShell>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <template v-else-if="rfq">
      <h1 class="page-title">{{ rfq.rfq_no }}</h1>
      <p class="rfq-status-line">{{ t('common.status') }}: <strong>{{ rfq.status }}</strong></p>

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

      <p v-if="successMessage" class="page-message page-message--success">{{ successMessage }}</p>
      <p v-if="message" class="page-message page-message--error">{{ message }}</p>

      <div v-show="activeTab === 'specs'" class="tab-panel">
        <dl class="detail-grid">
          <div><dt>{{ t('rfq.stepProcess') }}</dt><dd>{{ rfq.service_category_name }}</dd></div>
          <div><dt>{{ t('rfq.quantity') }}</dt><dd>{{ rfq.quantity }}</dd></div>
          <div><dt>{{ t('rfq.material') }}</dt><dd>{{ rfq.material || '—' }}</dd></div>
          <div><dt>{{ t('rfq.tolerance') }}</dt><dd>{{ rfq.tolerance || '—' }}</dd></div>
          <div><dt>{{ t('rfq.surfaceFinish') }}</dt><dd>{{ rfq.surface_finish || '—' }}</dd></div>
          <div><dt>{{ t('rfq.targetDate') }}</dt><dd>{{ rfq.target_delivery_date || '—' }}</dd></div>
          <div class="full">
            <dt>{{ t('rfq.remark') }}</dt>
            <dd>
              {{ rfq.remark || '—' }}
              <TextTranslateBlock
                v-if="rfq.remark"
                context-type="rfq"
                :context-id="rfq.id"
                role="member"
                :text="rfq.remark"
              />
            </dd>
          </div>
        </dl>

        <section v-if="rfq.can_edit" class="edit-card">
          <h2 class="section-sub">{{ t('myRfqs.editRfq') }}</h2>
          <div class="edit-grid">
            <label>{{ t('rfq.quantity') }}<input v-model.number="editForm.quantity" type="number" min="1" /></label>
            <label>{{ t('rfq.material') }}<input v-model="editForm.material" /></label>
            <label>{{ t('rfq.tolerance') }}<input v-model="editForm.tolerance" /></label>
            <label>{{ t('rfq.surfaceFinish') }}<input v-model="editForm.surface_finish" /></label>
            <label>{{ t('rfq.targetDate') }}<input v-model="editForm.target_delivery_date" type="date" /></label>
            <label>{{ t('rfq.budget') }}<input v-model.number="editForm.budget_amount" type="number" min="0" /></label>
            <label class="full">{{ t('rfq.remark') }}<textarea v-model="editForm.remark" rows="3" /></label>
          </div>
          <button type="button" class="btn btn-secondary btn-sm" :disabled="saving" @click="onSaveRfq">
            {{ t('mypage.save') }}
          </button>
        </section>

        <h2 class="section-sub">{{ t('rfq.attachments') }}</h2>
        <p v-if="!rfq.attachments?.length" class="page-empty">—</p>
        <ul v-else class="att-list">
          <li v-for="a in rfq.attachments" :key="a.id">
            <span>{{ a.file_name }}</span>
            <button
              v-if="a.is_previewable"
              type="button"
              class="btn btn-secondary btn-sm"
              @click="openRfqPreview(a)"
            >
              {{ t('filePreview.preview') }}
            </button>
            <button type="button" class="btn btn-secondary btn-sm" @click="downloadRfqFile(a)">
              {{ t('filePreview.download') }}
            </button>
          </li>
        </ul>

        <section v-if="canReattach" class="reattach-box">
          <p class="hint">{{ t('rfq.attachmentReselectHint') }}</p>
          <input type="file" multiple @change="onReattachFiles" />
          <ul v-if="uploadItems.length" class="upload-list">
            <li v-for="item in uploadItems" :key="item.id">
              <span>{{ item.file.name }} · {{ item.status }}</span>
              <span v-if="item.message" class="err">{{ item.message }}</span>
            </li>
          </ul>
          <button
            type="button"
            class="btn btn-secondary btn-sm"
            :disabled="uploading || !uploadItems.length"
            @click="uploadPendingAttachments"
          >
            {{
              uploading
                ? t('common.loading')
                : uploadItems.some((i) => i.status === 'failed')
                  ? t('rfq.retryFailedAttachments')
                  : t('quoteRequest.uploadAttachment')
            }}
          </button>
        </section>
        <p v-else class="hint">{{ t('rfq.attachmentLocked') }}</p>
      </div>

      <div v-show="activeTab === 'quotes'" class="tab-panel">
        <section v-if="participants.length" class="participants-box">
          <h2 class="section-sub">{{ t('myRfqs.participants') }}</h2>
          <p class="hint">{{ t('myRfqs.participantsHint') }}</p>
          <ul class="participant-list">
            <li v-for="p in participants" :key="p.quote_request_id">
              <div>
                <strong>{{ p.supplier_company_name }}</strong>
                <span class="muted"> · {{ p.status }}</span>
                <span v-if="p.has_visible_quote" class="muted"> · {{ t('myRfqs.hasQuote') }}</span>
              </div>
              <button
                type="button"
                class="btn btn-secondary btn-sm"
                @click="windowOpenChat(p.quote_request_id)"
              >
                {{ t('chat.openChat') }}
              </button>
            </li>
          </ul>
        </section>

        <h2 class="section-sub">{{ t('myRfqs.plans') }}</h2>
        <button v-if="rfq.plans?.length" type="button" class="btn btn-secondary btn-sm mb" @click="onDownloadPdf">
          {{ t('myRfqs.downloadPdf') }}
        </button>
        <p v-if="!rfq.plans?.length" class="page-empty">{{ t('myRfqs.noPlans') }}</p>
        <table v-else-if="rfq.plans.length > 1" class="quote-table mb">
          <thead>
            <tr>
              <th></th>
              <th v-for="p in rfq.plans" :key="p.id">
                <button type="button" class="plan-link" @click="openDetail(p.id)">
                  {{ t('myRfqs.plan') }} {{ p.plan_label || p.id }}
                </button>
                <span v-if="p.supplier_name" class="supplier-sub">{{ p.supplier_name }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{{ t('myRfqs.supplier') }}</td>
              <td v-for="p in rfq.plans" :key="p.id">{{ p.supplier_name || '—' }}</td>
            </tr>
            <tr>
              <td>{{ t('rfq.price') }}</td>
              <td v-for="p in rfq.plans" :key="p.id">
                {{ formatMoney({ amount: p.price_amount, currency: p.currency }) }}
              </td>
            </tr>
            <tr>
              <td>{{ t('myRfqs.unitPrice') }}</td>
              <td v-for="p in rfq.plans" :key="p.id">
                {{ p.unit_price ? formatMoney({ amount: p.unit_price, currency: p.currency }) : '—' }}
              </td>
            </tr>
            <tr>
              <td>{{ t('myRfqs.moldFee') }}</td>
              <td v-for="p in rfq.plans" :key="p.id">
                {{ p.mold_fee ? formatMoney({ amount: p.mold_fee, currency: p.currency }) : '—' }}
              </td>
            </tr>
            <tr>
              <td>{{ t('myRfqs.sampleFee') }}</td>
              <td v-for="p in rfq.plans" :key="p.id">
                {{ p.sample_fee ? formatMoney({ amount: p.sample_fee, currency: p.currency }) : '—' }}
              </td>
            </tr>
            <tr>
              <td>{{ t('myRfqs.moq') }}</td>
              <td v-for="p in rfq.plans" :key="p.id">{{ p.moq || '—' }}</td>
            </tr>
            <tr>
              <td>{{ t('rfq.leadTime') }}</td>
              <td v-for="p in rfq.plans" :key="p.id">{{ p.lead_time_days }}</td>
            </tr>
            <tr>
              <td>{{ t('myRfqs.paymentTerms') }}</td>
              <td v-for="p in rfq.plans" :key="p.id">{{ p.payment_terms || t('myRfqs.paymentTermsPlatform') }}</td>
            </tr>
            <tr>
              <td>{{ t('myRfqs.revision') }}</td>
              <td v-for="p in rfq.plans" :key="p.id">
                v{{ p.revision_version || 1 }}
                <span v-if="p.revised_at" class="muted"> · {{ String(p.revised_at).slice(0, 16).replace('T', ' ') }}</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="rfq.plans?.length" class="plan-grid">
          <article
            v-for="p in rfq.plans"
            :key="p.id"
            class="plan-card"
            :class="{ 'plan-card--accepted': p.status === 'accepted' }"
            role="button"
            tabindex="0"
            @click="openDetail(p.id)"
            @keydown.enter="openDetail(p.id)"
          >
            <div class="plan-head">
              <span class="plan-label">{{ t('myRfqs.plan') }} {{ p.plan_label || '-' }}</span>
              <span v-if="p.status === 'accepted'" class="accepted">✓ {{ t('myRfqs.confirmed') }}</span>
            </div>
            <p v-if="p.supplier_name" class="supplier-name">{{ p.supplier_name }}</p>
            <p class="plan-price">{{ formatMoney({ amount: p.price_amount, currency: p.currency }) }}</p>
            <p class="price-hint">{{ t('myRfqs.customerPriceHint') }}</p>
            <ul class="plan-meta">
              <li>{{ t('rfq.leadTime') }}: {{ p.lead_time_days }}</li>
              <li>{{ t('rfq.validUntil') }}: {{ p.valid_until || '—' }}</li>
              <li v-if="p.moq">{{ t('myRfqs.moq') }}: {{ p.moq }}</li>
              <li>{{ t('myRfqs.paymentTerms') }}: {{ p.payment_terms || t('myRfqs.paymentTermsPlatform') }}</li>
              <li>{{ t('myRfqs.revision') }}: v{{ p.revision_version || 1 }}</li>
              <li v-if="p.attachment_count">{{ t('quoteDetail.attachmentCount', { n: p.attachment_count }) }}</li>
            </ul>
            <div class="plan-actions" @click.stop>
              <button type="button" class="btn btn-secondary btn-sm" @click="openDetail(p.id)">
                {{ t('quoteDetail.viewDetail') }}
              </button>
              <button
                v-if="p.quote_request_id"
                type="button"
                class="btn btn-secondary btn-sm"
                @click="windowOpenChat(p.quote_request_id)"
              >
                {{ t('chat.openChat') }}
              </button>
              <button
                v-if="p.status === 'sent'"
                type="button"
                class="btn btn-secondary btn-sm"
                @click="openCounterForm(p.id)"
              >
                {{ t('myRfqs.counterOffer') }}
              </button>
              <button
                v-if="p.status === 'sent'"
                type="button"
                class="btn btn-primary btn-sm"
                @click="onAccept(p.id)"
              >
                {{ t('myRfqs.confirmPlan') }}
              </button>
            </div>
          </article>
        </div>

        <section v-if="counterForm.quoteId" class="counter-box">
          <h3 class="section-sub">{{ t('myRfqs.counterOfferTitle') }}</h3>
          <p class="hint">{{ t('myRfqs.counterOfferDisclaimer') }}</p>
          <div class="edit-grid">
            <label>
              {{ t('myRfqs.counterTargetAmount') }}
              <input v-model="counterForm.target_total_amount" type="number" min="1" />
            </label>
            <label>
              {{ t('rfq.quantity') }}
              <input v-model="counterForm.quantity" type="number" min="1" />
            </label>
            <label>
              {{ t('rfq.leadTime') }}
              <input v-model="counterForm.lead_time_days" type="number" min="0" />
            </label>
            <label class="full">
              {{ t('rfq.remark') }}
              <textarea v-model="counterForm.note" rows="2" />
            </label>
          </div>
          <button
            type="button"
            class="btn btn-primary btn-sm"
            :disabled="counterSubmitting || !counterForm.target_total_amount"
            @click="submitCounterOffer"
          >
            {{ counterSubmitting ? t('common.loading') : t('myRfqs.counterOfferSubmit') }}
          </button>
          <p v-if="counterLoading" class="muted">{{ t('common.loading') }}</p>
          <ul v-else-if="counterOffers.length" class="counter-list">
            <li v-for="co in counterOffers" :key="co.id">
              <span>
                {{ formatMoney({ amount: co.target_total_amount, currency: co.currency }) }}
                · {{ co.status }}
              </span>
              <button
                v-if="co.status === 'pending'"
                type="button"
                class="btn btn-secondary btn-sm"
                @click="onWithdrawCounter(co.id)"
              >
                {{ t('myRfqs.counterOfferWithdraw') }}
              </button>
            </li>
          </ul>
        </section>
      </div>

      <FulfillmentHub
        v-if="activeTab === 'contract' || activeTab === 'payment' || activeTab === 'project' || activeTab === 'files'"
        role="buyer"
        :section="activeTab"
        :fulfillment="fulfillment"
        :loading="fulfillmentLoading"
        @refresh="loadFulfillment"
      />
    </template>

    <QuoteDetailModal
      :open="detailOpen"
      :detail="quoteDetail"
      :loading="detailLoading"
      :error="detailError"
      :can-accept="true"
      @close="closeDetail"
      @accept="onAccept"
    />
    <FilePreviewModal
      :open="previewOpen"
      :file="previewFile"
      context-type="rfq"
      :context-id="rfq?.id"
      role="member"
      @close="previewOpen = false"
    />
  </PageShell>
</template>

<style scoped lang="scss">
.rfq-status-line { margin-bottom: var(--space-md); }
.deal-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: var(--space-xl);
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
  margin: 0 0 var(--space-2xl);
  .full { grid-column: 1 / -1; }
  dt { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text); opacity: 0.6; }
  dd { margin: 0.25rem 0 0; font-weight: 500; }
}
.edit-card {
  margin-bottom: var(--space-xl);
  padding: var(--space-lg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}
.edit-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md);
  margin-bottom: var(--space-md);
  label { display: flex; flex-direction: column; gap: 0.35rem; font-size: 0.85rem; }
  .full { grid-column: 1 / -1; }
  input, textarea { padding: 0.5rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
}
.section-sub { font-size: 1.125rem; margin: 0 0 var(--space-md); }
.participants-box { margin-bottom: var(--space-xl); }
.participant-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
    padding: 0.65rem 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
  }
}
.muted { color: var(--color-text); opacity: 0.65; font-size: 0.85rem; }
.att-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  li { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
}
.plan-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--space-lg); }
.plan-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
  &:hover { border-color: var(--color-steel); box-shadow: 0 2px 10px rgba(0,0,0,0.04); }
}
.plan-card--accepted { border-color: var(--color-steel); background: var(--color-steel-muted); }
.plan-head { display: flex; justify-content: space-between; align-items: center; }
.plan-label { font-weight: 700; font-size: 1rem; }
.supplier-name { margin: 0; font-size: 0.9rem; font-weight: 600; }
.supplier-sub { display: block; font-size: 0.7rem; font-weight: 500; text-transform: none; opacity: 0.7; }
.plan-price { font-size: 1.375rem; font-weight: 700; margin: 0; }
.price-hint { margin: 0; font-size: 0.75rem; opacity: 0.65; }
.plan-meta { margin: 0; padding-left: 1rem; font-size: 0.85rem; }
.plan-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: auto; }
.accepted { color: var(--color-steel); font-size: 0.8rem; font-weight: 600; }
.mb { margin-bottom: var(--space-md); }
.plan-link {
  background: none;
  border: 0;
  color: var(--color-steel);
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  padding: 0;
}
.quote-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
  th, td { border: 1px solid var(--color-border); padding: 0.5rem 0.65rem; text-align: left; }
  th { background: var(--color-bg-muted, #f7f7f8); }
}
.counter-box {
  margin-top: var(--space-xl);
  padding: var(--space-lg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}
.counter-list {
  list-style: none;
  padding: 0;
  margin: var(--space-md) 0 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  li { display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; }
}
.hint { font-size: 0.85rem; opacity: 0.75; margin: 0 0 var(--space-md); }
</style>
