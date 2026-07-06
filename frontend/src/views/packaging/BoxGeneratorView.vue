<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import DOMPurify from 'dompurify'
import PageShell from '../../components/PageShell.vue'
import { convertSimpleQuote, createSimpleQuote } from '../../api'
import {
  buildPreview,
  buildQuoteInputs,
  downloadTextFile,
  exportDxf,
  exportSvg,
  fromMm,
  renderPreviewSvg,
} from '../../lib/packaging/boxEngine'
import { categoriesWithTemplates, getBoxTemplate } from '../../lib/packaging/fefcoCatalog'

const { t } = useI18n()
const router = useRouter()

const fefcoCategories = categoriesWithTemplates()
const activeCategory = ref(fefcoCategories[0]?.code || '0200')

const productName = ref('')
const unit = ref('mm')
const dimensionType = ref('internal')
const boardType = ref('E')
const boxCode = ref('0201')
const length = ref(200)
const width = ref(150)
const height = ref(100)
const thickness = ref(1.5)
const quantity = ref(1000)
const printColors = ref(1)

const error = ref('')
const previewError = ref('')
const result = ref(null)
const submitting = ref(false)

const activeTemplates = computed(() => {
  const cat = fefcoCategories.find((c) => c.code === activeCategory.value)
  return cat?.templates || []
})

const selectedTemplate = computed(() => getBoxTemplate(boxCode.value))

const canQuote = computed(() => selectedTemplate.value?.quoteEnabled ?? false)

const params = computed(() => ({
  boxCode: boxCode.value,
  length: Number(length.value),
  width: Number(width.value),
  height: Number(height.value),
  thickness: Number(thickness.value),
  unit: unit.value,
  dimensionType: dimensionType.value,
  boardType: boardType.value,
  quantity: Math.max(1, Number(quantity.value) || 1),
  printColors: Math.max(0, Number(printColors.value) || 0),
}))

const preview = computed(() => {
  previewError.value = ''
  const tpl = getBoxTemplate(boxCode.value)
  if (!tpl?.previewEnabled) {
    previewError.value = t('packaging.previewNotReady')
    return null
  }
  try {
    return buildPreview(params.value)
  } catch (err) {
    previewError.value = err.message || t('packaging.invalidDims')
    return null
  }
})

const previewSvg = computed(() => {
  if (!preview.value) return ''
  return DOMPurify.sanitize(renderPreviewSvg(preview.value, unit.value))
})

const fmt = (value, decimals = 0) => {
  const n = Number(value)
  if (Number.isNaN(n)) return '-'
  return decimals ? n.toFixed(decimals) : Math.round(n).toLocaleString()
}

const displaySize = (size) => {
  const l = fromMm(size.length, unit.value)
  const w = fromMm(size.width, unit.value)
  const h = fromMm(size.height, unit.value)
  const d = unit.value === 'in' ? 4 : 1
  return `${l.toFixed(d)} × ${w.toFixed(d)} × ${h.toFixed(d)} ${unit.value}`
}

watch([length, width, height, thickness, unit, dimensionType, boxCode], () => {
  error.value = ''
})

const selectBox = (code) => {
  boxCode.value = code
}

const onDownloadSvg = () => {
  if (!preview.value) return
  downloadTextFile(exportSvg(preview.value), `dieline-${boxCode.value}.svg`, 'image/svg+xml')
}

const onDownloadDxf = () => {
  if (!preview.value) return
  downloadTextFile(exportDxf(preview.value), `dieline-${boxCode.value}.dxf`, 'application/dxf')
}

const onGenerate = async () => {
  if (!canQuote.value) {
    error.value = t('packaging.previewNotReady')
    return
  }
  if (!preview.value) {
    error.value = previewError.value || t('packaging.invalidDims')
    return
  }
  error.value = ''
  submitting.value = true
  result.value = null
  try {
    const res = await createSimpleQuote({
      quote_type: 'paper_box',
      product_name: productName.value,
      inputs: buildQuoteInputs(params.value),
    })
    result.value = res.data
  } catch (err) {
    error.value = err.message || t('packaging.failed')
  } finally {
    submitting.value = false
  }
}

