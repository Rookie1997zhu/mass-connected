<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  activateDielineTemplateAsset,
  deleteDielineCategory,
  deleteDielineTemplateAsset,
  deleteDielineTemplate,
  fetchDielineTemplateAssets,
  fetchDielineCategories,
  fetchDielineTemplates,
  saveDielineCategory,
  saveDielineTemplate,
  updateDielineTemplateAsset,
  updateDielineCategory,
  updateDielineTemplate,
  uploadDielineTemplateAsset,
} from '../api'

const { t } = useI18n()
const items = ref([])
const categories = ref([])
const dialog = ref(false)
const categoryDialog = ref(false)
const assetDialog = ref(false)
const submitting = ref(false)
const categorySubmitting = ref(false)
const assetSubmitting = ref(false)
const editingId = ref(null)
const editingCategoryId = ref(null)
const assetTemplate = ref(null)
const assets = ref([])
const selectedAssetId = ref(null)
const selectedRole = ref('cut')
const assetToolMode = ref('line_role')
const selectedDimField = ref('length')
const selectedDimDrawMode = ref('entity')
const dimensionAnnotations = ref([])
const pendingDimPoint = ref(null)
const entityRoles = ref({})
const assetUpload = ref({
  file: null,
  base_length: 200,
  base_width: 150,
  base_height: 100,
  base_thickness: 1.5,
})
const assetDialogFullscreen = ref(true)
const assetSidebarCollapsed = ref(false)
const canvasZoom = ref(1)
const canvasPan = ref({ x: 0, y: 0 })
const isPanning = ref(false)
const spacePressed = ref(false)
const panStart = ref(null)
const assetSvgRef = ref(null)

const CANVAS_ZOOM_MIN = 0.2
const CANVAS_ZOOM_MAX = 8
const CANVAS_ZOOM_STEP = 1.2

const engineOptions = [
  { value: 'slotted_rsc', label: '0201 Slotted RSC' },
  { value: 'folding_shipping', label: '0210 Folding shipping box' },
  { value: 'mailer_folder', label: '0427 Mailer folder' },
  { value: 'tuck_end', label: '0713 Tuck end' },
  { value: 'auto_lock_bottom', label: '0716 Auto lock bottom' },
]

const fluteOptions = [
  { value: 'e', label: 'E' },
  { value: 'b', label: 'B' },
  { value: 'c', label: 'C' },
  { value: 'bc', label: 'BC' },
  { value: 'none', label: 'Non-flute' },
]

const materialOptions = [
  { value: 'corrugated', label: 'Corrugated' },
  { value: 'white_card', label: 'White card' },
  { value: 'kraft', label: 'Kraft' },
  { value: 'coated', label: 'Coated' },
]

const dimensionTypeOptions = [
  { value: 'internal', label: 'Internal' },
  { value: 'external', label: 'External' },
  { value: 'manufacturing', label: 'Manufacturing' },
]

const lineRoleOptions = [
  { value: 'cut', label: 'Cut' },
  { value: 'crease', label: 'Crease' },
  { value: 'bleed', label: 'Bleed' },
  { value: 'dimension', label: 'Dimension' },
  { value: 'ignore', label: 'Ignore' },
]

const assetToolOptions = computed(() => [
  { value: 'line_role', label: t('dielineTemplates.assetToolLineRole') },
  { value: 'dimension', label: t('dielineTemplates.assetToolDimension') },
])

const dimFieldOptions = computed(() => [
  { value: 'length', label: t('dielineTemplates.assetDimFieldLength') },
  { value: 'width', label: t('dielineTemplates.assetDimFieldWidth') },
  { value: 'height', label: t('dielineTemplates.assetDimFieldHeight') },
])

const dimDrawModeOptions = computed(() => [
  { value: 'entity', label: t('dielineTemplates.assetDimDrawEntity') },
  { value: 'manual', label: t('dielineTemplates.assetDimDrawManual') },
])

const emptyDims = () => ({ length: 200, width: 150, height: 100 })

const emptyForm = () => ({
  code: '',
  category_id: null,
  category_code: '',
  engine_key: 'slotted_rsc',
  name_i18n: { zh: '', en: '', ko: '' },
  desc_i18n: { zh: '', en: '', ko: '' },
  manufacturing: emptyDims(),
  internal: emptyDims(),
  external: emptyDims(),
  default_thickness_mm: 1.5,
  default_glue_tab_mm: 25,
  flute_type: 'b',
  material_type: 'corrugated',
  default_dimension_type: 'internal',
  min_length_mm: null,
  max_length_mm: null,
  min_width_mm: null,
  max_width_mm: null,
  min_height_mm: null,
  max_height_mm: null,
  slot_gap_mm: null,
  crease_gap_mm: null,
  flap_gap_mm: 2,
  structure_params: {},
  allowances: {},
  priority: 'P0',
  quote_enabled: false,
  preview_enabled: false,
  sort_order: 0,
  is_active: false,
  thumbnail: null,
  production_asset: null,
  production_asset_url: null,
})

const emptyCategoryForm = () => ({
  code: '',
  name_i18n: { zh: '', en: '', ko: '' },
  desc_i18n: { zh: '', en: '', ko: '' },
  sort_order: 0,
  is_active: true,
})

const form = ref(emptyForm())
const categoryForm = ref(emptyCategoryForm())

const categoryOptions = computed(() =>
  categories.value.map((c) => ({
    value: c.id,
    label: `${c.code} · ${c.name_i18n?.zh || c.name_i18n?.en || c.code}`,
    code: c.code,
  })),
)

const selectedAsset = computed(() => assets.value.find((item) => item.id === selectedAssetId.value) || null)

const assetEntities = computed(() => selectedAsset.value?.parsed_geometry?.entities || [])

const assetViewBox = computed(() => {
  const bbox = selectedAsset.value?.parsed_geometry?.bbox
  if (!bbox) return '0 0 100 100'
  const width = Math.max(10, bbox.max_x - bbox.min_x)
  const height = Math.max(10, bbox.max_y - bbox.min_y)
  const pad = Math.max(10, Math.max(width, height) * 0.05)
  return `${bbox.min_x - pad} ${bbox.min_y - pad} ${width + pad * 2} ${height + pad * 2}`
})

const parseViewBox = (viewBox) => {
  const parts = String(viewBox).trim().split(/\s+/).map(Number)
  if (parts.length !== 4 || parts.some((value) => !Number.isFinite(value))) {
    return { x: 0, y: 0, w: 100, h: 100 }
  }
  return { x: parts[0], y: parts[1], w: parts[2], h: parts[3] }
}

const baseViewBox = computed(() => parseViewBox(assetViewBox.value))

const canvasViewBox = computed(() => {
  const { x, y, w, h } = baseViewBox.value
  const zoom = canvasZoom.value
  const viewW = w / zoom
  const viewH = h / zoom
  const cx = x + w / 2 + canvasPan.value.x
  const cy = y + h / 2 + canvasPan.value.y
  return `${cx - viewW / 2} ${cy - viewH / 2} ${viewW} ${viewH}`
})

