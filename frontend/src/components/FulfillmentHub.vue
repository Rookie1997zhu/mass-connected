<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import FilePreviewModal from './FilePreviewModal.vue'
import { downloadAuthedFile, fetchAuthedBlobUrl } from '../utils/downloadAuthedFile'
import { useLocaleCurrency } from '../composables/useLocaleCurrency'
import {
  confirmProductionOrder,
  confirmSupplierPayment,
  rejectProductionOrder,
  signContract,
  uploadPaymentProof,
} from '../api'
import { resolveApiMessage } from '../utils/apiErrors'

const props = defineProps({
  role: { type: String, required: true }, // buyer | supplier
  fulfillment: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  /** null = 全部；order|contract|payment|project|files = 单段（用于详情页 Tab） */
  section: { type: String, default: null },
})

const emit = defineEmits(['refresh', 'payment-confirmed'])

const { t, te } = useI18n()
const { formatMoney } = useLocaleCurrency()
const actionError = ref('')
const actionMessage = ref('')
const busy = ref(false)
const previewOpen = ref(false)
const previewFile = ref(null)
const signForm = ref({
  company_name: '',
  business_reg_no: '',
  company_address: '',
  signer_name: '',
  agree: false,
})
const signatureFile = ref(null)
const signaturePreviewUrl = ref('')
const signatureInputRef = ref(null)
const signatureDisplayUrl = ref('')

const isBuyer = computed(() => props.role === 'buyer')
const order = computed(() => props.fulfillment?.production_order || null)
const contract = computed(() => props.fulfillment?.contract || null)
const payment = computed(() => props.fulfillment?.payment || null)
const project = computed(() => props.fulfillment?.project || null)
const files = computed(() => props.fulfillment?.files || [])
const hasFulfillment = computed(() => Boolean(order.value || contract.value || payment.value || project.value || files.value.length))
const showAll = computed(() => !props.section)
const showOrder = computed(() => showAll.value || props.section === 'order' || props.section === 'project')
const showContract = computed(() => showAll.value || props.section === 'contract')
const showPayment = computed(() => showAll.value || props.section === 'payment')
const showProject = computed(() => showAll.value || props.section === 'project')
const showFiles = computed(() => showAll.value || props.section === 'files')

const proofFile = computed(() => {
  const p = payment.value
  if (!p?.proof_url) return null
  return {
    id: `payment-proof-${p.id}`,
    file_url: p.proof_url,
    file_name: p.proof_file_name || t('fulfillment.proofFile'),
    file_ext: p.proof_file_ext || '',
    is_previewable: Boolean(p.proof_is_previewable),
  }
})
const canSupplierConfirmPayment = computed(
  () =>
    !isBuyer.value
    && payment.value?.status === 'pending_confirm'
    && Boolean(payment.value?.proof_url),
)

watch(
  () => props.fulfillment,
  () => {
    actionError.value = ''
    actionMessage.value = ''
    const c = props.fulfillment?.contract
    if (c) {
      signForm.value = {
        company_name: c.company_name || '',
        business_reg_no: c.business_reg_no || '',
        company_address: c.company_address || '',
        signer_name: c.signer_name || '',
        agree: false,
      }
    }
    if (signaturePreviewUrl.value) {
      URL.revokeObjectURL(signaturePreviewUrl.value)
      signaturePreviewUrl.value = ''
    }
    signatureFile.value = null
  },
  { immediate: true },
)

watch(
  () => contract.value?.signature_image_url,
  async (url) => {
    if (signatureDisplayUrl.value) {
      URL.revokeObjectURL(signatureDisplayUrl.value)
      signatureDisplayUrl.value = ''
    }
    if (!url) return
    try {
      signatureDisplayUrl.value = await fetchAuthedBlobUrl(url)
    } catch {
      signatureDisplayUrl.value = ''
    }
  },
  { immediate: true },
)

const onOpenContractPdf = async () => {
  if (!contract.value?.pdf_url) return
  try {
    await downloadAuthedFile(contract.value.pdf_url, 'contract.pdf')
  } catch {
    actionError.value = t('common.failed') || 'Failed'
  }
}

