import { computed, onMounted, ref, watch, type Ref } from 'vue'
import type { Router } from 'vue-router'
import type { Composer } from 'vue-i18n'
import { createSimpleQuote, drawingParse, previewSimpleQuote, stpParse } from '../api'
import { pollParseJob } from '../utils/pollJob'

export const INJECTION_MATERIALS = ['ABS', 'ABS+Gf', 'PC', 'PA66', 'PP'] as const
export const MOLD_MATERIALS = ['P20', '718', 'NAK80', 'S136', 'H13'] as const

export const newInjectionPart = () => ({
  material: 'ABS',
  color: 'normal',
  weight_g: 5,
  cavity: 1,
  slider_count: 0,
  quantity: 1000,
})

type UseInjectionQuoteOpts = {
  productName: Ref<string>
  router: Router
  t: Composer['t']
}

export function useInjectionQuote({ productName, router, t }: UseInjectionQuoteOpts) {
  const injection = ref({
    mold_material: 'P20',
    is_precision: false,
    file_name: '',
    contact_person: '',
    parts: [newInjectionPart()],
  })

  const geometry = ref(null)
  const densities = ref({})
  const parsing = ref(false)
  const stpInput = ref(null)

  const undercut = ref(null)
  const materialSuggestion = ref(null)

  const ocr = ref(null)
  const ocrParsing = ref(false)
  const ocrError = ref('')
  const drawingInput = ref(null)

  const preview = ref(null)
  const previewLoading = ref(false)
  const previewError = ref('')
  const submitting = ref(false)
  const error = ref('')
  const familyExpanded = ref(false)

  let previewTimer = null
  let lastPreviewKey = ''

  const previewMesh = computed(() => geometry.value?.preview_mesh || null)

  const familyMaterialMismatch = computed(() => {
    const mats = new Set(injection.value.parts.map((p) => p.material))
    return injection.value.parts.length > 1 && mats.size > 1
  })

  const primaryPart = computed(() => injection.value.parts[0] || newInjectionPart())

  const packagingAmount = computed(() => {
    const part = preview.value?.parts?.[0]
    if (!part) return null
    return part.after_packaging ?? null
  })

  const productionAmount = computed(() => preview.value?.production_fee ?? null)

  const shippingAmount = computed(() => preview.value?.shipping_fee ?? null)

  const shippingHint = computed(() => {
    const ship = preview.value?.shipping
    if (!ship?.chargeable_weight_kg) return ''
    return t('injectionQuote.shippingAutoHint', {
      kg: ship.chargeable_weight_kg,
      krw: ship.fee_krw != null ? Number(ship.fee_krw).toLocaleString() : '—',
    })
  })

  const applyWeightFromGeometry = (part) => {
    if (!geometry.value?.volume_cm3) return
    const density = densities.value[part.material]
    if (!density) return
    part.weight_g = Number((geometry.value.volume_cm3 * density).toFixed(4))
  }

  const onMaterialChange = (part) => {
    applyWeightFromGeometry(part)
  }

  const applyStpSuggestions = () => {
    const first = injection.value.parts[0]
    if (!first) return
    if (undercut.value && typeof undercut.value.suggested_sliders === 'number') {
      first.slider_count = undercut.value.suggested_sliders
    }
    if (materialSuggestion.value?.material && first.material === 'ABS') {
      first.material = materialSuggestion.value.material
      applyWeightFromGeometry(first)
    }
  }

  const buildInputs = () => ({
    mold_material: injection.value.mold_material,
    is_precision: injection.value.is_precision,
    file_name: injection.value.file_name,
    contact_person: injection.value.contact_person || undefined,
    shipping_mode: 'air',
    bbox_mm: geometry.value?.bbox_mm || undefined,
    parts: injection.value.parts.map((p) => ({
      material: p.material,
      color: p.color,
      weight_g: Number(p.weight_g) || 0,
      cavity: Number(p.cavity) || 1,
      slider_count: Number(p.slider_count) || 0,
      quantity: Number(p.quantity) || 1,
    })),
  })

  const refreshPreview = async () => {
    if (familyMaterialMismatch.value) {
      previewError.value = t('simpleQuote.familyMaterialHint')
      preview.value = null
      return
    }
    previewError.value = ''
    const inputs = buildInputs()
    const key = JSON.stringify(inputs)
    if (key === lastPreviewKey && preview.value) return

    previewLoading.value = true
    try {
      lastPreviewKey = key
      const res = await previewSimpleQuote({ quote_type: 'injection', inputs })
      preview.value = res.data
    } catch (err) {
      preview.value = null
      previewError.value = err.message || t('injectionQuote.previewFailed')
    } finally {
      previewLoading.value = false
    }
  }

  const schedulePreview = () => {
    if (previewTimer) clearTimeout(previewTimer)
    previewTimer = setTimeout(refreshPreview, 400)
  }

  watch(
    () => [injection.value, productName.value, geometry.value?.bbox_mm],
    () => schedulePreview(),
    { deep: true },
  )

  onMounted(() => {
    schedulePreview()
  })

  const onStpSelected = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    error.value = ''
    parsing.value = true
    geometry.value = null
    undercut.value = null
    materialSuggestion.value = null
    try {
      const form = new FormData()
      form.append('file', file)
      const enqueued = await stpParse(form)
      const jobId = enqueued.data?.job_id
      const job = await pollParseJob(jobId)
      const result = job.result || {}
      geometry.value = result.geometry
      densities.value = result.densities || {}
      undercut.value = result.geometry?.undercut || null
      materialSuggestion.value = result.geometry?.material_suggestion || null
      injection.value.file_name = file.name
      injection.value.parts.forEach(applyWeightFromGeometry)
      applyStpSuggestions()
      schedulePreview()
    } catch (err) {
      error.value = err.message || t('simpleQuote.parseFailed')
    } finally {
      parsing.value = false
      if (stpInput.value) stpInput.value.value = ''
    }
  }

  const applyOcrSuggestions = () => {
    const first = injection.value.parts[0]
    if (!first || !ocr.value) return
    if (ocr.value.material?.value && INJECTION_MATERIALS.includes(ocr.value.material.value)) {
      first.material = ocr.value.material.value
      applyWeightFromGeometry(first)
    }
    if (ocr.value.precision && typeof ocr.value.precision.is_precision === 'boolean') {
      injection.value.is_precision = ocr.value.precision.is_precision
    }
    const colors = ocr.value.colors || []
    if (colors.includes('transparent')) first.color = 'transparent'
    else if (colors.includes('semi')) first.color = 'semi'
    else if (colors.includes('pantone')) first.color = 'pantone'
  }

  const onDrawingSelected = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    ocrError.value = ''
    ocrParsing.value = true
    ocr.value = null
    try {
      const form = new FormData()
      form.append('file', file)
      const enqueued = await drawingParse(form)
      const jobId = enqueued.data?.job_id
      const job = await pollParseJob(jobId)
      ocr.value = job.result?.ocr
      applyOcrSuggestions()
      schedulePreview()
    } catch (err) {
      ocrError.value = err.message || t('simpleQuote.ocrFailed')
    } finally {
      ocrParsing.value = false
      if (drawingInput.value) drawingInput.value.value = ''
    }
  }

  const addPart = () => {
    injection.value.parts.push(newInjectionPart())
    if (geometry.value?.volume_cm3) applyWeightFromGeometry(injection.value.parts[injection.value.parts.length - 1])
    familyExpanded.value = true
  }

  const removePart = (i) => {
    if (injection.value.parts.length > 1) injection.value.parts.splice(i, 1)
  }

  const onGenerate = async () => {
    error.value = ''
    if (familyMaterialMismatch.value) {
      error.value = t('simpleQuote.familyMaterialHint')
      return null
    }
    submitting.value = true
    try {
      const res = await createSimpleQuote({
        quote_type: 'injection',
        product_name: productName.value,
        inputs: buildInputs(),
      })
      router.replace({ query: { id: res.data.id } })
      return res.data
    } catch (e) {
      error.value = e.message || t('simpleQuote.failed')
      return null
    } finally {
      submitting.value = false
    }
  }

  const fmt = (n, digits = 0) => {
    if (n === null || n === undefined || n === '') return '—'
    return Number(n).toLocaleString(undefined, { maximumFractionDigits: digits })
  }

  const moldTypeLabel = computed(() => {
    if (injection.value.is_precision) return t('injectionQuote.moldTypePrecision')
    if (primaryPart.value.slider_count > 0) return t('injectionQuote.moldTypeSlider')
    return t('injectionQuote.moldTypeStandard')
  })

  return {
    injection,
    geometry,
    densities,
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
    refreshPreview,
  }
}
