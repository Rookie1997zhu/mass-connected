<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import FilePreviewModal from './FilePreviewModal.vue'
import TextTranslateBlock from './TextTranslateBlock.vue'
import { useLocaleCurrency } from '../composables/useLocaleCurrency'
import { downloadAuthedFile } from '../utils/downloadAuthedFile'

const props = defineProps({
  open: { type: Boolean, default: false },
  detail: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  canAccept: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'accept', 'preview'])

const { t } = useI18n()
const { formatMoney } = useLocaleCurrency()
const previewFile = ref(null)
const previewOpen = ref(false)

const profile = computed(() => props.detail?.supplier_profile || null)
const attachments = computed(() => props.detail?.attachments || [])
const publicAttachments = computed(() => profile.value?.public_attachments || [])

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) {
      previewOpen.value = false
      previewFile.value = null
    }
  },
)

const close = () => emit('close')

const onAccept = () => {
  if (props.detail?.id) emit('accept', props.detail.id)
}

const openPreview = (file) => {
  previewFile.value = file
  previewOpen.value = true
}

const downloadFile = async (file) => {
  if (!file?.file_url) return
  try {
    await downloadAuthedFile(file.file_url, file.file_name || 'file')
  } catch (e) {
    console.error(e)
  }
}
</script>

<template>
  <div v-if="open" class="detail-overlay" @click.self="close">
    <div class="detail-dialog" role="dialog" aria-modal="true">
      <header class="detail-head">
        <h3>
          {{ t('quoteDetail.title') }}
          <span v-if="detail?.plan_label"> · {{ t('myRfqs.plan') }} {{ detail.plan_label }}</span>
        </h3>
        <button type="button" class="btn btn-secondary btn-sm" @click="close">
          {{ t('common.close') }}
        </button>
      </header>

      <div class="detail-body">
        <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
        <p v-else-if="error" class="page-message page-message--error">{{ error }}</p>
        <template v-else-if="detail">
          <section class="block">
            <h4>{{ t('quoteDetail.priceBreakdown') }}</h4>
            <p class="supplier">{{ detail.supplier_name || t('myRfqs.supplier') }}</p>
            <p class="price">{{ formatMoney({ amount: detail.price_amount, currency: detail.currency }) }}</p>
            <p class="hint">{{ t('myRfqs.customerPriceHint') }}</p>
            <dl class="meta-grid">
              <div>
                <dt>{{ t('myRfqs.unitPrice') }}</dt>
                <dd>
                  {{ detail.unit_price ? formatMoney({ amount: detail.unit_price, currency: detail.currency }) : '—' }}
                </dd>
              </div>
              <div>
                <dt>{{ t('myRfqs.moldFee') }}</dt>
                <dd>
                  {{ detail.mold_fee ? formatMoney({ amount: detail.mold_fee, currency: detail.currency }) : '—' }}
                </dd>
              </div>
              <div>
                <dt>{{ t('myRfqs.sampleFee') }}</dt>
                <dd>
                  {{ detail.sample_fee ? formatMoney({ amount: detail.sample_fee, currency: detail.currency }) : '—' }}
                </dd>
              </div>
              <div>
                <dt>{{ t('myRfqs.moq') }}</dt>
                <dd>{{ detail.moq || '—' }}</dd>
              </div>
            </dl>
          </section>

          <section class="block">
            <h4>{{ t('quoteDetail.deliveryTerms') }}</h4>
            <ul class="plain-list">
              <li>{{ t('rfq.leadTime') }}: {{ detail.lead_time_days }}</li>
              <li>{{ t('rfq.validUntil') }}: {{ detail.valid_until || '—' }}</li>
              <li>
                {{ t('myRfqs.paymentTerms') }}: {{ detail.payment_terms || '—' }}
                <TextTranslateBlock
                  v-if="detail.payment_terms"
                  context-type="quote"
                  :context-id="detail.id"
                  role="member"
                  :text="detail.payment_terms"
                />
              </li>
              <li v-if="detail.revision_version">
                {{ t('quoteRequest.revision') }}: v{{ detail.revision_version }}
              </li>
              <li v-if="detail.note">
                {{ t('rfq.note') }}: {{ detail.note }}
                <TextTranslateBlock
                  context-type="quote"
                  :context-id="detail.id"
                  role="member"
                  :text="detail.note"
                />
              </li>
            </ul>
          </section>

          <section v-if="profile" class="block">
            <h4>{{ t('quoteDetail.supplierProfile') }}</h4>
            <dl class="meta-grid">
              <div><dt>{{ t('mypage.companyName') }}</dt><dd>{{ profile.company_name || '—' }}</dd></div>
              <div>
                <dt>{{ t('quoteDetail.location') }}</dt>
                <dd>{{ [profile.region, profile.city, profile.country].filter(Boolean).join(' · ') || '—' }}</dd>
              </div>
              <div>
                <dt>{{ t('quoteDetail.establishedYear') }}</dt>
                <dd>{{ profile.established_year || '—' }}</dd>
              </div>
              <div>
                <dt>{{ t('quoteDetail.employeeScale') }}</dt>
                <dd>{{ profile.employee_scale || '—' }}</dd>
              </div>
              <div>
                <dt>{{ t('quoteDetail.factoryArea') }}</dt>
                <dd>{{ profile.factory_area_sqm ? `${profile.factory_area_sqm} m²` : '—' }}</dd>
              </div>
              <div>
                <dt>{{ t('quoteDetail.score') }}</dt>
                <dd>{{ profile.score ?? '—' }}</dd>
              </div>
              <div class="full">
                <dt>{{ t('quoteDetail.mainProducts') }}</dt>
                <dd>{{ profile.main_products || '—' }}</dd>
              </div>
              <div class="full">
                <dt>{{ t('quoteDetail.monthlyCapacity') }}</dt>
                <dd>{{ profile.monthly_capacity || '—' }}</dd>
              </div>
              <div class="full">
                <dt>{{ t('quoteDetail.certifications') }}</dt>
                <dd>{{ profile.quality_certifications || '—' }}</dd>
              </div>
              <div class="full">
                <dt>{{ t('quoteDetail.equipment') }}</dt>
                <dd>{{ profile.equipment_summary || '—' }}</dd>
              </div>
              <div class="full">
                <dt>{{ t('mypage.intro') }}</dt>
                <dd>{{ profile.intro || '—' }}</dd>
              </div>
              <div class="full" v-if="profile.process_names?.length">
                <dt>{{ t('quoteDetail.processes') }}</dt>
                <dd>{{ profile.process_names.join(' / ') }}</dd>
              </div>
              <div class="full" v-if="profile.tags?.length">
                <dt>{{ t('quoteDetail.tags') }}</dt>
                <dd>{{ profile.tags.join(' · ') }}</dd>
              </div>
            </dl>
          </section>

          <section class="block">
            <h4>{{ t('quoteDetail.quoteAttachments') }}</h4>
            <p v-if="!attachments.length" class="page-empty">{{ t('quoteDetail.noAttachments') }}</p>
            <ul v-else class="att-list">
              <li v-for="a in attachments" :key="a.id">
                <span>{{ a.file_name }}</span>
                <button
                  v-if="a.is_previewable"
                  type="button"
                  class="btn btn-secondary btn-sm"
                  @click="openPreview(a)"
                >
                  {{ t('filePreview.preview') }}
                </button>
                <button type="button" class="btn btn-secondary btn-sm" @click="downloadFile(a)">
                  {{ t('filePreview.download') }}
                </button>
              </li>
            </ul>
          </section>

          <section v-if="publicAttachments.length" class="block">
            <h4>{{ t('quoteDetail.companyAttachments') }}</h4>
            <ul class="att-list">
              <li v-for="a in publicAttachments" :key="a.id">
                <span>{{ a.file_name }} <em>({{ a.category }})</em></span>
                <button
                  v-if="a.is_previewable"
                  type="button"
                  class="btn btn-secondary btn-sm"
                  @click="openPreview(a)"
                >
                  {{ t('filePreview.preview') }}
                </button>
                <button type="button" class="btn btn-secondary btn-sm" @click="downloadFile(a)">
                  {{ t('filePreview.download') }}
                </button>
              </li>
            </ul>
          </section>

          <div v-if="canAccept && detail.status === 'sent'" class="actions">
            <button type="button" class="btn btn-primary" @click="onAccept">
              {{ t('myRfqs.confirmPlan') }}
            </button>
          </div>
        </template>
      </div>
    </div>
  </div>

  <FilePreviewModal
    :open="previewOpen"
    :file="previewFile"
    context-type="quote"
    :context-id="detail?.id"
    role="member"
    @close="previewOpen = false"
  />