const canSign = computed(
  () =>
    isBuyer.value
    && contract.value?.status === 'pending_sign'
    && Boolean(signForm.value.company_name?.trim())
    && Boolean(signForm.value.business_reg_no?.trim())
    && Boolean(signForm.value.company_address?.trim())
    && Boolean(signForm.value.signer_name?.trim())
    && signForm.value.agree
    && Boolean(signatureFile.value),
)

const onPickSignature = (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  const allowed = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
  if (file.type && !allowed.includes(file.type)) {
    actionError.value = t('mypage.signatureTypeInvalid')
    return
  }
  if (file.size > 2 * 1024 * 1024) {
    actionError.value = t('mypage.signatureTooLarge')
    return
  }
  if (signaturePreviewUrl.value) URL.revokeObjectURL(signaturePreviewUrl.value)
  signatureFile.value = file
  signaturePreviewUrl.value = URL.createObjectURL(file)
  actionError.value = ''
}

const clearSignature = () => {
  if (signaturePreviewUrl.value) URL.revokeObjectURL(signaturePreviewUrl.value)
  signaturePreviewUrl.value = ''
  signatureFile.value = null
}

const money = (amount, currency) => formatMoney({ amount, currency: currency || 'CNY' })

const openPreview = (file) => {
  previewFile.value = file
  previewOpen.value = true
}

const downloadFile = async (file) => {
  if (!file?.file_url) return
  try {
    await downloadAuthedFile(file.file_url, file.file_name || 'file')
  } catch (e) {
    actionError.value = resolveApiMessage(e, t, 'fulfillment.actionFailed')
  }
}

const onSign = async () => {
  if (!contract.value?.id || !canSign.value) return
  busy.value = true
  actionError.value = ''
  try {
    const fd = new FormData()
    fd.append('company_name', signForm.value.company_name.trim())
    fd.append('business_reg_no', signForm.value.business_reg_no.trim())
    fd.append('company_address', signForm.value.company_address.trim())
    fd.append('signer_name', signForm.value.signer_name.trim())
    fd.append('agree', 'true')
    fd.append('signature_image', signatureFile.value)
    await signContract(contract.value.id, fd)
    actionMessage.value = t('mypage.contractSigned')
    clearSignature()
    emit('refresh')
  } catch (e) {
    actionError.value = resolveApiMessage(e, t, 'fulfillment.actionFailed')
  } finally {
    busy.value = false
  }
}

const onUploadProof = async (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !payment.value?.id) return
  busy.value = true
  actionError.value = ''
  try {
    const fd = new FormData()
    fd.append('proof', file)
    await uploadPaymentProof(payment.value.id, fd)
    actionMessage.value = t('mypage.proofUploaded')
    emit('refresh')
  } catch (e) {
    actionError.value = resolveApiMessage(e, t, 'fulfillment.actionFailed')
  } finally {
    busy.value = false
  }
}

const onConfirmOrder = async () => {
  if (!order.value?.id) return
  busy.value = true
  actionError.value = ''
  try {
    await confirmProductionOrder(order.value.id)
    actionMessage.value = t('productionOrder.confirmed')
    emit('refresh')
  } catch (e) {
    actionError.value = resolveApiMessage(e, t, 'fulfillment.actionFailed')
  } finally {
    busy.value = false
  }
}

const onConfirmPayment = async () => {
  if (!payment.value?.id) return
  busy.value = true
  actionError.value = ''
  try {
    await confirmSupplierPayment(payment.value.id)
    actionMessage.value = t('fulfillment.paymentConfirmed')
    emit('refresh')
    emit('payment-confirmed')
  } catch (e) {
    actionError.value = resolveApiMessage(e, t, 'fulfillment.actionFailed')
  } finally {
    busy.value = false
  }
}

const onRejectOrder = async () => {
  if (!order.value?.id) return
  busy.value = true
  actionError.value = ''
  try {
    await rejectProductionOrder(order.value.id)
    actionMessage.value = t('productionOrder.rejected')
    emit('refresh')
  } catch (e) {
    actionError.value = resolveApiMessage(e, t, 'fulfillment.actionFailed')
  } finally {
    busy.value = false
  }
}