const canvasZoomPercent = computed(() => Math.round(canvasZoom.value * 100))

const canvasCursorClass = computed(() => {
  if (isPanning.value) return 'is-panning'
  if (spacePressed.value) return 'is-pan-ready'
  return ''
})

const resetCanvasViewport = () => {
  canvasZoom.value = 1
  canvasPan.value = { x: 0, y: 0 }
}

const clampCanvasZoom = (value) => Math.min(CANVAS_ZOOM_MAX, Math.max(CANVAS_ZOOM_MIN, value))

const zoomCanvas = (factor) => {
  canvasZoom.value = clampCanvasZoom(canvasZoom.value * factor)
}

const zoomCanvasIn = () => zoomCanvas(CANVAS_ZOOM_STEP)
const zoomCanvasOut = () => zoomCanvas(1 / CANVAS_ZOOM_STEP)
const zoomCanvasReset = () => {
  canvasZoom.value = 1
  canvasPan.value = { x: 0, y: 0 }
}

const blockAnnotationClick = () => isPanning.value || spacePressed.value

const onCanvasWheel = (event) => {
  if (!assetEntities.value.length) return
  const svg = assetSvgRef.value
  if (!svg?.createSVGPoint) return

  const factor = event.deltaY < 0 ? CANVAS_ZOOM_STEP : 1 / CANVAS_ZOOM_STEP
  const oldZoom = canvasZoom.value
  const newZoom = clampCanvasZoom(oldZoom * factor)
  if (newZoom === oldZoom) return

  const point = svg.createSVGPoint()
  point.x = event.clientX
  point.y = event.clientY
  const matrix = svg.getScreenCTM()?.inverse()
  if (!matrix) {
    canvasZoom.value = newZoom
    return
  }
  const cursor = point.matrixTransform(matrix)
  const { x, y, w, h } = baseViewBox.value
  const viewW = w / oldZoom
  const viewH = h / oldZoom
  const cx = x + w / 2 + canvasPan.value.x
  const cy = y + h / 2 + canvasPan.value.y
  const left = cx - viewW / 2
  const top = cy - viewH / 2
  const fx = (cursor.x - left) / viewW
  const fy = (cursor.y - top) / viewH

  canvasZoom.value = newZoom
  const newViewW = w / newZoom
  const newViewH = h / newZoom
  const newLeft = cursor.x - fx * newViewW
  const newTop = cursor.y - fy * newViewH
  canvasPan.value = {
    x: newLeft + newViewW / 2 - (x + w / 2),
    y: newTop + newViewH / 2 - (y + h / 2),
  }
}

const onCanvasPointerDown = (event) => {
  if (event.button !== 1 && !(event.button === 0 && spacePressed.value)) return
  event.preventDefault()
  isPanning.value = true
  panStart.value = {
    clientX: event.clientX,
    clientY: event.clientY,
    panX: canvasPan.value.x,
    panY: canvasPan.value.y,
    zoom: canvasZoom.value,
    base: { ...baseViewBox.value },
  }
}

const onCanvasPointerMove = (event) => {
  if (!isPanning.value || !panStart.value) return
  const svg = assetSvgRef.value
  if (!svg) return
  const rect = svg.getBoundingClientRect()
  if (!rect.width || !rect.height) return
  const { w, h } = panStart.value.base
  const viewW = w / panStart.value.zoom
  const viewH = h / panStart.value.zoom
  const dxPx = event.clientX - panStart.value.clientX
  const dyPx = event.clientY - panStart.value.clientY
  const dx = (-dxPx / rect.width) * viewW
  const dy = (-dyPx / rect.height) * viewH
  canvasPan.value = {
    x: panStart.value.panX + dx,
    y: panStart.value.panY + dy,
  }
}

const endCanvasPan = () => {
  isPanning.value = false
  panStart.value = null
}

const onCanvasPointerUp = () => endCanvasPan()

const onAssetDialogKeyDown = (event) => {
  if (!assetDialog.value) return
  if (event.code === 'Space') {
    event.preventDefault()
    spacePressed.value = true
  }
}

const onAssetDialogKeyUp = (event) => {
  if (event.code === 'Space') {
    spacePressed.value = false
    endCanvasPan()
  }
}

watch(assetDialog, (open) => {
  if (open) {
    assetDialogFullscreen.value = true
    assetSidebarCollapsed.value = false
    resetCanvasViewport()
    window.addEventListener('keydown', onAssetDialogKeyDown)
    window.addEventListener('keyup', onAssetDialogKeyUp)
    return
  }
  window.removeEventListener('keydown', onAssetDialogKeyDown)
  window.removeEventListener('keyup', onAssetDialogKeyUp)
  spacePressed.value = false
  endCanvasPan()
})

const roleStroke = (role) => {
  const map = {
    cut: '#2563eb',
    crease: '#ef4444',
    bleed: '#22c55e',
    dimension: '#f59e0b',
    ignore: '#94a3b8',
  }
  return map[role] || map.cut
}

const roleDash = (role) => (role === 'crease' ? '8 5' : role === 'ignore' ? '3 5' : '')

const dimFieldLabel = (field) => dimFieldOptions.value.find((item) => item.value === field)?.label || field

const dimBaseValue = (field) => {
  if (field === 'length') return assetUpload.value.base_length
  if (field === 'width') return assetUpload.value.base_width
  if (field === 'height') return assetUpload.value.base_height
  return ''
}

const roundCoord = (value) => Math.round(Number(value || 0) * 10000) / 10000

const normalizeDimAnnotations = (items = []) =>
  (Array.isArray(items) ? items : [])
    .filter((item) => item?.field && Number.isFinite(Number(item.x1)) && Number.isFinite(Number(item.y1)) && Number.isFinite(Number(item.x2)) && Number.isFinite(Number(item.y2)))
    .map((item) => {
      const x1 = roundCoord(item.x1)
      const y1 = roundCoord(item.y1)
      const x2 = roundCoord(item.x2)
      const y2 = roundCoord(item.y2)
      const axis = item.axis || (Math.abs(x2 - x1) >= Math.abs(y2 - y1) ? 'horizontal' : 'vertical')
      return {
        id: item.id || `dim_${item.field}_${Date.now()}`,
        field: item.field,
        axis,
        source: item.source || 'manual',
        entity_id: item.entity_id || null,
        x1,
        y1,
        x2,
        y2,
        label_x: roundCoord(item.label_x ?? (x1 + x2) / 2),
        label_y: roundCoord(item.label_y ?? (y1 + y2) / 2),
      }
    })

const syncAssetMappingState = () => {
  const mapping = selectedAsset.value?.mapping_schema || {}
  entityRoles.value = { ...(mapping.entity_roles || {}) }
  dimensionAnnotations.value = normalizeDimAnnotations(mapping.dimension_annotations || [])
  pendingDimPoint.value = null
}

