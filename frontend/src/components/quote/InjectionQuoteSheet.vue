<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import StpViewer3d from './StpViewer3d.vue'
import { INJECTION_MATERIALS, MOLD_MATERIALS, useInjectionQuote } from '../../composables/useInjectionQuote'
import { useLocaleCurrency } from '../../composables/useLocaleCurrency'
import { useAuthStore } from '../../stores/auth'

const productName = defineModel('productName', { type: String, default: '' })

const props = defineProps({
  savedResult: { type: Object, default: null },
})

const emit = defineEmits(['generated', 'convert'])

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const { formatMoney, fromPreview, displayCurrency } = useLocaleCurrency()

/** 内部成本金额仅平台管理员可见；普通会员隐藏红框价格 */
const canSeeInternalAmounts = computed(() => auth.isStaff)

const {
  injection,
  geometry,
  parsing,
  stpInput,
  undercut,
  materialSuggestion,
  ocr,
  ocrParsing,
  ocrError,
  drawingInput,
  preview,
  previewLoading,
  previewError,
  submitting,
  error,
  familyExpanded,
  previewMesh,
  familyMaterialMismatch,
  primaryPart,
  packagingAmount,
  productionAmount,
  shippingAmount,
  shippingHint,
  onMaterialChange,
  onStpSelected,
  onDrawingSelected,
  addPart,
  removePart,
  onGenerate,
  fmt,
  moldTypeLabel,
} = useInjectionQuote({ productName, router, t })

const quoteNo = computed(() => props.savedResult?.quote_no || 'MC-2026-—')

const previewCtx = computed(() => preview.value || props.savedResult?.result || null)

const fmtAmount = (n, digits = 0) => {
  if (n === null || n === undefined || n === '') return '—'
  return fromPreview(n, previewCtx.value, digits)
}

const colorLabel = (color) => {
  const map = {
    normal: t('simpleQuote.colorNormal'),
    transparent: t('simpleQuote.colorTransparent'),
    semi: t('simpleQuote.colorSemi'),
    pantone: t('simpleQuote.colorPantone'),
  }
  return map[color] || color
}

const undercutMetaHint = computed(() => {
  const uc = undercut.value
  if (!uc?.draw_direction) return ''
  const parts = []
  if (uc.confidence) {
    const confidenceKey = {
      high: 'confidenceHigh',
      medium: 'confidenceMedium',
      low: 'confidenceLow',
    }[uc.confidence]
    if (confidenceKey) {
      parts.push(`${t('simpleQuote.confidence')}: ${t(`simpleQuote.${confidenceKey}`)}`)
    }
  }
  if (uc.sampling?.downsampled) {
    parts.push(t('simpleQuote.undercutDownsampled'))
  }
  return parts.join(' · ')
})

const handleGenerate = async () => {
  const data = await onGenerate()
  if (data) emit('generated', data)
}
</script>