const onConvert = async () => {
  if (!result.value?.id) return
  try {
    const res = await convertSimpleQuote(result.value.id, {})
    router.push({ name: 'my-rfq-detail', params: { id: res.data.rfq_id } })
  } catch (err) {
    error.value = err.message || t('packaging.failed')
  }
}
</script>

<template>
  <PageShell :title="t('packaging.title')" :subtitle="t('packaging.desc')">
    <div class="pkg-layout">
      <section class="pkg-form card">
        <h2>{{ t('packaging.fefcoLibrary') }}</h2>
        <p class="pkg-lib-desc">{{ t('packaging.fefcoLibraryDesc') }}</p>

        <div class="pkg-cat-tabs">
          <button
            v-for="cat in fefcoCategories"
            :key="cat.code"
            type="button"
            class="pkg-cat-tab"
            :class="{ active: activeCategory === cat.code }"
            @click="activeCategory = cat.code"
          >
            {{ t(`packaging.${cat.nameKey}`) }}
          </button>
        </div>

        <div class="pkg-box-grid">
          <button
            v-for="tpl in activeTemplates"
            :key="tpl.code"
            type="button"
            class="pkg-box-card"
            :class="{ active: boxCode === tpl.code, disabled: !tpl.previewEnabled }"
            @click="selectBox(tpl.code)"
          >
            <span class="pkg-box-code">FEFCO {{ tpl.code }}</span>
            <span class="pkg-box-name">{{ t(`packaging.${tpl.nameKey}`) }}</span>
            <span class="pkg-box-desc">{{ t(`packaging.${tpl.descKey}`) }}</span>
            <span v-if="!tpl.quoteEnabled" class="pkg-box-badge">{{ t('packaging.comingSoon') }}</span>
            <span v-else class="pkg-box-badge pkg-box-badge--ok">{{ tpl.priority }}</span>
          </button>
        </div>

        <label>{{ t('packaging.productName') }}
          <input v-model="productName" type="text" />
        </label>

        <div class="pkg-row">
          <label>{{ t('packaging.unit') }}
            <select v-model="unit">
              <option value="mm">{{ t('packaging.unitMm') }}</option>
              <option value="in">{{ t('packaging.unitIn') }}</option>
            </select>
          </label>
          <label>{{ t('packaging.thickness') }}
            <input v-model.number="thickness" type="number" min="0.1" step="0.1" />
          </label>
        </div>

        <fieldset class="pkg-fieldset">
          <legend>{{ t('packaging.dimensionType') }}</legend>
          <label class="pkg-radio"><input v-model="dimensionType" type="radio" value="internal" /> {{ t('packaging.dimInternal') }}</label>
          <label class="pkg-radio"><input v-model="dimensionType" type="radio" value="external" /> {{ t('packaging.dimExternal') }}</label>
          <label class="pkg-radio"><input v-model="dimensionType" type="radio" value="manufacturing" /> {{ t('packaging.dimManufacturing') }}</label>
        </fieldset>

        <div class="pkg-row">
          <label>{{ t('packaging.length') }}<input v-model.number="length" type="number" min="1" step="0.1" /></label>
          <label>{{ t('packaging.width') }}<input v-model.number="width" type="number" min="1" step="0.1" /></label>
        </div>
        <label>{{ t('packaging.height') }}<input v-model.number="height" type="number" min="1" step="0.1" /></label>

        <label>{{ t('packaging.boardType') }}
          <select v-model="boardType">
            <option value="E">{{ t('packaging.boardE') }}</option>
            <option value="B">{{ t('packaging.boardB') }}</option>
            <option value="C">{{ t('packaging.boardC') }}</option>
            <option value="白卡">{{ t('packaging.boardWhite') }}</option>
          </select>
        </label>

        <div class="pkg-row">
          <label>{{ t('packaging.quantity') }}<input v-model.number="quantity" type="number" min="1" /></label>
          <label>{{ t('packaging.printColors') }}<input v-model.number="printColors" type="number" min="0" /></label>
        </div>

        <p v-if="error" class="page-message page-message--error">{{ error }}</p>
        <button type="button" class="btn btn-primary" :disabled="submitting || !preview || !canQuote" @click="onGenerate">
          {{ t('packaging.generate') }}
        </button>
      </section>

      <section class="pkg-preview card">
        <div class="pkg-preview-head">
          <h2>{{ t('packaging.preview') }}</h2>
          <div class="pkg-legend">
            <span class="legend legend--bleed">{{ t('packaging.legendBleed') }}</span>
            <span class="legend legend--cut">{{ t('packaging.legendCut') }}</span>
            <span class="legend legend--crease">{{ t('packaging.legendCrease') }}</span>
          </div>
        </div>

        <p v-if="previewError" class="page-message page-message--error">{{ previewError }}</p>
        <div v-else-if="preview" class="pkg-canvas" v-html="previewSvg" />
        <p v-if="preview?.previewMode === 'blank'" class="pkg-stp-hint">{{ t('packaging.previewBlankNote') }}</p>

        <div v-if="preview" class="pkg-summary">
          <h3>{{ t('packaging.sizeSummary') }}</h3>
          <p><strong>{{ t('packaging.manufacturing') }}:</strong> {{ displaySize(preview.geometry.manufacturing) }}</p>
          <p><strong>{{ t('packaging.internal') }}:</strong> {{ displaySize(preview.geometry.internal) }}</p>
          <p><strong>{{ t('packaging.external') }}:</strong> {{ displaySize(preview.geometry.external) }}</p>
          <p><strong>{{ t('packaging.blankSize') }}:</strong> {{ preview.geometry.blankWidthMm.toFixed(1) }} × {{ preview.geometry.blankHeightMm.toFixed(1) }} mm</p>
          <p><strong>{{ t('packaging.area') }}:</strong> {{ preview.geometry.unfoldAreaM2.toFixed(4) }} m²</p>
        </div>

        <div v-if="preview" class="pkg-actions">
          <button type="button" class="btn btn-secondary btn-sm" @click="onDownloadSvg">{{ t('packaging.downloadSvg') }}</button>
          <button type="button" class="btn btn-secondary btn-sm" @click="onDownloadDxf">{{ t('packaging.downloadDxf') }}</button>
        </div>
      </section>

      <section v-if="result" class="pkg-result card">
        <h2>{{ t('simpleQuote.result') }}</h2>
        <p class="pkg-no">{{ result.quote_no }}</p>
        <ul class="pkg-breakdown">
          <li v-for="(item, i) in result.result?.breakdown || []" :key="i">
            <span>{{ item.label }}</span><span>{{ result.currency }} {{ fmt(item.amount) }}</span>
          </li>
        </ul>
        <p class="pkg-total">{{ t('simpleQuote.total') }}: <strong>{{ result.currency }} {{ fmt(result.total_amount) }}</strong></p>
        <p v-if="result.result?.total_krw" class="pkg-krw">{{ t('simpleQuote.krwConverted') }}: KRW {{ fmt(result.result.total_krw) }}</p>
        <p class="pkg-meta">{{ t('packaging.area') }}: {{ result.result?.unfold_area_m2 }} m²</p>
        <div class="pkg-actions">
          <a v-if="result.pdf_url" :href="result.pdf_url" target="_blank" rel="noopener" class="btn btn-secondary btn-sm">PDF</a>
          <button v-if="!result.converted_rfq" type="button" class="btn btn-primary btn-sm" @click="onConvert">{{ t('packaging.convert') }}</button>
        </div>
      </section>
    </div>
  </PageShell>