const svgPointFromEvent = (event) => {
  const svg = event.currentTarget?.ownerSVGElement || event.currentTarget
  if (!svg?.createSVGPoint) return null
  const point = svg.createSVGPoint()
  point.x = event.clientX
  point.y = event.clientY
  const matrix = svg.getScreenCTM()?.inverse()
  if (!matrix) return null
  const svgPoint = point.matrixTransform(matrix)
  return { x: roundCoord(svgPoint.x), y: roundCoord(svgPoint.y) }
}

const makeDimAnnotation = ({ source, entity = null, start, end }) => {
  const field = selectedDimField.value
  const x1 = roundCoord(start.x)
  const y1 = roundCoord(start.y)
  const x2 = roundCoord(end.x)
  const y2 = roundCoord(end.y)
  const axis = Math.abs(x2 - x1) >= Math.abs(y2 - y1) ? 'horizontal' : 'vertical'
  const midX = (x1 + x2) / 2
  const midY = (y1 + y2) / 2
  const labelOffset = 12
  return {
    id: `dim_${field}_${Date.now()}`,
    field,
    axis,
    source,
    entity_id: entity?.entity_id || null,
    x1,
    y1,
    x2,
    y2,
    label_x: roundCoord(axis === 'vertical' ? midX + labelOffset : midX),
    label_y: roundCoord(axis === 'horizontal' ? midY - labelOffset : midY),
  }
}

const upsertDimAnnotation = (annotation) => {
  dimensionAnnotations.value = [
    ...dimensionAnnotations.value.filter((item) => item.field !== annotation.field),
    annotation,
  ]
}

const removeDimAnnotation = (field) => {
  dimensionAnnotations.value = dimensionAnnotations.value.filter((item) => item.field !== field)
  if (pendingDimPoint.value?.field === field) pendingDimPoint.value = null
}

const onAssetLineClick = (entity, event) => {
  if (blockAnnotationClick()) return
  event.stopPropagation()
  if (assetToolMode.value !== 'dimension') {
    markEntity(entity)
    return
  }
  if (selectedDimDrawMode.value === 'entity') {
    upsertDimAnnotation(makeDimAnnotation({
      source: 'entity',
      entity,
      start: { x: entity.x1, y: entity.y1 },
      end: { x: entity.x2, y: entity.y2 },
    }))
    return
  }
  const point = svgPointFromEvent(event)
  if (!point) return
  handleManualDimPoint(point)
}

const handleManualDimPoint = (point) => {
  if (!pendingDimPoint.value || pendingDimPoint.value.field !== selectedDimField.value) {
    pendingDimPoint.value = { field: selectedDimField.value, point }
    return
  }
  upsertDimAnnotation(makeDimAnnotation({
    source: 'manual',
    start: pendingDimPoint.value.point,
    end: point,
  }))
  pendingDimPoint.value = null
}

const onAssetSvgClick = (event) => {
  if (blockAnnotationClick()) return
  if (assetToolMode.value !== 'dimension' || selectedDimDrawMode.value !== 'manual') return
  const point = svgPointFromEvent(event)
  if (point) handleManualDimPoint(point)
}

const load = async () => {
  const [tplRes, catRes] = await Promise.all([fetchDielineTemplates(), fetchDielineCategories()])
  items.value = tplRes.data.items || []
  categories.value = catRes.data.items || []
}
onMounted(load)

const openCreate = () => {
  editingId.value = null
  form.value = emptyForm()
  if (categories.value.length) {
    form.value.category_id = categories.value[0].id
    form.value.category_code = categories.value[0].code
  }
  dialog.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.value = {
    code: row.code,
    category_id: row.category_id || categories.value.find((c) => c.code === row.category_code)?.id || null,
    category_code: row.category_code,
    engine_key: row.engine_key,
    name_i18n: { zh: '', en: '', ko: '', ...(row.name_i18n || {}) },
    desc_i18n: { zh: '', en: '', ko: '', ...(row.desc_i18n || {}) },
    manufacturing: {
      length: Number(row.default_manufacturing_length_mm ?? row.default_length_mm),
      width: Number(row.default_manufacturing_width_mm ?? row.default_width_mm),
      height: Number(row.default_manufacturing_height_mm ?? row.default_height_mm),
    },
    internal: {
      length: Number(row.default_internal_length_mm),
      width: Number(row.default_internal_width_mm),
      height: Number(row.default_internal_height_mm),
    },
    external: {
      length: Number(row.default_external_length_mm),
      width: Number(row.default_external_width_mm),
      height: Number(row.default_external_height_mm),
    },
    default_thickness_mm: Number(row.default_thickness_mm),
    default_glue_tab_mm: Number(row.default_glue_tab_mm),
    flute_type: row.flute_type || 'b',
    material_type: row.material_type || 'corrugated',
    default_dimension_type: row.default_dimension_type || 'internal',
    min_length_mm: row.min_length_mm != null ? Number(row.min_length_mm) : null,
    max_length_mm: row.max_length_mm != null ? Number(row.max_length_mm) : null,
    min_width_mm: row.min_width_mm != null ? Number(row.min_width_mm) : null,
    max_width_mm: row.max_width_mm != null ? Number(row.max_width_mm) : null,
    min_height_mm: row.min_height_mm != null ? Number(row.min_height_mm) : null,
    max_height_mm: row.max_height_mm != null ? Number(row.max_height_mm) : null,
    slot_gap_mm: row.slot_gap_mm != null ? Number(row.slot_gap_mm) : null,
    crease_gap_mm: row.crease_gap_mm != null ? Number(row.crease_gap_mm) : null,
    flap_gap_mm: row.flap_gap_mm != null ? Number(row.flap_gap_mm) : 2,
    structure_params: row.structure_params || {},
    allowances: row.allowances || {},
    priority: row.priority,
    quote_enabled: row.quote_enabled,
    preview_enabled: row.preview_enabled,
    sort_order: row.sort_order,
    is_active: row.is_active,
    thumbnail: null,
    production_asset: null,
    production_asset_url: row.production_asset_url || null,
  }
  dialog.value = true
}

const onProductionAsset = (e) => {
  form.value.production_asset = e.target.files?.[0] || null
}

const fileNameFromUrl = (url) => {
  if (!url) return ''
  const cleanUrl = String(url).split('?')[0]
  const name = cleanUrl.split('/').filter(Boolean).pop() || ''
  try {
    return decodeURIComponent(name)
  } catch {
    return name
  }
}

const onCategoryChange = (id) => {
  const cat = categories.value.find((c) => c.id === id)
  form.value.category_code = cat?.code || ''
}

const onThumbnail = (e) => {
  form.value.thumbnail = e.target.files?.[0] || null
}