<template>
  <div class="iq-sheet">
    <header class="iq-header">
      <div class="iq-header__brand">
        <strong>MASS CONNECTED</strong>
        <span>{{ t('injectionQuote.subtitleEn') }}</span>
      </div>
      <div class="iq-header__divider" />
      <div class="iq-header__title">
        <strong>{{ t('injectionQuote.sheetTitle') }}</strong>
        <span>{{ t('injectionQuote.autoQuotation') }}</span>
      </div>
    </header>

    <div class="iq-meta">
      <label class="iq-meta__item">
        <span>{{ t('injectionQuote.quoteNo') }}</span>
        <input class="iq-highlight" :value="quoteNo" readonly />
      </label>
      <label class="iq-meta__item">
        <span>{{ t('injectionQuote.customer') }}</span>
        <input v-model="productName" class="iq-highlight" type="text" />
      </label>
      <label class="iq-meta__item">
        <span>{{ t('injectionQuote.contact') }}</span>
        <input v-model="injection.contact_person" class="iq-highlight" type="text" />
      </label>
    </div>

    <div class="iq-body">
      <aside class="iq-left">
        <div class="iq-viewer-wrap">
          <StpViewer3d :preview-mesh="previewMesh" :loading="parsing" />
          <button type="button" class="btn btn-sm btn-secondary iq-upload" :disabled="parsing" @click="stpInput?.click()">
            {{ parsing ? t('simpleQuote.parsing') : t('simpleQuote.uploadStp') }}
          </button>
          <input ref="stpInput" type="file" accept=".stp,.step" hidden @change="onStpSelected" />
        </div>
        <div class="iq-file-meta">
          <label>
            {{ t('injectionQuote.materialWeight') }}
            <input class="iq-highlight" :value="primaryPart.weight_g" type="number" min="0" step="0.1" @input="(e) => { primaryPart.weight_g = Number(e.target.value) }" />
            <span class="iq-unit">g</span>
          </label>
          <label>
            {{ t('injectionQuote.fileLabel') }}
            <input v-model="injection.file_name" class="iq-highlight" type="text" placeholder="part.stp" />
          </label>
        </div>
        <div v-if="geometry" class="iq-geo-hint">
          <span>{{ t('simpleQuote.volume') }}: {{ geometry.volume_cm3 }} cm³</span>
          <span v-if="geometry.bbox_mm">{{ t('simpleQuote.dimensions') }}: {{ geometry.bbox_mm.join(' × ') }} mm</span>
        </div>
        <div class="iq-tools">
          <button type="button" class="btn btn-sm btn-secondary" :disabled="ocrParsing" @click="drawingInput?.click()">
            {{ ocrParsing ? t('simpleQuote.ocrParsing') : t('simpleQuote.uploadDrawing') }}
          </button>
          <input ref="drawingInput" type="file" accept=".pdf,.png,.jpg,.jpeg" hidden @change="onDrawingSelected" />
          <p v-if="ocrError" class="page-message page-message--error">{{ ocrError }}</p>
          <p v-if="undercut?.draw_direction" class="iq-suggest">
            {{ t('simpleQuote.drawDirection') }}: {{ undercut.draw_direction }} ·
            {{ t('simpleQuote.sliderSuggest') }}: {{ undercut.suggested_sliders }}
            <em class="iq-badge">{{ t('simpleQuote.needReview') }}</em>
          </p>
          <p v-if="undercutMetaHint" class="iq-suggest-meta">{{ undercutMetaHint }}</p>
          <p v-if="materialSuggestion" class="iq-suggest">
            {{ t('simpleQuote.materialSuggest') }}: {{ materialSuggestion.material }}
            <em class="iq-badge">{{ t('simpleQuote.needReview') }}</em>
          </p>
        </div>
      </aside>

      <section class="iq-right">
        <p v-if="previewError || error" class="page-message page-message--error">{{ previewError || error }}</p>

        <div class="iq-section">
          <div class="iq-section__head">
            <h3>1. {{ t('injectionQuote.moldCostSection') }}</h3>
            <div v-if="canSeeInternalAmounts" class="iq-amount">
              <span class="iq-highlight iq-amount__val">{{ previewLoading ? '—' : fmtAmount(preview?.mold_fee) }}</span>
              <span class="iq-amount__unit">{{ displayCurrency }}</span>
            </div>
          </div>
          <ol class="iq-lines">
            <li>
              <span>1. {{ t('injectionQuote.rawMaterial') }}</span>
              <select v-model="primaryPart.material" class="iq-highlight" @change="onMaterialChange(primaryPart)">
                <option v-for="m in INJECTION_MATERIALS" :key="m" :value="m">{{ m }}</option>
              </select>
            </li>
            <li>
              <span>2. {{ t('injectionQuote.moldKind') }}</span>
              <span class="iq-highlight iq-highlight--text">{{ moldTypeLabel }}</span>
            </li>
            <li>
              <span>3. {{ t('injectionQuote.cavityLabel') }}</span>
              <span class="iq-cavity">
                1 ×
                <input v-model.number="primaryPart.cavity" class="iq-highlight iq-highlight--narrow" type="number" min="1" />
              </span>
            </li>
            <li>
              <span>4. {{ t('injectionQuote.moldMaterialLabel') }}</span>
              <select v-model="injection.mold_material" class="iq-highlight">
                <option v-for="m in MOLD_MATERIALS" :key="m" :value="m">{{ m }}</option>
              </select>
            </li>
          </ol>
          <label class="iq-check">
            <input v-model="injection.is_precision" type="checkbox" />
            {{ t('simpleQuote.precision') }}
          </label>
          <label class="iq-check">
            {{ t('simpleQuote.sliderCount') }}
            <input v-model.number="primaryPart.slider_count" class="iq-highlight iq-highlight--narrow" type="number" min="0" />
          </label>
        </div>

        <div class="iq-section">
          <div class="iq-section__head">
            <h3>2. {{ t('injectionQuote.unitPriceSection') }}</h3>
            <div v-if="canSeeInternalAmounts" class="iq-amount">
              <span class="iq-highlight iq-amount__val">{{ previewLoading ? '—' : fmtAmount(preview?.product_total) }}</span>
              <span class="iq-amount__unit">{{ displayCurrency }}</span>
            </div>
          </div>
          <ol class="iq-lines">
            <li>
              <span>1. {{ t('injectionQuote.perUnitPrice') }}</span>
              <span v-if="canSeeInternalAmounts" class="iq-highlight iq-highlight--text">{{ previewLoading ? '—' : fmtAmount(preview?.parts?.[0]?.unit_price, 4) }}</span>
            </li>
            <li>
              <span>2. {{ t('injectionQuote.colorLabel') }}</span>
              <select v-model="primaryPart.color" class="iq-highlight">
                <option value="normal">{{ t('simpleQuote.colorNormal') }}</option>
                <option value="transparent">{{ t('simpleQuote.colorTransparent') }}</option>
                <option value="semi">{{ t('simpleQuote.colorSemi') }}</option>
                <option value="pantone">{{ t('simpleQuote.colorPantone') }}</option>
              </select>
            </li>
            <li>
              <span>3. {{ t('injectionQuote.productionCost') }}</span>
              <span v-if="canSeeInternalAmounts" class="iq-highlight iq-highlight--text">
                {{ previewLoading ? '—' : productionAmount != null ? fmtAmount(productionAmount, 4) : t('injectionQuote.shippingPending') }}
              </span>
            </li>
            <li>
              <span>4. {{ t('injectionQuote.packagingCost') }}</span>
              <span v-if="canSeeInternalAmounts" class="iq-highlight iq-highlight--text">{{ packagingAmount != null ? fmtAmount(packagingAmount, 4) : '—' }}</span>
            </li>
            <li>
              <span>5. {{ t('injectionQuote.shippingCost') }}</span>
              <span v-if="canSeeInternalAmounts" class="iq-highlight iq-highlight--text">
                {{ previewLoading ? '—' : shippingAmount != null ? fmtAmount(shippingAmount) : t('injectionQuote.shippingPending') }}
              </span>
            </li>
          </ol>
          <p v-if="canSeeInternalAmounts && shippingHint" class="iq-shipping-hint">{{ shippingHint }}</p>
          <label class="iq-check">
            {{ t('simpleQuote.quantity') }}
            <input v-model.number="primaryPart.quantity" class="iq-highlight iq-highlight--narrow" type="number" min="1" />
          </label>
        </div>

        <div class="iq-footer">
          <div class="iq-footer__row">
            <span>VAT</span>
            <span class="iq-highlight iq-highlight--text">—</span>
            <span class="iq-footer__sep">/</span>
            <span>{{ t('injectionQuote.grandTotal') }}</span>
            <template v-if="canSeeInternalAmounts">
              <span class="iq-highlight iq-amount__val">{{ previewLoading ? '—' : fmtAmount(preview?.total) }}</span>
              <span>{{ displayCurrency }}</span>
            </template>
          </div>
          <p class="iq-moq">{{ t('simpleQuote.moqHint', { kg: preview?.moq_kg || 25 }) }}</p>
        </div>

        <details class="iq-family" :open="familyExpanded || injection.parts.length > 1">
          <summary>{{ t('simpleQuote.family') }}</summary>
          <p v-if="familyMaterialMismatch" class="page-message page-message--error">{{ t('simpleQuote.familyMaterialHint') }}</p>
          <div v-for="(p, i) in injection.parts" :key="i" class="iq-family-part">
            <div class="iq-family-part__head">
              <span>{{ t('simpleQuote.part') }} {{ i + 1 }}</span>
              <button v-if="injection.parts.length > 1" type="button" class="btn btn-sm btn-secondary" @click="removePart(i)">{{ t('simpleQuote.removePart') }}</button>
            </div>
            <div class="iq-family-grid">
              <select v-model="p.material" @change="onMaterialChange(p)">
                <option v-for="m in INJECTION_MATERIALS" :key="m" :value="m">{{ m }}</option>
              </select>
              <select v-model="p.color">
                <option value="normal">{{ t('simpleQuote.colorNormal') }}</option>
                <option value="transparent">{{ t('simpleQuote.colorTransparent') }}</option>
                <option value="semi">{{ t('simpleQuote.colorSemi') }}</option>
                <option value="pantone">{{ t('simpleQuote.colorPantone') }}</option>
              </select>
              <input v-model.number="p.weight_g" type="number" min="0" step="0.1" :placeholder="t('simpleQuote.weight')" />
              <input v-model.number="p.cavity" type="number" min="1" :placeholder="t('simpleQuote.cavity')" />
              <input v-model.number="p.slider_count" type="number" min="0" :placeholder="t('simpleQuote.sliderCount')" />
              <input v-model.number="p.quantity" type="number" min="1" :placeholder="t('simpleQuote.quantity')" />
            </div>
            <p v-if="canSeeInternalAmounts && preview?.parts?.[i]" class="iq-family-price">
              {{ colorLabel(p.color) }} · {{ fmtAmount(preview.parts[i].unit_price, 4) }}
            </p>
          </div>
          <button type="button" class="btn btn-sm btn-secondary" @click="addPart">+ {{ t('simpleQuote.addPart') }}</button>
        </details>

        <div class="iq-actions">
          <button type="button" class="btn btn-primary" :disabled="submitting" @click="handleGenerate">
            {{ submitting ? t('injectionQuote.generating') : t('simpleQuote.generate') }}
          </button>
          <template v-if="savedResult">
            <a v-if="savedResult.pdf_url" :href="savedResult.pdf_url" target="_blank" rel="noopener" class="btn btn-secondary btn-sm">PDF</a>
            <button v-if="!savedResult.converted_rfq" type="button" class="btn btn-secondary btn-sm" @click="emit('convert')">
              {{ t('simpleQuote.convert') }}
            </button>
          </template>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped lang="scss">