</template>

<style scoped lang="scss">
.pkg-layout { display: grid; grid-template-columns: minmax(280px, 360px) 1fr; gap: var(--space-2xl); align-items: start; }
.card { padding: var(--space-xl); border: 1px solid var(--color-border); border-radius: var(--radius-md); }
.pkg-form { display: flex; flex-direction: column; gap: var(--space-md); label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.875rem; } select, input { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); } }
.pkg-lib-desc { font-size: 0.82rem; color: var(--color-text-muted); margin: 0 0 0.25rem; }
.pkg-cat-tabs { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.pkg-cat-tab { padding: 0.35rem 0.65rem; font-size: 0.78rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); background: var(--color-bg, #fff); cursor: pointer; &.active { border-color: var(--color-primary, #2563eb); color: var(--color-primary, #2563eb); font-weight: 600; } }
.pkg-box-grid { display: grid; grid-template-columns: 1fr; gap: 0.5rem; max-height: 280px; overflow-y: auto; margin-bottom: 0.25rem; }
.pkg-box-card { text-align: left; padding: 0.65rem 0.75rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); background: #fff; cursor: pointer; display: flex; flex-direction: column; gap: 0.2rem; &.active { border-color: var(--color-primary, #2563eb); box-shadow: 0 0 0 1px var(--color-primary, #2563eb); } &.disabled { opacity: 0.72; } }
.pkg-box-code { font-size: 0.72rem; font-weight: 700; color: var(--color-primary, #2563eb); }
.pkg-box-name { font-size: 0.88rem; font-weight: 600; }
.pkg-box-desc { font-size: 0.75rem; color: var(--color-text-muted); line-height: 1.35; }
.pkg-box-badge { align-self: flex-start; font-size: 0.68rem; padding: 0.1rem 0.4rem; border-radius: 999px; background: #f1f5f9; color: #64748b; margin-top: 0.15rem; &--ok { background: #ecfdf5; color: #15803d; } }
.pkg-stp-hint { font-size: 0.78rem; color: var(--color-text-muted); margin: 0; }
.pkg-row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md); }
.pkg-fieldset { border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: var(--space-md); display: flex; flex-direction: column; gap: 0.35rem; legend { font-size: 0.85rem; font-weight: 600; } }
.pkg-radio { flex-direction: row !important; align-items: center; gap: 0.5rem !important; }
.pkg-preview { display: flex; flex-direction: column; gap: var(--space-md); min-height: 420px; }
.pkg-preview-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: var(--space-sm); h2 { margin: 0; font-size: 1rem; } }
.pkg-legend { display: flex; flex-wrap: wrap; gap: var(--space-sm); font-size: 0.75rem; }
.legend { padding: 0.15rem 0.5rem; border-radius: var(--radius-sm); border: 1px solid var(--color-border); }
.legend--bleed { border-color: #22c55e; color: #15803d; }
.legend--cut { border-color: #2563eb; color: #1d4ed8; }
.legend--crease { border-color: #ef4444; color: #b91c1c; }
.pkg-canvas { flex: 1; min-height: 320px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); overflow: auto; background: #f8fafc; :deep(svg) { display: block; min-height: 300px; } }
.pkg-summary { font-size: 0.85rem; p { margin: 0.25rem 0; } h3 { margin: 0 0 0.35rem; font-size: 0.9rem; } }
.pkg-actions { display: flex; flex-wrap: wrap; gap: var(--space-sm); }
.pkg-result { grid-column: 1 / -1; }
.pkg-breakdown { list-style: none; padding: 0; margin: 0; li { display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--color-border); font-size: 0.9rem; } }
.pkg-no { font-size: 0.85rem; opacity: 0.6; margin: 0; }
.pkg-total { font-size: 1.1rem; margin-top: var(--space-sm); }
.pkg-krw, .pkg-meta { font-size: 0.9rem; color: var(--color-text-muted); margin: 0; }
@media (max-width: 960px) { .pkg-layout { grid-template-columns: 1fr; } }
</style>