const buildFormData = () => {
  const fd = new FormData()
  const f = form.value
  fd.append('code', f.code)
  if (f.category_id) fd.append('category_id', String(f.category_id))
  fd.append('category_code', f.category_code)
  fd.append('engine_key', f.engine_key)
  fd.append('name_i18n', JSON.stringify(f.name_i18n))
  fd.append('desc_i18n', JSON.stringify(f.desc_i18n))
  fd.append('default_manufacturing_length_mm', String(f.manufacturing.length))
  fd.append('default_manufacturing_width_mm', String(f.manufacturing.width))
  fd.append('default_manufacturing_height_mm', String(f.manufacturing.height))
  fd.append('default_internal_length_mm', String(f.internal.length))
  fd.append('default_internal_width_mm', String(f.internal.width))
  fd.append('default_internal_height_mm', String(f.internal.height))
  fd.append('default_external_length_mm', String(f.external.length))
  fd.append('default_external_width_mm', String(f.external.width))
  fd.append('default_external_height_mm', String(f.external.height))
  fd.append('default_length_mm', String(f.manufacturing.length))
  fd.append('default_width_mm', String(f.manufacturing.width))
  fd.append('default_height_mm', String(f.manufacturing.height))
  fd.append('default_thickness_mm', String(f.default_thickness_mm))
  fd.append('default_glue_tab_mm', String(f.default_glue_tab_mm))
  fd.append('flute_type', f.flute_type)
  fd.append('material_type', f.material_type)
  fd.append('default_dimension_type', f.default_dimension_type)
  if (f.min_length_mm != null) fd.append('min_length_mm', String(f.min_length_mm))
  if (f.max_length_mm != null) fd.append('max_length_mm', String(f.max_length_mm))
  if (f.min_width_mm != null) fd.append('min_width_mm', String(f.min_width_mm))
  if (f.max_width_mm != null) fd.append('max_width_mm', String(f.max_width_mm))
  if (f.min_height_mm != null) fd.append('min_height_mm', String(f.min_height_mm))
  if (f.max_height_mm != null) fd.append('max_height_mm', String(f.max_height_mm))
  if (f.slot_gap_mm != null) fd.append('slot_gap_mm', String(f.slot_gap_mm))
  if (f.crease_gap_mm != null) fd.append('crease_gap_mm', String(f.crease_gap_mm))
  if (f.flap_gap_mm != null) fd.append('flap_gap_mm', String(f.flap_gap_mm))
  fd.append('structure_params', JSON.stringify(f.structure_params || {}))
  fd.append('allowances', JSON.stringify(f.allowances || {}))
  fd.append('priority', f.priority)
  fd.append('quote_enabled', f.quote_enabled ? 'true' : 'false')
  fd.append('preview_enabled', f.preview_enabled ? 'true' : 'false')
  fd.append('sort_order', String(f.sort_order))
  fd.append('is_active', f.is_active ? 'true' : 'false')
  if (f.thumbnail) fd.append('thumbnail', f.thumbnail)
  if (f.production_asset) fd.append('production_asset', f.production_asset)
  return fd
}

const submit = async () => {
  if (!form.value.code?.trim()) {
    ElMessage.warning(t('dielineTemplates.codeRequired'))
    return
  }
  if (!form.value.category_id && !form.value.category_code) {
    ElMessage.warning(t('dielineTemplates.categoryRequired'))
    return
  }
  submitting.value = true
  try {
    const fd = buildFormData()
    if (editingId.value) {
      await updateDielineTemplate(editingId.value, fd)
    } else {
      await saveDielineTemplate(fd)
    }
    ElMessage.success(t('common.success'))
    dialog.value = false
    await load()
  } catch (err) {
    if (err?.code === 'DIELINE_TEMPLATE_ASSET_REQUIRED') {
      ElMessage.warning(t('dielineTemplates.assetRequiredBeforeEnable'))
    } else {
      ElMessage.error(err?.message || t('dielineTemplates.saveFailed'))
    }
  } finally {
    submitting.value = false
  }
}

const remove = async (row) => {
  await deleteDielineTemplate(row.id)
  ElMessage.success(t('common.success'))
  await load()
}

const loadAssets = async (templateId) => {
  const res = await fetchDielineTemplateAssets(templateId)
  assets.value = res.data.items || []
  selectedAssetId.value = assets.value[0]?.id || null
  syncAssetMappingState()
  resetCanvasViewport()
}

const openAssets = async (row) => {
  assetTemplate.value = row
  assetUpload.value = {
    file: null,
    base_length: Number(row.default_manufacturing_length_mm ?? row.default_length_mm ?? 200),
    base_width: Number(row.default_manufacturing_width_mm ?? row.default_width_mm ?? 150),
    base_height: Number(row.default_manufacturing_height_mm ?? row.default_height_mm ?? 100),
    base_thickness: Number(row.default_thickness_mm ?? 1.5),
  }
  assetDialog.value = true
  await loadAssets(row.id)
}

const onAssetFile = (event) => {
  assetUpload.value.file = event.target.files?.[0] || null
}

const uploadAsset = async () => {
  if (!assetTemplate.value || !assetUpload.value.file) {
    ElMessage.warning(t('dielineTemplates.assetFileRequired'))
    return
  }
  assetSubmitting.value = true
  try {
    const fd = new FormData()
    fd.append('source_file', assetUpload.value.file)
    fd.append('base_length', String(assetUpload.value.base_length))
    fd.append('base_width', String(assetUpload.value.base_width))
    fd.append('base_height', String(assetUpload.value.base_height))
    fd.append('base_thickness', String(assetUpload.value.base_thickness))
    await uploadDielineTemplateAsset(assetTemplate.value.id, fd)
    ElMessage.success(t('common.success'))
    await loadAssets(assetTemplate.value.id)
  } catch (err) {
    ElMessage.error(err?.message || t('dielineTemplates.assetParseFailed'))
  } finally {
    assetSubmitting.value = false
  }
}

const selectAsset = (asset) => {
  selectedAssetId.value = asset.id
  syncAssetMappingState()
  resetCanvasViewport()
}

const markEntity = (entity) => {
  entityRoles.value = {
    ...entityRoles.value,
    [entity.entity_id]: selectedRole.value,
  }
}

const saveAssetMapping = async () => {
  if (!assetTemplate.value || !selectedAsset.value) return
  const baseDimensions = {
    length: assetUpload.value.base_length,
    width: assetUpload.value.base_width,
    height: assetUpload.value.base_height,
    thickness: assetUpload.value.base_thickness,
  }
  const bbox = selectedAsset.value.parsed_geometry?.bbox || {}
  const mappingSchema = {
    ...(selectedAsset.value.mapping_schema || {}),
    schema_version: 1,
    mapping_mode: 'orthogonal_scale',
    base_dimensions: baseDimensions,
    dimension_refs: {
      length: { axis: 'x', from: bbox.min_x || 0, to: bbox.max_x || 0 },
      height: { axis: 'y', from: bbox.min_y || 0, to: bbox.max_y || 0 },
    },
    entity_roles: entityRoles.value,
    dimension_annotations: dimensionAnnotations.value,
    transform_rules: { x: 'length', y: 'height' },
  }
  await updateDielineTemplateAsset(assetTemplate.value.id, selectedAsset.value.id, {
    mapping_schema: mappingSchema,
    base_dimensions: baseDimensions,
  })
  ElMessage.success(t('common.success'))
  await loadAssets(assetTemplate.value.id)
}

