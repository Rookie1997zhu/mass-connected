<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import DOMPurify from 'dompurify'
import PageShell from '../../components/PageShell.vue'
import DimAnnotationLayer from '../../components/packaging/DimAnnotationLayer.vue'
import { convertSimpleQuote, createSimpleQuote, fetchFefcoCatalog } from '../../api'
import {
  buildPreview,
  buildQuoteInputs,
  computeDimViewBox,
  computeGeometry,
  downloadTextFile,
  exportDxf,
  fromMm,
  getDimAnnotations,
  PARAMETRIC_ASSET_REQUIRED,
  renderPreviewLinesSvg,
} from '../../lib/packaging/boxEngine'
import { exportDielineAi, exportDielinePdf } from '../../lib/packaging/dielineExport'
import {
  categoriesWithTemplates,
  defaultDimsForTemplate,
  getBoxTemplate,
  getEngineKey,
  resetFefcoCatalog,
  setFefcoCatalogFromApi,
} from '../../lib/packaging/fefcoCatalog'
import { useLocaleCurrency } from '../../composables/useLocaleCurrency'

const PREVIEW_ZOOM_MIN = 0.5
const PREVIEW_ZOOM_MAX = 3
const PREVIEW_ZOOM_STEP = 0.15

const { t, locale } = useI18n()
const { fromQuote } = useLocaleCurrency()
const router = useRouter()
const route = useRoute()

const catalogLoading = ref(false)
const catalogError = ref('')
const catalogReady = ref(false)

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

const previewZoom = ref(1)
const previewPanX = ref(0)
const previewPanY = ref(0)
const previewTool = ref('select')
const isPanning = ref(false)
const panStart = ref({ x: 0, y: 0, panX: 0, panY: 0 })

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
    // 尺寸未通过校验时保持用户输入
  }
}

const selectedTemplate = computed(() => (boxCode.value ? getBoxTemplate(boxCode.value) : undefined))

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
    previewError.value = t('packaging.noBoxSelected')
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
    const message = err instanceof Error ? err.message : String(err)
    previewError.value =
      message === PARAMETRIC_ASSET_REQUIRED ? t('packaging.parametricAssetRequired') : message || t('packaging.invalidDims')
    return null
  }
})

const dimAnnotations = computed(() => {
  if (!preview.value) return []
  return getDimAnnotations(
    preview.value,
    unit.value,
    dimensionType.value,
    getEngineKey(boxCode.value),
    selectedTemplate.value?.activeParametricAsset,
  )
})

const dimViewBox = computed(() => {
  if (!preview.value) return ''
  return computeDimViewBox(preview.value, dimAnnotations.value)
})

const previewLinesSvg = computed(() => {
  if (!preview.value) return ''
  return DOMPurify.sanitize(renderPreviewLinesSvg(preview.value, dimViewBox.value || preview.value.viewBox))
})

const previewTransformStyle = computed(() => ({
  transform: `translate(${previewPanX.value}px, ${previewPanY.value}px) scale(${previewZoom.value})`,
  transformOrigin: 'center center',
}))

const canvasAspectStyle = computed(() => {
  if (!preview.value) return undefined
  const { blankWidthMm, blankHeightMm } = preview.value.geometry
  if (!blankWidthMm || !blankHeightMm) return undefined
  return { aspectRatio: `${blankWidthMm} / ${blankHeightMm}` }
})

const viewportCursorClass = computed(() => {
  if (previewTool.value !== 'pan') return ''
  return isPanning.value ? 'is-panning' : 'is-pan-ready'
})

const displaySize = (size) => {
  const l = fromMm(size.length, unit.value)
  const w = fromMm(size.width, unit.value)
  const h = fromMm(size.height, unit.value)
  const d = unit.value === 'in' ? 4 : 1
  return `${l.toFixed(d)} × ${w.toFixed(d)} × ${h.toFixed(d)} ${unit.value}`
}

const resetPreviewView = () => {
  previewZoom.value = 1
  previewPanX.value = 0
  previewPanY.value = 0
  isPanning.value = false
}

const clampZoom = (value) => Math.min(PREVIEW_ZOOM_MAX, Math.max(PREVIEW_ZOOM_MIN, value))

const zoomIn = () => {
  previewZoom.value = clampZoom(Number((previewZoom.value + PREVIEW_ZOOM_STEP).toFixed(2)))
}

const zoomOut = () => {
  previewZoom.value = clampZoom(Number((previewZoom.value - PREVIEW_ZOOM_STEP).toFixed(2)))
}

const onDimFieldUpdate = ({ field, value }) => {
  if (field === 'length') length.value = value
  else if (field === 'width') width.value = value
  else if (field === 'height') height.value = value
}

const selectBox = (code) => {
  suppressDimTypeWatch = true
  boxCode.value = code
  const tpl = getBoxTemplate(code)
  if (tpl?.defaultDimensionType) {
    dimensionType.value = tpl.defaultDimensionType
  }
  applyTemplateDefaults(tpl, dimensionType.value)
  suppressDimTypeWatch = false
  resetPreviewView()
}

