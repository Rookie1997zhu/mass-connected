<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import DOMPurify from 'dompurify'
import PageShell from '../../components/PageShell.vue'
import DimAnnotationLayer from '../../components/packaging/DimAnnotationLayer.vue'
import { convertSimpleQuote, createSimpleQuote, fetchFefcoCatalog } from '../../api'
import {
  buildPreview,
  buildQuoteInputs,
  computeGeometry,
  downloadTextFile,
  exportDxf,
  fromMm,
  get0201DimAnnotations,
  renderPreviewLinesSvg,
} from '../../lib/packaging/boxEngine'
import { exportDielineAi, exportDielinePdf } from '../../lib/packaging/dielineExport'
import { categoriesWithTemplates, defaultDimsForTemplate, getBoxTemplate, getEngineKey, resetFefcoCatalog, setFefcoCatalogFromApi } from '../../lib/packaging/fefcoCatalog'
import { useLocaleCurrency } from '../../composables/useLocaleCurrency'

const { t, locale } = useI18n()
const { fromQuote } = useLocaleCurrency()
const router = useRouter()

const fefcoCategories = ref([])
const catalogLoading = ref(false)
const catalogError = ref('')
const activeCategory = ref('')

const productName = ref('')
const unit = ref('mm')
const dimensionType = ref('internal')
const boardType = ref('E')
const boxCode = ref('')
const length = ref('')
const width = ref('')
const height = ref('')
const thickness = ref('')
const quantity = ref('')
const printColors = ref('')

const error = ref('')
const previewError = ref('')
const result = ref(null)
const submitting = ref(false)

const formPinned = ref(false)
const formHovered = ref(false)
const isMobileLayout = ref(false)
let mobileMq = null

const formExpanded = computed(() => isMobileLayout.value || formPinned.value || formHovered.value)

const onFormMouseEnter = () => {
  if (!isMobileLayout.value) formHovered.value = true
}

const onFormMouseLeave = () => {
  if (!formPinned.value) formHovered.value = false
}

onMounted(() => {
  mobileMq = window.matchMedia('(max-width: 960px)')
  const syncMobile = () => {
    isMobileLayout.value = mobileMq.matches
    if (isMobileLayout.value) formHovered.value = false
  }
  syncMobile()
  mobileMq.addEventListener('change', syncMobile)
  loadCatalog()
})

onUnmounted(() => {
  mobileMq?.removeEventListener('change', syncMobile)
})

const activeTemplates = computed(() => {
  const cat = fefcoCategories.value.find((c) => c.code === activeCategory.value)
  return cat?.templates || []
})

const localeKey = computed(() => {
  const map = { 'zh-CN': 'zh', zh: 'zh', en: 'en', ko: 'ko', ja: 'ja' }
  return map[locale.value] || 'en'
})

const templateLabel = (tpl, field = 'name') => {
  if (!tpl) return ''
  const i18n = field === 'name' ? tpl.nameI18n : tpl.descI18n
  const key = field === 'name' ? tpl.nameKey : tpl.descKey
  return i18n?.[localeKey.value] || i18n?.zh || i18n?.en || (key ? t(`packaging.${key}`) : tpl.code)
}

const categoryLabel = (cat, field = 'name') => {
  if (!cat) return ''
  const i18n = field === 'name' ? cat.nameI18n : cat.descI18n
  const key = field === 'name' ? cat.nameKey : cat.descKey
  return i18n?.[localeKey.value] || i18n?.zh || i18n?.en || cat.code || (key ? t(`packaging.${key}`) : '')
}

let suppressDimTypeWatch = false

const applyTemplateDefaults = (tpl, dimType = dimensionType.value) => {
  if (!tpl) return
  const effectiveDimType = dimType || tpl.defaultDimensionType || 'internal'
  const dims = defaultDimsForTemplate(tpl, effectiveDimType)
  if (!dims?.lengthMm || !dims?.widthMm || !dims?.heightMm) return
  length.value = dims.lengthMm
  width.value = dims.widthMm
  height.value = dims.heightMm
  thickness.value = tpl.defaultThicknessMm ?? ''
  unit.value = 'mm'
}

const roundDimForUnit = (mmValue) => {
  const decimals = unit.value === 'in' ? 4 : 1
  return Number(fromMm(mmValue, unit.value).toFixed(decimals))
}