const activateAsset = async () => {
  if (!assetTemplate.value || !selectedAsset.value) return
  await activateDielineTemplateAsset(assetTemplate.value.id, selectedAsset.value.id)
  ElMessage.success(t('dielineTemplates.assetActivated'))
  await loadAssets(assetTemplate.value.id)
  await load()
}

const removeAsset = async (asset) => {
  if (!assetTemplate.value) return
  await deleteDielineTemplateAsset(assetTemplate.value.id, asset.id)
  ElMessage.success(t('common.success'))
  await loadAssets(assetTemplate.value.id)
}

const openCategoryCreate = () => {
  editingCategoryId.value = null
  categoryForm.value = emptyCategoryForm()
  categoryDialog.value = true
}

const openCategoryEdit = (row) => {
  editingCategoryId.value = row.id
  categoryForm.value = {
    code: row.code,
    name_i18n: { zh: '', en: '', ko: '', ...(row.name_i18n || {}) },
    desc_i18n: { zh: '', en: '', ko: '', ...(row.desc_i18n || {}) },
    sort_order: row.sort_order,
    is_active: row.is_active,
  }
  categoryDialog.value = true
}

const submitCategory = async () => {
  if (!categoryForm.value.code?.trim()) {
    ElMessage.warning(t('dielineTemplates.categoryCodeRequired'))
    return
  }
  categorySubmitting.value = true
  try {
    const payload = { ...categoryForm.value }
    if (editingCategoryId.value) {
      await updateDielineCategory(editingCategoryId.value, payload)
    } else {
      await saveDielineCategory(payload)
    }
    ElMessage.success(t('common.success'))
    categoryDialog.value = false
    await load()
  } finally {
    categorySubmitting.value = false
  }
}

const removeCategory = async (row) => {
  try {
    await deleteDielineCategory(row.id)
    ElMessage.success(t('common.success'))
    await load()
  } catch (err) {
    ElMessage.error(err?.message || t('dielineTemplates.categoryDeleteBlocked'))
  }
}

const formatDims = (l, w, h) => `${l}×${w}×${h}`
</script>