const initFromRoute = () => {
  const code = String(route.query.code || '').trim()
  if (!code) {
    boxCode.value = ''
    return
  }
  const tpl = getBoxTemplate(code)
  if (!tpl) {
    catalogError.value = t('packaging.boxNotFound')
    boxCode.value = ''
    return
  }
  selectBox(code)
}

const onViewportMouseDown = (event) => {
  if (previewTool.value !== 'pan' || event.button !== 0) return
  isPanning.value = true
  panStart.value = {
    x: event.clientX,
    y: event.clientY,
    panX: previewPanX.value,
    panY: previewPanY.value,
  }
}

const onViewportMouseMove = (event) => {
  if (!isPanning.value) return
  previewPanX.value = panStart.value.panX + (event.clientX - panStart.value.x)
  previewPanY.value = panStart.value.panY + (event.clientY - panStart.value.y)
}

const endPan = () => {
  isPanning.value = false
}

watch([length, width, height, thickness, unit, dimensionType, boxCode], () => {
  error.value = ''
})

watch(dimensionType, (newType, oldType) => {
  if (suppressDimTypeWatch) return
  syncDimsForDimensionType(newType, oldType)
})

watch(
  () => route.query.code,
  () => {
    if (!catalogReady.value) return
    initFromRoute()
  },
)

const loadCatalog = async () => {
  catalogLoading.value = true
  catalogError.value = ''
  try {
    const res = await fetchFefcoCatalog()
    setFefcoCatalogFromApi(res.data || {})
    const cats = categoriesWithTemplates()
    if (!cats.length) {
      catalogError.value = t('packaging.catalogEmpty')
      return
    }
    catalogReady.value = true
    initFromRoute()
  } catch {
    resetFefcoCatalog()
    catalogError.value = t('packaging.catalogLoadFailed')
  } finally {
    catalogLoading.value = false
  }
}

const goToLibrary = () => {
  router.push({ name: 'packaging-library' })
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
    error.value = t('packaging.noBoxSelected')
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

onMounted(() => {
  window.addEventListener('mouseup', endPan)
  loadCatalog()
})

onUnmounted(() => {
  window.removeEventListener('mouseup', endPan)
})
</script>

<template>
  <PageShell container-wide :title="t('packaging.title')" :subtitle="t('packaging.editorPageDesc')">
    <p v-if="catalogLoading" class="pkg-lib-status">{{ t('packaging.catalogLoading') }}</p>
    <p v-else-if="catalogError" class="page-message page-message--error">{{ catalogError }}</p>

    <div v-else-if="!boxCode" class="pkg-no-box card">
      <p>{{ t('packaging.noBoxSelected') }}</p>
      <button type="button" class="btn btn-primary" @click="goToLibrary">{{ t('packaging.backToLibrary') }}</button>
    </div>

    <div v-else class="pkg-layout">
      <section class="pkg-form card">
        <div class="pkg-form-head">
          <div>
            <h2>{{ t('packaging.editParams') }}</h2>
            <p class="pkg-selected-box">
              <span class="pkg-box-code">FEFCO {{ boxCode }}</span>
              <span class="pkg-box-name">{{ templateLabel(selectedTemplate, 'name') }}</span>
            </p>
          </div>
          <button type="button" class="btn btn-secondary btn-sm" @click="goToLibrary">{{ t('packaging.changeBox') }}</button>
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
        <template v-else-if="preview">
          <div
            class="pkg-canvas-viewport"
            :class="viewportCursorClass"
            @mousedown="onViewportMouseDown"
            @mousemove="onViewportMouseMove"
            @mouseleave="endPan"
          >
            <div class="pkg-canvas-stage" :style="previewTransformStyle">
              <div class="pkg-canvas" :style="canvasAspectStyle" v-html="previewLinesSvg" />
              <DimAnnotationLayer
                v-if="dimAnnotations.length"
                class="pkg-dim-layer"
                :class="{ 'is-pan-mode': previewTool === 'pan' }"
                :annotations="dimAnnotations"
                :view-box="dimViewBox || preview.viewBox"
                :unit="unit"
                @update:field="onDimFieldUpdate"
              />
            </div>
            <p v-if="dimAnnotations.length" class="pkg-dim-hint">{{ t('packaging.dimEditHint') }}</p>
            <div class="pkg-summary-overlay">
              <p><strong>{{ t('packaging.manufacturing') }}:</strong> {{ displaySize(preview.geometry.manufacturing) }}</p>
              <p><strong>{{ t('packaging.internal') }}:</strong> {{ displaySize(preview.geometry.internal) }}</p>
              <p><strong>{{ t('packaging.external') }}:</strong> {{ displaySize(preview.geometry.external) }}</p>
            </div>
          </div>

          <div class="pkg-preview-toolbar" role="toolbar" :aria-label="t('packaging.previewToolbar')">
            <button
              type="button"
              class="pkg-toolbar-btn"
              :class="{ active: previewTool === 'select' }"
              :title="t('packaging.previewToolSelect')"
              :aria-label="t('packaging.previewToolSelect')"
              @click="previewTool = 'select'"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                <path fill="currentColor" d="M4 4l7 17 2.5-7.5L21 11z" />
              </svg>
            </button>
            <button
              type="button"
              class="pkg-toolbar-btn"
              :class="{ active: previewTool === 'pan' }"
              :title="t('packaging.previewToolPan')"
              :aria-label="t('packaging.previewToolPan')"
              @click="previewTool = 'pan'"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                <path fill="currentColor" d="M13 6.5c0-1.1.9-2 2-2s2 .9 2 2-.9 2-2 2-2-.9-2-2zm-2 0c0-2.2 1.8-4 4-4s4 1.8 4 4c0 .7-.2 1.4-.5 2l4.8 4.8-1.4 1.4-4.8-4.8c-.6.3-1.3.5-2 .5-2.2 0-4-1.8-4-4zm-5 9.5c0-1.1.9-2 2-2s2 .9 2 2-.9 2-2 2-2-.9-2-2z" />
              </svg>
            </button>
            <span class="pkg-toolbar-divider" aria-hidden="true" />
            <button
              type="button"
              class="pkg-toolbar-btn"
              :title="t('packaging.previewZoomIn')"
              :aria-label="t('packaging.previewZoomIn')"
              @click="zoomIn"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                <path fill="currentColor" d="M19 13H5v-2h14v2z" />
                <path fill="currentColor" d="M13 5v14h2V5h-2z" />
              </svg>
            </button>
            <button
              type="button"
              class="pkg-toolbar-btn"
              :title="t('packaging.previewZoomOut')"
              :aria-label="t('packaging.previewZoomOut')"
              @click="zoomOut"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                <path fill="currentColor" d="M19 13H5v-2h14v2z" />
              </svg>
            </button>
          </div>
        </template>

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
  grid-template-columns: clamp(260px, 24vw, 320px) minmax(0, 1fr);
  gap: var(--space-lg);
  align-items: stretch;
}