.iq-sheet {
  border: 2px solid #111;
  background: #fff;
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}
.iq-header {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: var(--space-md);
  padding-bottom: var(--space-md);
  border-bottom: 3px solid #111;
  strong { font-size: 1.25rem; letter-spacing: 0.02em; }
  span { display: block; font-size: 0.85rem; color: var(--color-text-muted); }
  &__brand { text-align: left; }
  &__title { text-align: right; }
  &__divider { width: 1px; height: 3rem; background: #111; justify-self: center; }
}
.iq-meta {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-md);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid #111;
  &__item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    span { white-space: nowrap; }
  }
}
.iq-highlight {
  box-sizing: border-box;
  background: #ffff99;
  border: 1px solid #ccc;
  padding: 0.35rem 0.5rem;
  font-size: 0.875rem;
  .iq-meta__item &,
  .iq-file-meta label & {
    flex: 1;
    min-width: 0;
  }
  .iq-lines li > &,
  .iq-lines li > select.iq-highlight,
  .iq-lines li > input.iq-highlight {
    width: 100%;
    max-width: 100%;
    min-width: 0;
  }
  &--text {
    display: block;
    width: 100%;
    max-width: 100%;
    min-width: 0;
    text-align: right;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  &--narrow { max-width: 5rem; width: 100%; flex: none; }
}
.iq-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr);
  gap: var(--space-xl);
  align-items: start;
  min-width: 0;
}
.iq-left { display: flex; flex-direction: column; gap: var(--space-md); min-width: 0; }
.iq-viewer-wrap { display: flex; flex-direction: column; gap: 0.5rem; }
.iq-upload { align-self: flex-start; }
.iq-file-meta {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
  label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    min-width: 0;
    span:first-child { flex-shrink: 0; }
    input { overflow: hidden; text-overflow: ellipsis; }
  }
  .iq-unit { font-size: 0.85rem; flex-shrink: 0; }
}
.iq-geo-hint, .iq-suggest { font-size: 0.78rem; color: var(--color-text-muted); margin: 0; display: flex; flex-wrap: wrap; gap: 0.75rem; min-width: 0; word-break: break-word; }
.iq-suggest-meta { font-size: 0.68rem; color: var(--color-text-muted); margin: -0.15rem 0 0; opacity: 0.85; line-height: 1.35; }
.iq-badge { font-style: normal; font-size: 0.7rem; padding: 0.05rem 0.35rem; border-radius: var(--radius-sm); background: #fff3cd; color: #8a6d00; }
.iq-tools { display: flex; flex-direction: column; gap: 0.35rem; }
.iq-right { display: flex; flex-direction: column; gap: var(--space-md); min-width: 0; }
.iq-section {
  border-top: 1px solid #111;
  padding-top: var(--space-sm);
  min-width: 0;
  &__head {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.75rem;
    align-items: center;
    margin-bottom: 0.5rem;
    min-width: 0;
    h3 { margin: 0; font-size: 1rem; min-width: 0; }
  }
}
.iq-amount {
  display: flex;
  align-items: baseline;
  gap: 0.35rem;
  flex-shrink: 0;
  max-width: 100%;
  &__val {
    font-weight: 700;
    min-width: 0;
    max-width: 9rem;
    text-align: right;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  &__unit { font-size: 0.85rem; flex-shrink: 0; }
}
.iq-lines {
  list-style: none;
  margin: 0;
  padding: 0;
  min-width: 0;
  li {
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
    gap: 0.5rem;
    align-items: center;
    padding: 0.35rem 0;
    font-size: 0.875rem;
    border-bottom: 1px solid #eee;
    min-width: 0;
    > span:first-child { min-width: 0; }
    > .iq-cavity { min-width: 0; max-width: 100%; justify-self: stretch; }
  }
}
.iq-cavity { display: flex; align-items: center; gap: 0.35rem; min-width: 0; }
.iq-check {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  margin-top: 0.35rem;
}
.iq-footer {
  border-top: 2px solid #111;
  padding-top: var(--space-sm);
  min-width: 0;
  &__row {
    display: grid;
    grid-template-columns: auto minmax(2.5rem, auto) auto minmax(0, 1fr) auto auto;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.95rem;
    font-weight: 600;
    min-width: 0;
    .iq-highlight--text,
    .iq-amount__val {
      justify-self: end;
      max-width: 100%;
    }
  }
  &__sep { opacity: 0.5; }
}
.iq-krw, .iq-moq { font-size: 0.8rem; color: var(--color-text-muted); margin: 0.25rem 0 0; }
.iq-family {
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-sm) var(--space-md);
  summary { cursor: pointer; font-weight: 600; font-size: 0.9rem; }
}
.iq-family-part {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 0.5rem;
  margin: 0.5rem 0;
  &__head { display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.35rem; }
}
.iq-family-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.35rem;
  min-width: 0;
  select, input {
    padding: 0.35rem;
    font-size: 0.8rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    min-width: 0;
    width: 100%;
    box-sizing: border-box;
  }
}
.iq-family-price { font-size: 0.78rem; color: var(--color-text-muted); margin: 0.35rem 0 0; }
.iq-actions { display: flex; gap: var(--space-md); flex-wrap: wrap; margin-top: var(--space-sm); }
.iq-shipping-hint { font-size: 0.75rem; color: var(--color-text-muted); margin: 0.25rem 0 0; }

@media (max-width: 960px) {
  .iq-body { grid-template-columns: 1fr; }
  .iq-meta { grid-template-columns: 1fr; }
  .iq-header { grid-template-columns: 1fr; text-align: center; &__brand, &__title { text-align: center; } &__divider { display: none; } }
}
</style>