// 后端状态枚举 → 当前语言文案；无映射时回退原值
const statusLabel = (status) => {
  if (!status) return '—'
  const key = `statusLabel.${status}`
  return te(key) ? t(key) : status
}

const sourceLabel = (source) => {
  if (source === 'rfq') return t('fulfillment.sourceRfq')
  if (source === 'quote') return t('fulfillment.sourceQuote')
  return t('fulfillment.sourceProject')
}
</script>

<template>
  <section
    id="fulfillment-hub"
    class="fulfillment"
    :class="{ 'fulfillment--embedded': !!section }"
  >
    <h2 v-if="showAll" class="section-sub">{{ t('fulfillment.title') }}</h2>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <template v-else>
      <p v-if="actionMessage" class="page-message page-message--success">{{ actionMessage }}</p>
      <p v-if="actionError" class="page-message page-message--error">{{ actionError }}</p>
      <p v-if="showAll && !hasFulfillment" class="page-empty">{{ t('fulfillment.empty') }}</p>

      <div v-if="showOrder" class="block">
        <h3>{{ t('fulfillment.order') }}</h3>
        <template v-if="order">
          <dl class="meta">
            <div><dt>{{ t('productionOrder.orderNo') }}</dt><dd>{{ order.order_no }}</dd></div>
            <div><dt>{{ t('mypage.status') }}</dt><dd>{{ statusLabel(order.status) }}</dd></div>
            <div>
              <dt>{{ t('rfq.price') }}</dt>
              <dd>{{ money(order.price_amount, order.currency) }}</dd>
            </div>
          </dl>
          <div v-if="!isBuyer && order.status === 'pending_confirm'" class="actions">
            <button type="button" class="btn btn-primary btn-sm" :disabled="busy" @click="onConfirmOrder">
              {{ t('productionOrder.confirm') }}
            </button>
            <button type="button" class="btn btn-secondary btn-sm" :disabled="busy" @click="onRejectOrder">
              {{ t('productionOrder.reject') }}
            </button>
          </div>
        </template>
        <p v-else class="hint">{{ t('fulfillment.orderEmpty') }}</p>
      </div>

      <div v-if="showContract" class="block">
        <h3>{{ t('mypage.contracts') }}</h3>
        <template v-if="contract">
          <dl class="meta">
            <div><dt>No.</dt><dd>{{ contract.contract_no }}</dd></div>
            <div><dt>{{ t('mypage.status') }}</dt><dd>{{ statusLabel(contract.status) }}</dd></div>
          </dl>
          <pre v-if="contract.rendered_body" class="nda-body">{{ contract.rendered_body }}</pre>
          <template v-if="isBuyer && contract.status === 'pending_sign'">
            <div class="sign-form">
              <label>
                {{ t('mypage.companyName') }}
                <input v-model="signForm.company_name" type="text" autocomplete="organization" />
              </label>
              <label>
                {{ t('mypage.businessRegNo') }}
                <input v-model="signForm.business_reg_no" type="text" />
              </label>
              <label>
                {{ t('mypage.companyAddress') }}
                <input v-model="signForm.company_address" type="text" autocomplete="street-address" />
              </label>
              <label>
                {{ t('mypage.signerName') }}
                <input v-model="signForm.signer_name" type="text" autocomplete="name" />
              </label>
              <div class="sign-upload">
                <label class="btn btn-secondary btn-sm upload-btn">
                  {{ t('mypage.uploadSignature') }}
                  <input
                    ref="signatureInputRef"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    hidden
                    :disabled="busy"
                    @change="onPickSignature"
                  />
                </label>
                <button
                  v-if="signatureFile"
                  type="button"
                  class="btn btn-secondary btn-sm"
                  :disabled="busy"
                  @click="clearSignature"
                >
                  {{ t('mypage.clearSignature') }}
                </button>
              </div>
              <img
                v-if="signaturePreviewUrl"
                :src="signaturePreviewUrl"
                class="signature-preview"
                :alt="t('mypage.uploadSignature')"
              />
              <label class="checkbox">
                <input v-model="signForm.agree" type="checkbox" />
                {{ t('mypage.agreeNda') }}
              </label>
              <div class="actions">
                <button
                  type="button"
                  class="btn btn-primary btn-sm"
                  :disabled="busy || !canSign"
                  @click="onSign"
                >
                  {{ t('mypage.signContract') }}
                </button>
              </div>
            </div>
          </template>
          <template v-else-if="contract.status === 'signed'">
            <dl v-if="contract.company_name" class="meta">
              <div><dt>{{ t('mypage.companyName') }}</dt><dd>{{ contract.company_name }}</dd></div>
              <div v-if="contract.signer_name">
                <dt>{{ t('mypage.signerName') }}</dt>
                <dd>{{ contract.signer_name }}</dd>
              </div>
            </dl>
            <img
              v-if="signatureDisplayUrl"
              :src="signatureDisplayUrl"
              class="signature-preview"
              :alt="t('mypage.uploadSignature')"
            />
            <button
              v-if="contract.pdf_url"
              type="button"
              class="link"
              @click="onOpenContractPdf"
            >
              {{ t('mypage.viewSignedPdf') }}
            </button>
          </template>
        </template>
        <p v-else class="hint">{{ t('fulfillment.contractEmpty') }}</p>
      </div>

      <div v-if="showPayment" class="block">
        <h3>{{ t('mypage.payments') }}</h3>
        <template v-if="payment">
          <dl class="meta">
            <div><dt>No.</dt><dd>{{ payment.payment_no }}</dd></div>
            <div><dt>{{ t('mypage.status') }}</dt><dd>{{ statusLabel(payment.status) }}</dd></div>
            <div>
              <dt>{{ t('mypage.amount') }}</dt>
              <dd>{{ money(payment.amount, payment.currency) }}</dd>
            </div>
          </dl>
          <div v-if="proofFile" class="actions">
            <button
              v-if="proofFile.is_previewable"
              type="button"
              class="btn btn-secondary btn-sm"
              @click="openPreview(proofFile)"
            >
              {{ t('fulfillment.previewProof') }}
            </button>
            <button type="button" class="btn btn-secondary btn-sm" @click="downloadFile(proofFile)">
              {{ t('fulfillment.downloadProof') }}
            </button>
          </div>
          <div v-if="isBuyer && payment.status !== 'confirmed' && payment.status !== 'cancelled'" class="actions">
            <label class="btn btn-secondary btn-sm upload-btn">
              {{ t('mypage.uploadProof') }}
              <input type="file" hidden :disabled="busy" @change="onUploadProof" />
            </label>
          </div>
          <div v-if="canSupplierConfirmPayment" class="actions">
            <button type="button" class="btn btn-primary btn-sm" :disabled="busy" @click="onConfirmPayment">
              {{ t('fulfillment.confirmPayment') }}
            </button>
          </div>
          <p v-else-if="!isBuyer && !proofFile" class="hint">{{ t('fulfillment.paymentSupplierWaiting') }}</p>
        </template>
        <p v-else class="hint">{{ t('fulfillment.paymentEmpty') }}</p>
      </div>

      <div v-if="showProject" class="block">
        <h3>{{ t('mypage.projects') }}</h3>
        <template v-if="project">
          <dl class="meta">
            <div><dt>{{ t('fulfillment.projectNo') }}</dt><dd>{{ project.project_no }}</dd></div>
            <div><dt>{{ t('mypage.status') }}</dt><dd>{{ statusLabel(project.status) }}</dd></div>
            <div>
              <dt>{{ t('mypage.progress') }}</dt>
              <dd>{{ project.progress_percent }}%</dd>
            </div>
            <div v-if="project.current_stage">
              <dt>{{ t('workflow.currentStage') }}</dt>
              <dd>{{ project.current_stage.name }}</dd>
            </div>
          </dl>
          <div class="progress-bar"><span :style="{ width: (project.progress_percent || 0) + '%' }" /></div>
          <ol v-if="project.stages?.length" class="stages">
            <li v-for="s in project.stages" :key="s.id" :class="`stage--${s.status}`">
              {{ s.name }} · {{ statusLabel(s.status) }}
            </li>
          </ol>
          <RouterLink
            v-if="isBuyer"
            class="link"
            :to="`/my/projects/${project.id}`"
          >
            {{ t('fulfillment.openProject') }}
          </RouterLink>
          <RouterLink
            v-else
            class="link"
            :to="`/supplier/projects/${project.id}`"
          >
            {{ t('fulfillment.openProject') }}
          </RouterLink>
        </template>
        <p v-else class="hint">{{ t('fulfillment.projectEmpty') }}</p>
      </div>

      <div v-if="showFiles" class="block">
        <h3>{{ t('fulfillment.files') }}</h3>
        <p v-if="!files.length" class="hint">{{ t('fulfillment.filesEmpty') }}</p>
        <ul v-else class="file-list">
          <li v-for="f in files" :key="f.id">
            <span class="file-main">
              {{ f.file_name }}
              <em>{{ sourceLabel(f.source) }}<template v-if="f.stage_name"> · {{ f.stage_name }}</template></em>
            </span>
            <button
              v-if="f.is_previewable"
              type="button"
              class="btn btn-secondary btn-sm"
              @click="openPreview(f)"
            >
              {{ t('filePreview.preview') }}
            </button>
            <button type="button" class="btn btn-secondary btn-sm" @click="downloadFile(f)">
              {{ t('filePreview.download') }}
            </button>
          </li>
        </ul>
      </div>
    </template>
  </section>

  <FilePreviewModal :open="previewOpen" :file="previewFile" @close="previewOpen = false" />