<template>
  <div>
    <section class="section-block">
      <div class="toolbar">
        <h2>{{ t('dielineTemplates.categoryTitle') }}</h2>
        <el-button type="primary" @click="openCategoryCreate">{{ t('dielineTemplates.createCategory') }}</el-button>
      </div>
      <el-table :data="categories" size="small">
        <el-table-column prop="code" :label="t('dielineTemplates.categoryCode')" width="100" />
        <el-table-column :label="t('dielineTemplates.name')" min-width="140">
          <template #default="{ row }">{{ row.name_i18n?.zh || row.name_i18n?.en || row.code }}</template>
        </el-table-column>
        <el-table-column prop="sort_order" :label="t('dielineTemplates.sortOrder')" width="80" />
        <el-table-column :label="t('dielineTemplates.enabled')" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? t('dielineTemplates.active') : t('dielineTemplates.inactive') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('common.actions')" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="openCategoryEdit(row)">{{ t('common.edit') }}</el-button>
            <el-button size="small" type="danger" @click="removeCategory(row)">{{ t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="section-block">
      <div class="toolbar">
        <h2>{{ t('dielineTemplates.title') }}</h2>
        <el-button type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
      </div>
      <el-table :data="items">
        <el-table-column prop="code" :label="t('dielineTemplates.code')" width="90" />
        <el-table-column prop="category_code" :label="t('dielineTemplates.category')" width="90" />
        <el-table-column prop="engine_key" :label="t('dielineTemplates.engine')" width="140" />
        <el-table-column :label="t('dielineTemplates.name')" min-width="140">
          <template #default="{ row }">{{ row.name_i18n?.zh || row.name_i18n?.en || row.code }}</template>
        </el-table-column>
        <el-table-column :label="t('dielineTemplates.defaults')" min-width="280">
          <template #default="{ row }">
            <div class="dim-summary">
              <span>{{ t('dielineTemplates.dimManufacturing') }}: {{ formatDims(row.default_manufacturing_length_mm ?? row.default_length_mm, row.default_manufacturing_width_mm ?? row.default_width_mm, row.default_manufacturing_height_mm ?? row.default_height_mm) }}</span>
              <span>{{ t('dielineTemplates.dimInternal') }}: {{ formatDims(row.default_internal_length_mm, row.default_internal_width_mm, row.default_internal_height_mm) }}</span>
              <span>{{ t('dielineTemplates.dimExternal') }}: {{ formatDims(row.default_external_length_mm, row.default_external_width_mm, row.default_external_height_mm) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="t('dielineTemplates.thumbnail')" width="90">
          <template #default="{ row }">
            <img v-if="row.thumbnail_url" :src="row.thumbnail_url" alt="" class="thumb" />
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" :label="t('dielineTemplates.sortOrder')" width="80" />
        <el-table-column :label="t('dielineTemplates.enabled')" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? t('dielineTemplates.active') : t('dielineTemplates.inactive') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('dielineTemplates.parametricAsset')" width="130">
          <template #default="{ row }">
            <el-tag :type="row.parametric_asset_status === 'mapped' ? 'success' : 'info'" size="small">
              {{ row.parametric_asset_status || 'none' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('common.actions')" width="240">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
            <el-button size="small" @click="openAssets(row)">{{ t('dielineTemplates.assets') }}</el-button>
            <el-button size="small" type="danger" @click="remove(row)">{{ t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog
      v-model="categoryDialog"
      :title="editingCategoryId ? t('dielineTemplates.editCategory') : t('dielineTemplates.createCategory')"
      width="520px"
      destroy-on-close
    >
      <el-form label-width="120px">
        <el-form-item :label="t('dielineTemplates.categoryCode')">
          <el-input v-model="categoryForm.code" :disabled="!!editingCategoryId" />
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.nameZh')">
          <el-input v-model="categoryForm.name_i18n.zh" />
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.nameEn')">
          <el-input v-model="categoryForm.name_i18n.en" />
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.descZh')">
          <el-input v-model="categoryForm.desc_i18n.zh" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.sortOrder')">
          <el-input-number v-model="categoryForm.sort_order" :min="0" :controls="false" />
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.enabled')">
          <el-switch v-model="categoryForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="categoryDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="categorySubmitting" @click="submitCategory">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="dialog"
      :title="editingId ? t('common.edit') : t('common.create')"
      width="min(1040px, calc(100vw - 32px))"
      class="dieline-template-dialog"
      destroy-on-close
    >
      <el-form class="template-form" label-position="top">
        <el-alert
          type="info"
          :closable="false"
          :title="t('dielineTemplates.parametricWorkflowTitle')"
          :description="t('dielineTemplates.parametricWorkflowHint')"
          show-icon
          class="template-form-alert"
        />
        <el-form-item :label="t('dielineTemplates.code')">
          <el-input v-model="form.code" :disabled="!!editingId" />
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.category')">
          <el-select v-model="form.category_id" @change="onCategoryChange">
            <el-option
              v-for="opt in categoryOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.engine')">
          <el-select v-model="form.engine_key">
            <el-option v-for="opt in engineOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <p class="field-hint">{{ t('dielineTemplates.engineKeyMetadataHint') }}</p>
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.nameZh')">
          <el-input v-model="form.name_i18n.zh" />
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.nameEn')">
          <el-input v-model="form.name_i18n.en" />
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.descZh')">
          <el-input v-model="form.desc_i18n.zh" type="textarea" :rows="2" />
        </el-form-item>

        <el-divider>{{ t('dielineTemplates.dimManufacturing') }}</el-divider>
        <div class="dim-row">
          <el-form-item :label="t('dielineTemplates.defaultL')">
            <el-input-number v-model="form.manufacturing.length" :min="10" :controls="false" />
          </el-form-item>
          <el-form-item :label="t('dielineTemplates.defaultW')">
            <el-input-number v-model="form.manufacturing.width" :min="10" :controls="false" />
          </el-form-item>
          <el-form-item :label="t('dielineTemplates.defaultH')">
            <el-input-number v-model="form.manufacturing.height" :min="10" :controls="false" />
          </el-form-item>
        </div>

        <el-divider>{{ t('dielineTemplates.dimInternal') }}</el-divider>
        <div class="dim-row">
          <el-form-item :label="t('dielineTemplates.defaultL')">
            <el-input-number v-model="form.internal.length" :min="10" :controls="false" />
          </el-form-item>
          <el-form-item :label="t('dielineTemplates.defaultW')">
            <el-input-number v-model="form.internal.width" :min="10" :controls="false" />
          </el-form-item>
          <el-form-item :label="t('dielineTemplates.defaultH')">
            <el-input-number v-model="form.internal.height" :min="10" :controls="false" />
          </el-form-item>
        </div>

        <el-divider>{{ t('dielineTemplates.dimExternal') }}</el-divider>
        <div class="dim-row">
          <el-form-item :label="t('dielineTemplates.defaultL')">
            <el-input-number v-model="form.external.length" :min="10" :controls="false" />
          </el-form-item>
          <el-form-item :label="t('dielineTemplates.defaultW')">
            <el-input-number v-model="form.external.width" :min="10" :controls="false" />
          </el-form-item>
          <el-form-item :label="t('dielineTemplates.defaultH')">
            <el-input-number v-model="form.external.height" :min="10" :controls="false" />
          </el-form-item>
        </div>

        <el-form-item :label="t('dielineTemplates.defaultThickness')">
          <el-input-number v-model="form.default_thickness_mm" :min="0.1" :step="0.1" :controls="false" />
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.glueTab')">
          <el-input-number v-model="form.default_glue_tab_mm" :min="15" :controls="false" />
        </el-form-item>

        <el-divider>{{ t('dielineTemplates.precisionSection') }}</el-divider>
        <el-form-item :label="t('dielineTemplates.fluteType')">
          <el-select v-model="form.flute_type">
            <el-option v-for="opt in fluteOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.materialType')">
          <el-select v-model="form.material_type">
            <el-option v-for="opt in materialOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.defaultDimensionType')">
          <el-select v-model="form.default_dimension_type">
            <el-option
              v-for="opt in dimensionTypeOptions"
              :key="opt.value"
              :label="t(`dielineTemplates.dimType_${opt.value}`)"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <div class="dim-row">
          <el-form-item :label="t('dielineTemplates.minL')">
            <el-input-number v-model="form.min_length_mm" :min="0" :controls="false" />
          </el-form-item>
          <el-form-item :label="t('dielineTemplates.maxL')">
            <el-input-number v-model="form.max_length_mm" :min="0" :controls="false" />
          </el-form-item>
          <el-form-item :label="t('dielineTemplates.flapGap')">
            <el-input-number v-model="form.flap_gap_mm" :min="0" :step="0.5" :controls="false" />
          </el-form-item>
        </div>
        <div class="dim-row">
          <el-form-item :label="t('dielineTemplates.minW')">
            <el-input-number v-model="form.min_width_mm" :min="0" :controls="false" />
          </el-form-item>
          <el-form-item :label="t('dielineTemplates.maxW')">
            <el-input-number v-model="form.max_width_mm" :min="0" :controls="false" />
          </el-form-item>
          <el-form-item :label="t('dielineTemplates.slotGap')">
            <el-input-number v-model="form.slot_gap_mm" :min="0" :step="0.1" :controls="false" />
          </el-form-item>
        </div>
        <div class="dim-row">
          <el-form-item :label="t('dielineTemplates.minH')">
            <el-input-number v-model="form.min_height_mm" :min="0" :controls="false" />
          </el-form-item>
          <el-form-item :label="t('dielineTemplates.maxH')">
            <el-input-number v-model="form.max_height_mm" :min="0" :controls="false" />
          </el-form-item>
          <el-form-item :label="t('dielineTemplates.creaseGap')">
            <el-input-number v-model="form.crease_gap_mm" :min="0" :step="0.1" :controls="false" />
          </el-form-item>
        </div>
        <el-form-item :label="t('dielineTemplates.productionAsset')">
          <input type="file" accept=".dxf,.cf2,.svg,.pdf,.ai" @change="onProductionAsset" />
          <p v-if="form.production_asset" class="field-hint">
            {{ t('dielineTemplates.selectedFile') }}: {{ form.production_asset.name }}
          </p>
          <p v-else-if="form.production_asset_url" class="field-hint">
            {{ t('dielineTemplates.currentFile') }}:
            <a :href="form.production_asset_url" target="_blank" rel="noreferrer">
              {{ fileNameFromUrl(form.production_asset_url) || form.production_asset_url }}
            </a>
          </p>
          <p class="field-hint">{{ t('dielineTemplates.productionAssetHint') }}</p>
        </el-form-item>

        <el-form-item :label="t('dielineTemplates.sortOrder')">
          <el-input-number v-model="form.sort_order" :min="0" :controls="false" />
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.quoteEnabled')">
          <el-switch v-model="form.quote_enabled" />
          <p class="field-hint">{{ t('dielineTemplates.enableRequiresAsset') }}</p>
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.previewEnabled')">
          <el-switch v-model="form.preview_enabled" />
          <p class="field-hint">{{ t('dielineTemplates.enableRequiresAsset') }}</p>
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.enabled')">
          <el-switch v-model="form.is_active" />
          <p class="field-hint">{{ t('dielineTemplates.enableRequiresAsset') }}</p>
        </el-form-item>
        <el-form-item :label="t('dielineTemplates.thumbnail')">
          <input type="file" accept="image/*" @change="onThumbnail" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="assetDialog"
      :fullscreen="assetDialogFullscreen"
      :width="assetDialogFullscreen ? undefined : 'min(1180px, calc(100vw - 32px))'"
      class="asset-dialog"
      :class="{ 'is-fullscreen': assetDialogFullscreen }"
      destroy-on-close
    >
      <template #header>
        <div class="asset-dialog-header">
          <span class="asset-dialog-title">{{ t('dielineTemplates.parametricAsset') }} · {{ assetTemplate?.code || '' }}</span>
          <el-button size="small" @click="assetDialogFullscreen = !assetDialogFullscreen">
            {{ assetDialogFullscreen ? t('dielineTemplates.assetExitFullscreen') : t('dielineTemplates.assetFullscreen') }}
          </el-button>
        </div>
      </template>
      <div class="asset-panel" :class="{ 'is-sidebar-collapsed': assetSidebarCollapsed, 'is-fullscreen': assetDialogFullscreen }">
        <aside class="asset-side">
          <div class="asset-side-toolbar">
            <el-button
              size="small"
              text
              :title="assetSidebarCollapsed ? t('dielineTemplates.assetSidebarExpand') : t('dielineTemplates.assetSidebarCollapse')"
              @click="assetSidebarCollapsed = !assetSidebarCollapsed"
            >
              {{ assetSidebarCollapsed ? '»' : '«' }}
            </el-button>
          </div>
          <div v-show="!assetSidebarCollapsed" class="asset-side-body">
            <el-divider>{{ t('dielineTemplates.uploadAsset') }}</el-divider>
            <input type="file" accept=".dxf,.svg,.ai,.pdf" @change="onAssetFile" />
            <div class="dim-row asset-dims">
              <el-form-item :label="t('dielineTemplates.defaultL')">
                <el-input-number v-model="assetUpload.base_length" :min="1" :controls="false" />
              </el-form-item>
              <el-form-item :label="t('dielineTemplates.defaultW')">
                <el-input-number v-model="assetUpload.base_width" :min="1" :controls="false" />
              </el-form-item>
              <el-form-item :label="t('dielineTemplates.defaultH')">
                <el-input-number v-model="assetUpload.base_height" :min="1" :controls="false" />
              </el-form-item>
            </div>
            <el-form-item :label="t('dielineTemplates.defaultThickness')">
              <el-input-number v-model="assetUpload.base_thickness" :min="0" :step="0.1" :controls="false" />
            </el-form-item>
            <el-button type="primary" :loading="assetSubmitting" @click="uploadAsset">
              {{ t('dielineTemplates.uploadAndParse') }}
            </el-button>

            <el-divider>{{ t('dielineTemplates.assetDimAnnotate') }}</el-divider>
            <div class="dim-annotation-panel">
              <el-form-item :label="t('dielineTemplates.assetDimField')">
                <el-select v-model="selectedDimField">
                  <el-option
                    v-for="opt in dimFieldOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item :label="t('dielineTemplates.assetDimDrawMode')">
                <el-radio-group v-model="selectedDimDrawMode" size="small">
                  <el-radio-button v-for="opt in dimDrawModeOptions" :key="opt.value" :label="opt.value">
                    {{ opt.label }}
                  </el-radio-button>
                </el-radio-group>
              </el-form-item>
              <p class="field-hint">
                {{ selectedDimDrawMode === 'entity' ? t('dielineTemplates.assetDimEntityHint') : t('dielineTemplates.assetDimManualHint') }}
              </p>
              <p v-if="pendingDimPoint" class="field-hint dim-pending">
                {{ t('dielineTemplates.assetDimPendingEnd') }}
              </p>
              <div class="dim-annotation-list">
                <div v-for="ann in dimensionAnnotations" :key="ann.id" class="dim-annotation-item">
                  <span>
                    <strong>{{ dimFieldLabel(ann.field) }}</strong>
                    <small>{{ ann.source }} · {{ ann.axis }}</small>
                  </span>
                  <el-button size="small" text type="danger" @click="removeDimAnnotation(ann.field)">
                    {{ t('common.delete') }}
                  </el-button>
                </div>
                <p v-if="!dimensionAnnotations.length" class="field-hint">{{ t('dielineTemplates.assetDimEmpty') }}</p>
              </div>
            </div>

            <el-divider>{{ t('dielineTemplates.assetVersions') }}</el-divider>
            <div class="asset-list">
              <button
                v-for="asset in assets"
                :key="asset.id"
                class="asset-item"
                :class="{ active: asset.id === selectedAssetId }"
                type="button"
                @click="selectAsset(asset)"
              >
                <span>v{{ asset.version }} · {{ asset.source_format }}</span>
                <el-tag size="small" :type="asset.is_active ? 'success' : 'info'">
                  {{ asset.mapping_status }}
                </el-tag>
              </button>
            </div>
          </div>
        </aside>

        <main class="asset-workbench">
          <div class="asset-toolbar">
            <div class="asset-tools">
              <el-radio-group v-model="assetToolMode" size="small">
                <el-radio-button v-for="opt in assetToolOptions" :key="opt.value" :label="opt.value">
                  {{ opt.label }}
                </el-radio-button>
              </el-radio-group>
              <el-radio-group v-if="assetToolMode === 'line_role'" v-model="selectedRole" size="small">
                <el-radio-button v-for="opt in lineRoleOptions" :key="opt.value" :label="opt.value">
                  {{ opt.label }}
                </el-radio-button>
              </el-radio-group>
              <el-radio-group v-else v-model="selectedDimField" size="small">
                <el-radio-button v-for="opt in dimFieldOptions" :key="opt.value" :label="opt.value">
                  {{ opt.label }}
                </el-radio-button>
              </el-radio-group>
              <div class="asset-zoom-tools">
                <el-button size="small" @click="zoomCanvasOut">{{ t('dielineTemplates.assetZoomOut') }}</el-button>
                <span class="asset-zoom-level">{{ canvasZoomPercent }}%</span>
                <el-button size="small" @click="zoomCanvasIn">{{ t('dielineTemplates.assetZoomIn') }}</el-button>
                <el-button size="small" @click="resetCanvasViewport">{{ t('dielineTemplates.assetFitView') }}</el-button>
                <el-button size="small" @click="zoomCanvasReset">{{ t('dielineTemplates.assetZoomReset') }}</el-button>
              </div>
            </div>
            <div class="asset-actions">
              <el-button :disabled="!selectedAsset" @click="saveAssetMapping">
                {{ t('dielineTemplates.saveMapping') }}
              </el-button>
              <el-button type="success" :disabled="!selectedAsset" @click="activateAsset">
                {{ t('dielineTemplates.activateAsset') }}
              </el-button>
              <el-button type="danger" :disabled="!selectedAsset" @click="removeAsset(selectedAsset)">
                {{ t('common.delete') }}
              </el-button>
            </div>
          </div>
          <p class="field-hint">{{ t('dielineTemplates.assetAnnotatorHint') }} · {{ t('dielineTemplates.assetPanHint') }}</p>
          <div v-if="selectedAsset?.parse_errors?.message" class="asset-error">
            {{ selectedAsset.parse_errors.message }}
          </div>
          <div
            v-if="assetEntities.length"
            class="asset-canvas-wrap"
            :class="canvasCursorClass"
            @wheel.prevent="onCanvasWheel"
            @pointerdown="onCanvasPointerDown"
            @pointermove="onCanvasPointerMove"
            @pointerup="onCanvasPointerUp"
            @pointerleave="onCanvasPointerUp"
            @pointercancel="onCanvasPointerUp"
            @contextmenu.prevent
          >
            <svg
              ref="assetSvgRef"
              class="asset-svg"
              :viewBox="canvasViewBox"
              @click="onAssetSvgClick"
            >
              <defs>
                <marker
                  id="admin-dim-arrow"
                  viewBox="0 0 10 10"
                  refX="5"
                  refY="5"
                  markerWidth="5"
                  markerHeight="5"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />
                </marker>
              </defs>
              <line
                v-for="entity in assetEntities"
                :key="entity.entity_id"
                :x1="entity.x1"
                :y1="entity.y1"
                :x2="entity.x2"
                :y2="entity.y2"
                :stroke="roleStroke(entityRoles[entity.entity_id] || entity.role)"
                :stroke-dasharray="roleDash(entityRoles[entity.entity_id] || entity.role)"
                stroke-width="1.5"
                vector-effect="non-scaling-stroke"
                class="asset-line"
                @click="onAssetLineClick(entity, $event)"
              />
              <g v-for="ann in dimensionAnnotations" :key="ann.id" class="asset-dim-annotation">
                <line
                  :x1="ann.x1"
                  :y1="ann.y1"
                  :x2="ann.x2"
                  :y2="ann.y2"
                  stroke="#f59e0b"
                  stroke-width="1.6"
                  vector-effect="non-scaling-stroke"
                  marker-start="url(#admin-dim-arrow)"
                  marker-end="url(#admin-dim-arrow)"
                />
                <text
                  :x="ann.label_x"
                  :y="ann.label_y"
                  text-anchor="middle"
                  dominant-baseline="central"
                  class="asset-dim-label"
                >
                  {{ dimBaseValue(ann.field) }} mm
                </text>
              </g>
            </svg>
          </div>
          <el-empty v-else :description="t('dielineTemplates.noParsedGeometry')" />
        </main>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.section-block {
  margin-bottom: 2rem;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}
.thumb {
  width: 48px;
  height: 36px;
  object-fit: contain;
  border-radius: 4px;
  background: #f5f5f5;
}
.dim-summary {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  font-size: 0.82rem;
  line-height: 1.35;
}
.dim-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem 1rem;
}
.field-hint {
  margin: 0.35rem 0 0;
  font-size: 0.8rem;
  color: #64748b;
}

.asset-panel {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 1rem;
  min-height: 560px;
}

.asset-panel.is-fullscreen {
  flex: 1;
  min-height: 0;
  height: 100%;
}

.asset-panel.is-sidebar-collapsed {
  grid-template-columns: 48px minmax(0, 1fr);
}

.asset-side {
  border-right: 1px solid #e2e8f0;
  padding-right: 1rem;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.asset-side-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 0.25rem;
}

.asset-side-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 0.25rem;
}

.asset-dims {
  grid-template-columns: 1fr;
  margin-top: 0.75rem;
}

.dim-annotation-panel :deep(.el-form-item) {
  margin-bottom: 0.65rem;
}

.dim-annotation-panel :deep(.el-select),
.dim-annotation-panel :deep(.el-radio-group) {
  width: 100%;
}

.dim-pending {
  color: #d97706;
  font-weight: 600;
}

.dim-annotation-list {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-top: 0.75rem;
}

.dim-annotation-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.45rem 0.55rem;
  border: 1px solid #fde68a;
  border-radius: 8px;
  background: #fffbeb;
}

.dim-annotation-item span {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}

.dim-annotation-item small {
  color: #92400e;
}

.asset-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.asset-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0.6rem 0.7rem;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
}

.asset-item.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.asset-workbench {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  flex: 1;
}

.asset-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.asset-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.asset-zoom-tools {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.asset-zoom-level {
  min-width: 3rem;
  text-align: center;
  font-size: 0.82rem;
  color: #475569;
  font-variant-numeric: tabular-nums;
}

.asset-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.asset-canvas-wrap {
  flex: 1;
  min-height: 280px;
  overflow: hidden;
  position: relative;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  background: #f8fafc;
}

.asset-panel:not(.is-fullscreen) .asset-canvas-wrap {
  height: min(70vh, 720px);
  min-height: 520px;
}

.asset-canvas-wrap.is-pan-ready {
  cursor: grab;
}

.asset-canvas-wrap.is-panning {
  cursor: grabbing;
}

.asset-svg {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 280px;
  background: transparent;
  border: 0;
  border-radius: 0;
}

.asset-line {
  cursor: pointer;
}

.asset-line:hover {
  stroke-width: 3;
}

.asset-dim-annotation {
  pointer-events: none;
}

.asset-dim-label {
  fill: #b45309;
  font-size: 12px;
  font-weight: 700;
  paint-order: stroke;
  stroke: #fffbeb;
  stroke-width: 3px;
}

.asset-error {
  margin: 0.75rem 0;
  padding: 0.75rem;
  border-radius: 8px;
  background: #fef2f2;
  color: #b91c1c;
}

.template-form {
  max-height: min(72vh, 720px);
  overflow-y: auto;
  padding-right: 0.5rem;
}

.template-form-alert {
  margin-bottom: 1rem;
}

.template-form :deep(.el-form-item) {
  margin-bottom: 0.9rem;
}

.template-form :deep(.el-form-item__label) {
  line-height: 1.25;
  margin-bottom: 0.35rem;
  white-space: normal;
}

.template-form :deep(.el-input-number),
.template-form :deep(.el-select),
.template-form :deep(.el-input) {
  width: 100%;
}

:deep(.asset-dialog.is-fullscreen .el-dialog__body) {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: calc(100vh - 54px);
  overflow: hidden;
  padding: 12px 16px 16px;
}

.asset-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding-right: 2rem;
}

.asset-dialog-title {
  font-size: 1rem;
  font-weight: 600;
  color: #0f172a;
}

@media (max-width: 820px) {
  .dim-row {
    grid-template-columns: 1fr;
  }

  .asset-panel {
    grid-template-columns: 1fr;
  }

  .asset-panel.is-sidebar-collapsed {
    grid-template-columns: 48px minmax(0, 1fr);
  }

  .asset-side {
    border-right: 0;
    border-bottom: 1px solid #e2e8f0;
    padding-right: 0;
    padding-bottom: 1rem;
  }

  .asset-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