</template>

<style scoped lang="scss">
.detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}
.detail-dialog {
  background: var(--color-surface, #fff);
  border-radius: var(--radius-md, 8px);
  width: min(760px, 100%);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.detail-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--color-border);
  h3 { margin: 0; font-size: 1.05rem; }
}
.detail-body {
  padding: 1rem;
  overflow: auto;
}
.block {
  margin-bottom: 1.25rem;
  h4 { margin: 0 0 0.65rem; font-size: 0.95rem; }
}
.supplier { margin: 0; font-weight: 600; }
.price { margin: 0.35rem 0; font-size: 1.5rem; font-weight: 700; }
.hint { margin: 0 0 0.75rem; font-size: 0.8rem; opacity: 0.65; }
.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem 1rem;
  margin: 0;
  .full { grid-column: 1 / -1; }
  dt { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; opacity: 0.6; }
  dd { margin: 0.2rem 0 0; font-weight: 500; white-space: pre-wrap; }
}
.plain-list {
  margin: 0;
  padding-left: 1.1rem;
  li { margin: 0.25rem 0; }
}
.att-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  li {
    display: flex;
    gap: 0.65rem;
    align-items: center;
    flex-wrap: wrap;
    padding: 0.5rem 0.65rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
  }
  em { font-style: normal; opacity: 0.55; font-size: 0.8rem; }
}
.actions { display: flex; justify-content: flex-end; margin-top: 0.5rem; }
@media (max-width: 640px) {
  .meta-grid { grid-template-columns: 1fr; }
}
</style>