const syncDimsForDimensionType = (newType, oldType) => {
  if (!boxCode.value || !oldType || newType === oldType || !hasBoxDims.value) return
  const tpl = getBoxTemplate(boxCode.value)
  if (!tpl?.previewEnabled) return
  try {
    const geo = computeGeometry({
      boxCode: boxCode.value,
      length: Number(length.value),
      width: Number(width.value),
      height: Number(height.value),
      thickness: Number(thickness.value),
      unit: unit.value,
      dimensionType: oldType,
      boardType: boardType.value,
      quantity: Math.max(1, Number(quantity.value) || 1),
      printColors: Math.max(0, Number(printColors.value) || 0),
    })
    const target = geo[newType]
    if (!target) return
    length.value = roundDimForUnit(target.length)
    width.value = roundDimForUnit(target.width)
    height.value = roundDimForUnit(target.height)
  } catch {
    // 尺寸未通过校验时保持用户输入，避免切换口径时清空表单
  }
}

const isSlottedRsc = computed(() => {
  const ek = getEngineKey(boxCode.value)
  return ek === 'slotted_rsc' || ek === 'folding_shipping'
})

const selectedTemplate = computed(() => getBoxTemplate(boxCode.value))

const canQuote = computed(() => selectedTemplate.value?.quoteEnabled ?? false)

const hasBoxDims = computed(() => {
  const nums = [length.value, width.value, height.value, thickness.value]
  return nums.every((v) => v !== '' && v !== null && Number(v) > 0)
})

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
  if (!boxCode.value) {
    previewError.value = t('packaging.selectBoxFirst')
    return null
  }
  if (!hasBoxDims.value) {
    previewError.value = t('packaging.fillDimsFirst')
    return null
  }
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

const previewLinesSvg = computed(() => {
  if (!preview.value) return ''
  return DOMPurify.sanitize(renderPreviewLinesSvg(preview.value))
})

const dimAnnotations = computed(() => {
  if (!preview.value || !isSlottedRsc.value) return []
  return get0201DimAnnotations(preview.value.geometry, unit.value, dimensionType.value)
})

const onDimFieldUpdate = ({ field, value }) => {
  if (field === 'length') length.value = value
  else if (field === 'width') width.value = value
  else if (field === 'height') height.value = value
}

