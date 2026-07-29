<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import DimAnnotationLayer from '../../components/packaging/DimAnnotationLayer.vue'
import { downloadTextFile, exportDxf, fromMm } from '../../lib/packaging/boxEngine'
import { exportDielineAi, exportDielinePdf } from '../../lib/packaging/dielineExport'

const PREVIEW_ZOOM_MIN = 0.5
const PREVIEW_ZOOM_MAX = 3
const PREVIEW_ZOOM_STEP = 0.15

const props = defineProps({
  boxCode: { type: String, default: '' },
  unit: { type: String, default: 'mm' },
  previewError: { type: String, default: '' },
  preview: { type: Object, default: null },
  dimAnnotations: { type: Array, default: () => [] },
  dimViewBox: { type: String, default: '' },
  previewLinesSvg: { type: String, default: '' },
  productionAssetUrl: { type: String, default: '' },
})

const emit = defineEmits(['dim-field-update'])

const { t } = useI18n()

const previewZoom = ref(1)
const previewPanX = ref(0)
const previewPanY = ref(0)
const previewTool = ref('select')
const isPanning = ref(false)
const panStart = ref({ x: 0, y: 0, panX: 0, panY: 0 })

const previewTransformStyle = computed(() => ({
  transform: `translate(${previewPanX.value}px, ${previewPanY.value}px) scale(${previewZoom.value})`,
  transformOrigin: 'center center',
}))

const canvasAspectStyle = computed(() => {
  if (!props.preview) return undefined
  const { blankWidthMm, blankHeightMm } = props.preview.geometry
  if (!blankWidthMm || !blankHeightMm) return undefined
  return { aspectRatio: `${blankWidthMm} / ${blankHeightMm}` }
})

const viewportCursorClass = computed(() => {
  if (previewTool.value !== 'pan') return ''
  return isPanning.value ? 'is-panning' : 'is-pan-ready'
})

const displaySize = (size) => {
  const l = fromMm(size.length, props.unit)
  const w = fromMm(size.width, props.unit)
  const h = fromMm(size.height, props.unit)
  const d = props.unit === 'in' ? 4 : 1
  return `${l.toFixed(d)} × ${w.toFixed(d)} × ${h.toFixed(d)} ${props.unit}`
}

const clampZoom = (value) => Math.min(PREVIEW_ZOOM_MAX, Math.max(PREVIEW_ZOOM_MIN, value))

const zoomIn = () => {
  previewZoom.value = clampZoom(Number((previewZoom.value + PREVIEW_ZOOM_STEP).toFixed(2)))
}

const zoomOut = () => {
  previewZoom.value = clampZoom(Number((previewZoom.value - PREVIEW_ZOOM_STEP).toFixed(2)))
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

const onDimFieldUpdate = (payload) => emit('dim-field-update', payload)

const onDownloadDielinePdf = () => {
  if (!props.preview) return
  exportDielinePdf(props.preview)
}

const onDownloadDielineAi = () => {
  if (!props.preview) return
  exportDielineAi(props.preview)
}

const onDownloadDxf = () => {
  if (!props.preview) return
  downloadTextFile(exportDxf(props.preview), `dieline-${props.boxCode}.dxf`, 'application/dxf')
}

onMounted(() => {
  window.addEventListener('mouseup', endPan)
})

onUnmounted(() => {
  window.removeEventListener('mouseup', endPan)
})
</script>

<template>
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
        v-if="productionAssetUrl"
        :href="productionAssetUrl"
        target="_blank"
        rel="noopener"
        class="btn btn-secondary btn-sm"
      >{{ t('packaging.downloadProductionAsset') }}</a>
    </div>
  </section>
</template>

<style scoped lang="scss">
.card {
  padding: var(--space-xl);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
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

@media (max-width: 960px) {
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