</template>

<style scoped lang="scss">
.fulfillment {
  margin-top: var(--space-2xl);
  padding-top: var(--space-lg);
  border-top: 1px solid var(--color-border);
}
.fulfillment--embedded {
  margin-top: 0;
  padding-top: 0;
  border-top: 0;
}
.section-sub { font-size: 1.125rem; margin: 0 0 var(--space-md); }
.block {
  margin-bottom: var(--space-xl);
  padding: var(--space-lg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  h3 { margin: 0 0 var(--space-md); font-size: 1rem; }
}
.fulfillment--embedded .block:last-child { margin-bottom: 0; }
.meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem 1rem;
  margin: 0 0 var(--space-md);
  dt { font-size: 0.72rem; text-transform: uppercase; opacity: 0.6; }
  dd { margin: 0.15rem 0 0; font-weight: 600; }
}
.actions { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
.hint { margin: 0; font-size: 0.875rem; opacity: 0.7; }
.link { color: var(--color-steel); font-size: 0.9rem; }
.upload-btn { display: inline-flex; cursor: pointer; }
.nda-body {
  white-space: pre-wrap;
  font-size: 0.82rem;
  line-height: 1.5;
  max-height: 360px;
  overflow: auto;
  padding: var(--space-md);
  margin: 0 0 var(--space-md);
  background: var(--color-surface-muted, #f8f9fa);
  border-radius: var(--radius-sm);
}
.sign-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  label {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
    font-size: 0.875rem;
  }
  label.checkbox { flex-direction: row; align-items: center; }
  input[type='text'] {
    padding: 0.625rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
  }
}
.sign-upload { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
.signature-preview {
  max-width: 220px;
  max-height: 90px;
  object-fit: contain;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #fff;
}
.progress-bar {
  height: 8px;
  background: var(--color-border);
  border-radius: 999px;
  overflow: hidden;
  margin-bottom: var(--space-md);
  span { display: block; height: 100%; background: var(--color-steel); }
}
.stages {
  margin: 0 0 var(--space-md);
  padding-left: 1.1rem;
  font-size: 0.85rem;
  li { margin: 0.2rem 0; }
  .stage--completed { opacity: 0.75; }
  .stage--in_progress { font-weight: 600; }
}
.file-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  li {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    align-items: center;
    padding: 0.5rem 0.65rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
  }
  .file-main { flex: 1; min-width: 140px; }
  em { display: block; font-style: normal; font-size: 0.75rem; opacity: 0.55; }
}
@media (max-width: 640px) {
  .meta { grid-template-columns: 1fr; }
}
</style>