const canvasAspectStyle = computed(() => {
  if (!preview.value) return undefined
  const { blankWidthMm, blankHeightMm } = preview.value.geometry
  if (!blankWidthMm || !blankHeightMm) return undefined
  return { aspectRatio: `${blankWidthMm} / ${blankHeightMm}` }
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
  suppressDimTypeWatch = true
  boxCode.value = code
  const tpl = getBoxTemplate(code)
  if (tpl?.defaultDimensionType) {
    dimensionType.value = tpl.defaultDimensionType
  }
  applyTemplateDefaults(tpl, dimensionType.value)
  suppressDimTypeWatch = false
}

watch(dimensionType, (newType, oldType) => {
  if (suppressDimTypeWatch) return
  syncDimsForDimensionType(newType, oldType)
})

const loadCatalog = async () => {
  catalogLoading.value = true
  catalogError.value = ''
  try {
    const res = await fetchFefcoCatalog()
    setFefcoCatalogFromApi(res.data || {})
    fefcoCategories.value = categoriesWithTemplates()
    if (!fefcoCategories.value.length) {
      catalogError.value = t('packaging.catalogEmpty')
      activeCategory.value = ''
      return
    }
    if (!fefcoCategories.value.some((c) => c.code === activeCategory.value)) {
      activeCategory.value = fefcoCategories.value[0]?.code || ''
    }
  } catch {
    resetFefcoCatalog()
    fefcoCategories.value = []
    catalogError.value = t('packaging.catalogLoadFailed')
    activeCategory.value = ''
  } finally {
    catalogLoading.value = false
  }
}

const onDownloadDielinePdf = () => {
  if (!preview.value) return
  exportDielinePdf(preview.value)
}

const onDownloadDielineAi = () => {
  if (!preview.value) return
  exportDielineAi(preview.value)
}

const onDownloadDxf = () => {
  if (!preview.value) return
  downloadTextFile(exportDxf(preview.value), `dieline-${boxCode.value}.dxf`, 'application/dxf')
}

const onGenerate = async () => {
  if (!boxCode.value) {
    error.value = t('packaging.selectBoxFirst')
    return
  }
  if (!hasBoxDims.value) {
    error.value = t('packaging.fillDimsFirst')
    return
  }
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
  <PageShell container-wide :title="t('packaging.title')" :subtitle="t('packaging.desc')">
    <div class="pkg-layout" :class="{ 'is-form-expanded': formExpanded }">
      <section
        class="pkg-form card"
        :class="{ 'is-expanded': formExpanded }"
        @mouseenter="onFormMouseEnter"
        @mouseleave="onFormMouseLeave"
      >
        <div class="pkg-form-rail">
          <span class="pkg-rail-title">FEFCO</span>
          <button
            type="button"
            class="pkg-rail-pin"
            :class="{ pinned: formPinned }"
            :title="t('packaging.sidebarPin')"
            :aria-label="t('packaging.sidebarPin')"
            @click="formPinned = !formPinned"
          >
            <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
              <path
                fill="currentColor"
                d="M16 9V4h1c.55 0 1-.45 1-1s-.45-1-1-1H8c-.55 0-1 .45-1 1s.45 1 1 1h1v5c0 1.66-1.34 3-3 3v2h5.97v7l1.03-1 1.03 1v-7H19v-2c-1.66 0-3-1.34-3-3z"
              />
            </svg>
          </button>
          <span class="pkg-rail-hint">{{ t('packaging.sidebarExpand') }}</span>
        </div>

        <div v-show="formExpanded" class="pkg-form-body">
        <div class="pkg-form-library">
          <h2>{{ t('packaging.fefcoLibrary') }}</h2>
          <p class="pkg-lib-desc">{{ t('packaging.fefcoLibraryDesc') }}</p>

          <p v-if="catalogLoading" class="pkg-lib-status">{{ t('packaging.catalogLoading') }}</p>
          <p v-else-if="catalogError" class="page-message page-message--error">{{ catalogError }}</p>

          <div v-else class="pkg-cat-tabs">
            <button
              v-for="cat in fefcoCategories"
              :key="cat.code"
              type="button"
              class="pkg-cat-tab"
              :class="{ active: activeCategory === cat.code }"
              @click="activeCategory = cat.code"
            >
              {{ categoryLabel(cat) }}
            </button>
          </div>

          <div v-if="!catalogLoading && !catalogError" class="pkg-box-grid">
            <button
              v-for="tpl in activeTemplates"
              :key="tpl.code"
              type="button"
              class="pkg-box-card"
              :class="{ active: boxCode === tpl.code, disabled: !tpl.previewEnabled }"
              :title="templateLabel(tpl, 'desc')"
              @click="selectBox(tpl.code)"
            >
              <img v-if="tpl.thumbnailUrl" :src="tpl.thumbnailUrl" class="pkg-box-thumb" alt="" />
              <span class="pkg-box-head">
                <span class="pkg-box-code">FEFCO {{ tpl.code }}</span>
                <span class="pkg-box-name">{{ templateLabel(tpl, 'name') }}</span>
              </span>
              <span class="pkg-box-desc">{{ templateLabel(tpl, 'desc') }}</span>
            </button>
          </div>
        </div>

        <div class="pkg-form-fields">
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
            <input v-model.number="thickness" type="number" min="0.1" step="0.1" :placeholder="t('packaging.dimPlaceholder')" />
          </label>
        </div>

        <div class="pkg-dim-type">
          <span class="pkg-dim-label">{{ t('packaging.dimensionType') }}</span>
          <div class="pkg-dim-chips">
            <button
              type="button"
              class="pkg-dim-chip"
              :class="{ active: dimensionType === 'internal' }"
              @click="dimensionType = 'internal'"
            >
              {{ t('packaging.dimInternal') }}
            </button>
            <button
              type="button"
              class="pkg-dim-chip"
              :class="{ active: dimensionType === 'external' }"
              @click="dimensionType = 'external'"
            >
              {{ t('packaging.dimExternal') }}
            </button>
            <button
              type="button"
              class="pkg-dim-chip"
              :class="{ active: dimensionType === 'manufacturing' }"
              @click="dimensionType = 'manufacturing'"
            >
              {{ t('packaging.dimManufacturing') }}
            </button>
          </div>
        </div>

        <div class="pkg-row">
          <label>{{ t('packaging.length') }}<input v-model.number="length" type="number" min="1" step="0.1" :placeholder="t('packaging.dimPlaceholder')" /></label>
          <label>{{ t('packaging.width') }}<input v-model.number="width" type="number" min="1" step="0.1" :placeholder="t('packaging.dimPlaceholder')" /></label>
        </div>
        <label>{{ t('packaging.height') }}<input v-model.number="height" type="number" min="1" step="0.1" :placeholder="t('packaging.dimPlaceholder')" /></label>

        <label>{{ t('packaging.boardType') }}
          <select v-model="boardType">
            <option value="E">{{ t('packaging.boardE') }}</option>
            <option value="B">{{ t('packaging.boardB') }}</option>
            <option value="C">{{ t('packaging.boardC') }}</option>
            <option value="白卡">{{ t('packaging.boardWhite') }}</option>
          </select>
        </label>

        <div class="pkg-row">
          <label>{{ t('packaging.quantity') }}<input v-model.number="quantity" type="number" min="1" :placeholder="t('packaging.dimPlaceholder')" /></label>
          <label>{{ t('packaging.printColors') }}<input v-model.number="printColors" type="number" min="0" :placeholder="t('packaging.dimPlaceholder')" /></label>
        </div>

        <p v-if="error" class="page-message page-message--error">{{ error }}</p>
        <button type="button" class="btn btn-primary" :disabled="submitting || !preview || !canQuote || !hasBoxDims" @click="onGenerate">
          {{ t('packaging.generate') }}
        </button>
        </div>
        </div>
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
        <div v-else-if="preview" class="pkg-canvas-wrap">
          <div class="pkg-canvas" :style="canvasAspectStyle" v-html="previewLinesSvg" />
          <DimAnnotationLayer
            v-if="isSlottedRsc && dimAnnotations.length"
            :annotations="dimAnnotations"
            :view-box="preview.viewBox"
            :unit="unit"
            @update:field="onDimFieldUpdate"
          />
          <p v-if="isSlottedRsc" class="pkg-dim-hint">{{ t('packaging.dimEditHint') }}</p>
          <div class="pkg-summary-overlay">
            <p><strong>{{ t('packaging.manufacturing') }}:</strong> {{ displaySize(preview.geometry.manufacturing) }}</p>
            <p><strong>{{ t('packaging.internal') }}:</strong> {{ displaySize(preview.geometry.internal) }}</p>
            <p><strong>{{ t('packaging.external') }}:</strong> {{ displaySize(preview.geometry.external) }}</p>
          </div>
        </div>
        <p v-if="preview?.previewMode === 'blank'" class="pkg-stp-hint">{{ t('packaging.previewBlankNote') }}</p>
        <p v-if="preview && preview.previewMode === 'detailed'" class="pkg-stp-hint">{{ t('packaging.structuralReferenceNote') }}</p>

        <div v-if="preview" class="pkg-meta-row">
          <p><strong>{{ t('packaging.blankSize') }}:</strong> {{ preview.geometry.blankWidthMm.toFixed(1) }} × {{ preview.geometry.blankHeightMm.toFixed(1) }} mm</p>
          <p><strong>{{ t('packaging.area') }}:</strong> {{ preview.geometry.unfoldAreaM2.toFixed(4) }} m²</p>
        </div>

        <div v-if="preview" class="pkg-actions">
          <button type="button" class="btn btn-secondary btn-sm" @click="onDownloadDielinePdf">{{ t('packaging.downloadDielinePdf') }}</button>
          <button type="button" class="btn btn-secondary btn-sm" @click="onDownloadDielineAi">{{ t('packaging.downloadDielineAi') }}</button>
          <button type="button" class="btn btn-secondary btn-sm" @click="onDownloadDxf">{{ t('packaging.downloadDxf') }}</button>
          <a
            v-if="selectedTemplate?.productionAssetUrl"
            :href="selectedTemplate.productionAssetUrl"
            target="_blank"
            rel="noopener"
            class="btn btn-secondary btn-sm"
          >{{ t('packaging.downloadProductionAsset') }}</a>
        </div>
      </section>

      <section v-if="result" class="pkg-result card">
        <h2>{{ t('simpleQuote.result') }}</h2>
        <p class="pkg-no">{{ result.quote_no }}</p>
        <ul class="pkg-breakdown">
          <li v-for="(item, i) in result.result?.breakdown || []" :key="i">
            <span>{{ item.label }}</span><span>{{ fromQuote(item.amount, result) }}</span>
          </li>
        </ul>
        <p class="pkg-total">{{ t('simpleQuote.total') }}: <strong>{{ fromQuote(result.total_amount, result) }}</strong></p>
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
.pkg-layout {
  display: grid;
  grid-template-columns: var(--pkg-rail-width, 52px) minmax(0, 1fr);
  gap: var(--space-lg);
  align-items: stretch;
  transition: grid-template-columns 0.22s var(--ease-out, ease-out);

  &.is-form-expanded {
    --pkg-rail-width: clamp(220px, 22vw, 260px);
  }
}

.card {
  padding: var(--space-xl);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.pkg-form {
  display: flex;
  flex-direction: row;
  gap: 0;
  padding: 0;
  position: sticky;
  top: calc(var(--header-height) + 1rem);
  align-self: start;
  max-height: calc(100vh - var(--header-height) - 2rem);
  overflow: hidden;
  min-width: 0;

  &.is-expanded {
    padding: var(--space-lg);
    flex-direction: column;
    gap: 0;
  }

  h2 {
    margin: 0;
    font-size: 0.95rem;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-size: 0.8125rem;
  }

  select,
  input {
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
    padding: 0.45rem 0.5rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
  }

  .btn {
    width: 100%;
  }
}

.pkg-form-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: 0.5rem;
  width: 52px;
  flex-shrink: 0;
  padding: var(--space-md) 0.35rem;
  border-right: 1px solid transparent;

  .is-expanded & {
    display: none;
  }
}

.pkg-rail-title {
  writing-mode: vertical-rl;
  text-orientation: mixed;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--color-primary, #2563eb);
}

.pkg-rail-pin {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg, #fff);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: color var(--duration-fast), border-color var(--duration-fast), background var(--duration-fast);

  &:hover,
  &.pinned {
    color: var(--color-primary, #2563eb);
    border-color: var(--color-primary, #2563eb);
    background: rgba(37, 99, 235, 0.06);
  }
}

.pkg-rail-hint {
  writing-mode: vertical-rl;
  font-size: 0.62rem;
  color: var(--color-text-muted);
  line-height: 1.2;
  text-align: center;
  max-height: 8rem;
  overflow: hidden;
}

.pkg-form-body {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow: hidden;
  overflow-x: hidden;
}

.pkg-form-library {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--space-sm);
  min-width: 0;
  overflow-x: hidden;
}

.pkg-form-fields {
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 0;
}

.pkg-lib-desc {
  font-size: 0.78rem;
  color: var(--color-text-muted);
  margin: 0;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pkg-cat-tabs {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  flex-shrink: 0;
}

.pkg-cat-tab {
  width: 100%;
  padding: 0.3rem 0.5rem;
  font-size: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg, #fff);
  cursor: pointer;
  text-align: left;

  &.active {
    border-color: var(--color-primary, #2563eb);
    color: var(--color-primary, #2563eb);
    font-weight: 600;
    background: rgba(37, 99, 235, 0.06);
  }
}

.pkg-box-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.4rem;
  flex-shrink: 0;
}

.pkg-box-card {
  text-align: left;
  padding: 0.5rem 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #fff;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;

  .pkg-box-thumb {
    width: 100%;
    height: 56px;
    object-fit: contain;
    border-radius: 4px;
    background: #f8fafc;
    margin-bottom: 0.15rem;
  }

  &.active {
    border-color: var(--color-primary, #2563eb);
    box-shadow: 0 0 0 1px var(--color-primary, #2563eb);
    background: rgba(37, 99, 235, 0.04);
  }

  &.disabled {
    opacity: 0.72;
  }
}

.pkg-box-head {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  min-width: 0;
}

.pkg-box-code {
  flex-shrink: 0;
  font-size: 0.68rem;
  font-weight: 700;
  color: var(--color-primary, #2563eb);
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  background: rgba(37, 99, 235, 0.08);
}

.pkg-box-name {
  font-size: 0.8rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pkg-box-desc {
  font-size: 0.72rem;
  color: var(--color-text-muted);
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pkg-dim-type {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.pkg-dim-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-heading);
}

.pkg-dim-chips {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.pkg-dim-chip {
  width: 100%;
  flex: none;
  padding: 0.35rem 0.45rem;
  font-size: 0.72rem;
  line-height: 1.2;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg, #fff);
  color: var(--color-text);
  cursor: pointer;
  text-align: center;
  transition: border-color var(--duration-fast), background var(--duration-fast);

  &.active {
    border-color: var(--color-primary, #2563eb);
    color: var(--color-primary, #2563eb);
    font-weight: 600;
    background: rgba(37, 99, 235, 0.08);
    box-shadow: 0 0 0 1px var(--color-primary, #2563eb);
  }
}

.pkg-stp-hint {
  font-size: 0.78rem;
  color: var(--color-text-muted);
  margin: 0;
}

.pkg-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-sm);
}

.pkg-preview {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  min-width: 0;
  min-height: min(82vh, 920px);
}

.pkg-preview-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-sm);

  h2 {
    margin: 0;
    font-size: 1rem;
  }
}

.pkg-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
  font-size: 0.75rem;
}

.legend {
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

.legend--bleed {
  border-color: #22c55e;
  color: #15803d;
}

.legend--cut {
  border-color: #2563eb;
  color: #1d4ed8;
}

.legend--crease {
  border-color: #ef4444;
  color: #b91c1c;
}

.pkg-canvas-wrap {
  position: relative;
  flex: 1;
  min-height: min(78vh, 860px);
  display: flex;
  flex-direction: column;
}

.pkg-dim-hint {
  position: absolute;
  right: 0.75rem;
  bottom: 0.5rem;
  z-index: 2;
  margin: 0;
  font-size: 0.72rem;
  color: var(--color-text-muted);
  pointer-events: none;
}

.pkg-canvas {
  flex: 1;
  width: 100%;
  min-height: min(75vh, 820px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;

  :deep(svg) {
    display: block;
    width: 100%;
    height: 100%;
    min-height: 680px;
  }
}

.pkg-summary-overlay {
  position: absolute;
  top: 0.75rem;
  left: 0.75rem;
  z-index: 2;
  padding: 0.5rem 0.75rem;
  font-size: 0.82rem;
  line-height: 1.45;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  pointer-events: none;

  p {
    margin: 0.15rem 0;
  }
}

.pkg-meta-row {
  font-size: 0.85rem;

  p {
    margin: 0.25rem 0;
  }
}

.pkg-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.pkg-result {
  grid-column: 1 / -1;
}

.pkg-breakdown {
  list-style: none;
  padding: 0;
  margin: 0;

  li {
    display: flex;
    justify-content: space-between;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--color-border);
    font-size: 0.9rem;
  }
}

.pkg-no {
  font-size: 0.85rem;
  opacity: 0.6;
  margin: 0;
}

.pkg-total {
  font-size: 1.1rem;
  margin-top: var(--space-sm);
}

.pkg-krw,
.pkg-meta {
  font-size: 0.9rem;
  color: var(--color-text-muted);
  margin: 0;
}

@media (max-width: 960px) {
  .pkg-layout {
    grid-template-columns: 1fr;

    &.is-form-expanded {
      --pkg-rail-width: 100%;
    }
  }

  .pkg-form {
    position: static;
    max-height: none;
    overflow: visible;
    padding: var(--space-xl);
    flex-direction: column;

    .pkg-form-rail {
      display: none;
    }
  }

  .pkg-form-library {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
  }

  .pkg-form-fields {
    overflow-y: visible;
    padding-right: 0;
  }

  .pkg-lib-desc {
    white-space: normal;
    display: block;
  }

  .pkg-cat-tabs {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .pkg-cat-tab {
    width: auto;
  }

  .pkg-row {
    grid-template-columns: 1fr 1fr;
  }

  .pkg-dim-chips {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .pkg-dim-chip {
    flex: 1 1 calc(33% - 0.3rem);
    width: auto;
  }

  .pkg-box-desc {
    display: block;
    -webkit-line-clamp: unset;
    overflow: visible;
  }

  .pkg-preview {
    min-height: min(70vh, 720px);
  }

  .pkg-canvas-wrap {
    min-height: min(65vh, 640px);
  }

  .pkg-canvas {
    min-height: min(62vh, 600px);

    :deep(svg) {
      min-height: 560px;
    }
  }
}
</style>