.card {
  padding: var(--space-xl);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.pkg-no-box {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-md);
}

.pkg-lib-status {
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

.pkg-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  position: sticky;
  top: calc(var(--header-height) + 1rem);
  align-self: start;
  max-height: calc(100vh - var(--header-height) - 2rem);
  overflow: hidden;
  min-width: 0;

  h2 {
    margin: 0;
    font-size: 1rem;
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

.pkg-form-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-sm);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--color-border);
}

.pkg-selected-box {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin: 0.35rem 0 0;
  font-size: 0.85rem;
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
  font-weight: 600;
}

.pkg-form-fields {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  overflow-y: auto;
  padding-right: 0.15rem;
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
  padding: 0.35rem 0.45rem;
  font-size: 0.72rem;
  line-height: 1.2;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg, #fff);
  color: var(--color-text);
  cursor: pointer;
  text-align: center;

  &.active {
    border-color: var(--color-primary, #2563eb);
    color: var(--color-primary, #2563eb);
    font-weight: 600;
    background: rgba(37, 99, 235, 0.08);
    box-shadow: 0 0 0 1px var(--color-primary, #2563eb);
  }
}

.pkg-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
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

.pkg-canvas-viewport {
  position: relative;
  flex: 1;
  min-height: min(68vh, 760px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #f8fafc;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;

  &.is-pan-ready {
    cursor: grab;
  }

  &.is-panning {
    cursor: grabbing;
  }
}

.pkg-canvas-stage {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: min(65vh, 720px);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.05s ease-out;
  will-change: transform;
}

.pkg-canvas {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;

  :deep(svg) {
    display: block;
    width: 100%;
    height: 100%;
    min-height: 560px;
  }
}

.pkg-dim-layer {
  position: absolute;
  inset: 0;

  &.is-pan-mode {
    pointer-events: none;
  }
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

.pkg-preview-toolbar {
  display: inline-flex;
  align-items: center;
  gap: 0.15rem;
  align-self: center;
  padding: 0.35rem 0.5rem;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
}

.pkg-toolbar-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: none;
  border-radius: 0.45rem;
  background: transparent;
  color: var(--color-text);
  cursor: pointer;

  &:hover {
    background: rgba(15, 23, 42, 0.06);
  }

  &.active {
    background: rgba(15, 23, 42, 0.08);
    color: var(--color-text-heading);
  }
}

.pkg-toolbar-divider {
  width: 1px;
  height: 1.25rem;
  margin: 0 0.15rem;
  background: var(--color-border);
}

.pkg-stp-hint {
  font-size: 0.78rem;
  color: var(--color-text-muted);
  margin: 0;
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

.pkg-meta {
  font-size: 0.9rem;
  color: var(--color-text-muted);
  margin: 0;
}

@media (max-width: 960px) {
  .pkg-layout {
    grid-template-columns: 1fr;
  }

  .pkg-form {
    position: static;
    max-height: none;
  }

  .pkg-dim-chips {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .pkg-dim-chip {
    flex: 1 1 calc(33% - 0.3rem);
    width: auto;
  }

  .pkg-preview {
    min-height: min(70vh, 720px);
  }

  .pkg-canvas-viewport {
    min-height: min(60vh, 600px);
  }

  .pkg-canvas-stage {
    min-height: min(58vh, 560px);
  }
}
</style>
