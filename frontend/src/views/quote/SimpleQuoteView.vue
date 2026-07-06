<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { convertSimpleQuote, createSimpleQuote, fetchSimpleQuote, stpParse, drawingParse, shippingEstimate } from '../../api'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const quoteType = ref('injection')
const productName = ref('')
const error = ref('')
const result = ref(null)
const submitting = ref(false)

const injectionMaterials = ['ABS', 'ABS+Gf', 'PC', 'PA66', 'PP']
const colorOptions = ['normal', 'transparent', 'semi', 'pantone']
const moldMaterials = ['P20', '718', 'NAK80', 'S136', 'H13']

const newPart = () => ({ material: 'ABS', color: 'normal', weight_g: 5, cavity: 1, slider_count: 0, quantity: 1000 })
const injection = ref({
  mold_material: 'P20',
  is_precision: false,
  file_name: '',
  parts: [newPart()],
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

const applyWeightFromGeometry = (part) => {
  if (!geometry.value || !geometry.value.volume_cm3) return
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
  if (materialSuggestion.value && materialSuggestion.value.material) {
    // 仅在用户尚未指定（默认 ABS）时预填建议材料
    if (first.material === 'ABS') {
      first.material = materialSuggestion.value.material
      applyWeightFromGeometry(first)
    }
  }
}

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
    const res = await stpParse(form)
    geometry.value = res.data.geometry
    densities.value = res.data.densities || {}
    undercut.value = res.data.geometry?.undercut || null
    materialSuggestion.value = res.data.geometry?.material_suggestion || null
    injection.value.file_name = file.name
    injection.value.parts.forEach(applyWeightFromGeometry)
    applyStpSuggestions()
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
  if (ocr.value.material?.value && injectionMaterials.includes(ocr.value.material.value)) {
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
    const res = await drawingParse(form)
    ocr.value = res.data.ocr
    applyOcrSuggestions()
  } catch (err) {
    ocrError.value = err.message || t('simpleQuote.ocrFailed')
  } finally {
    ocrParsing.value = false
    if (drawingInput.value) drawingInput.value.value = ''
  }
}

const print3d = ref({ material: 'PLA', model_weight_g: 30, print_hours: 4, quantity: 10, post_process: 'none', rush: false })
const generic = ref({ layers: 2, module_count: 3 })

const pcbaPackages = ['0402', '0603', '0805', '1206', 'SOT-23', 'SOP-8', 'SOP-16', 'QFN-16', 'QFN-24', 'DIP-CONN-2-10', 'CAP-2PIN']
const newComponent = () => ({ package: '0402', qty: 10, tech: 'smt' })
const pcba = ref({ pcb_quantity: 100, array_count: 1, components: [newComponent()] })

const pcbBaseOptions = [
  { no: 1, group: 'A', labelKey: 'pcbDev.a1' },
  { no: 2, group: 'A', labelKey: 'pcbDev.a2' },
  { no: 3, group: 'A', labelKey: 'pcbDev.a3' },
  { no: 4, group: 'A', labelKey: 'pcbDev.a4' },
  { no: 5, group: 'A', labelKey: 'pcbDev.a5' },
  { no: 6, group: 'A', labelKey: 'pcbDev.a6' },
  { no: 7, group: 'A', labelKey: 'pcbDev.a7' },
  { no: 8, group: 'A', labelKey: 'pcbDev.a8' },
  { no: 9, group: 'B', labelKey: 'pcbDev.b9' },
  { no: 10, group: 'B', labelKey: 'pcbDev.b10' },
]
const pcbWeightOptions = [
  { key: 'sample_only', labelKey: 'pcbDev.wSample' },
  { key: 'mass_production', labelKey: 'pcbDev.wMass' },
  { key: 'pcb_fr4', labelKey: 'pcbDev.wFr4' },
  { key: 'pcb_metal', labelKey: 'pcbDev.wMetal' },
  { key: 'qty_2', labelKey: 'pcbDev.wQty2' },
  { key: 'size_100', labelKey: 'pcbDev.wSize100' },
  { key: 'size_large', labelKey: 'pcbDev.wSizeLarge' },
]
const pcbServiceOptions = [
  { no: 1, labelKey: 'pcbDev.s1' }, { no: 2, labelKey: 'pcbDev.s2' }, { no: 9, labelKey: 'pcbDev.s9' },
  { no: 10, labelKey: 'pcbDev.s10' }, { no: 11, labelKey: 'pcbDev.s11' }, { no: 12, labelKey: 'pcbDev.s12' },
]
const pcbDev = ref({
  base_item_no: 2,
  weight_keys: ['mass_production', 'pcb_fr4', 'qty_2', 'size_100'],
  service_nos: [],
  ad_consent: false,
  shipping_weight_kg: 1,
})

const shippingMode = ref('air')
const shipping = ref({
  weight_kg: 0.6, length_cm: 20, width_cm: 20, height_cm: 10,
  cbm: 3, has_battery: false, service_days: 4, has_pickup: true, has_co: true,
})
const shippingResult = ref(null)
const shippingLoading = ref(false)
const shippingError = ref('')

const addComponent = () => pcba.value.components.push(newComponent())
const removeComponent = (i) => { if (pcba.value.components.length > 1) pcba.value.components.splice(i, 1) }

const onShippingEstimate = async () => {
  shippingError.value = ''
  shippingLoading.value = true
  shippingResult.value = null
  try {
    const payload = shippingMode.value === 'air'
      ? { mode: 'air', ...shipping.value }
      : { mode: 'lcl', ...shipping.value }
    const res = await shippingEstimate(payload)
    shippingResult.value = res.data
  } catch (e) {
    shippingError.value = e.message || t('shipping.failed')
  } finally {
    shippingLoading.value = false
  }
}

const print3dMaterials = ['PLA', 'ABS', 'PETG', 'Resin', 'Nylon', 'TPU']
const postProcesses = ['none', 'sanding', 'paint']

const familyMaterialMismatch = computed(() => {
  const mats = new Set(injection.value.parts.map((p) => p.material))
  return injection.value.parts.length > 1 && mats.size > 1
})

const addPart = () => injection.value.parts.push(newPart())
const removePart = (i) => { if (injection.value.parts.length > 1) injection.value.parts.splice(i, 1) }

const buildInputs = () => {
  if (quoteType.value === 'injection') {
    return {
      mold_material: injection.value.mold_material,
      is_precision: injection.value.is_precision,
      file_name: injection.value.file_name,
      parts: injection.value.parts.map((p) => ({
        material: p.material,
        color: p.color,
        weight_g: Number(p.weight_g) || 0,
        cavity: Number(p.cavity) || 1,
        slider_count: Number(p.slider_count) || 0,
        quantity: Number(p.quantity) || 1,
      })),
    }
  }
  if (quoteType.value === 'print3d') return { ...print3d.value }
  if (quoteType.value === 'pcba') {
    return {
      pcb_quantity: Number(pcba.value.pcb_quantity) || 1,
      array_count: Number(pcba.value.array_count) || 1,
      components: pcba.value.components.map((c) => ({
        package: c.package,
        qty: Number(c.qty) || 1,
        tech: c.tech,
      })),
    }
  }
  if (quoteType.value === 'pcb') {
    return {
      base_item_no: pcbDev.value.base_item_no,
      weight_keys: [...pcbDev.value.weight_keys],
      service_nos: [...pcbDev.value.service_nos],
      ad_consent: pcbDev.value.ad_consent,
      shipping_weight_kg: Number(pcbDev.value.shipping_weight_kg) || 1,
    }
  }
  return { ...generic.value }
}

const loadExisting = async (id) => {
  const res = await fetchSimpleQuote(id)
  result.value = res.data
  quoteType.value = res.data.quote_type
  productName.value = res.data.product_name
}

const onGenerate = async () => {
  error.value = ''
  if (quoteType.value === 'injection' && familyMaterialMismatch.value) {
    error.value = t('simpleQuote.familyMaterialHint')
    return
  }
  submitting.value = true
  try {
    const res = await createSimpleQuote({
      quote_type: quoteType.value,
      product_name: productName.value,
      inputs: buildInputs(),
    })
    result.value = res.data
    router.replace({ query: { id: res.data.id } })
  } catch (e) {
    error.value = e.message || t('simpleQuote.failed')
  } finally {
    submitting.value = false
  }
}

const onConvert = async () => {
  if (!result.value) return
  const res = await convertSimpleQuote(result.value.id, {})
  router.push({ name: 'my-rfq-detail', params: { id: res.data.rfq_id } })
}

const fmt = (n, digits = 0) => Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: digits })

onMounted(() => {
  if (route.query.id) loadExisting(route.query.id)
})
watch(() => route.query.id, (id) => { if (id) loadExisting(id); else result.value = null })
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ t('simpleQuote.title') }}</h1>
    <p class="page-lead">{{ t('simpleQuote.desc') }}</p>

    <div class="sq-layout">
      <section class="sq-form card">
        <label>{{ t('simpleQuote.type') }}
          <select v-model="quoteType">
            <option value="injection">{{ t('simpleQuote.injection') }}</option>
            <option value="print3d">{{ t('simpleQuote.print3d') }}</option>
            <option value="pcba">{{ t('simpleQuote.pcba') }}</option>
            <option value="pcb">{{ t('simpleQuote.pcbDev') }}</option>
            <option value="software">{{ t('simpleQuote.software') }}</option>
            <option value="ic">{{ t('simpleQuote.ic') }}</option>
          </select>
        </label>
        <label>{{ t('simpleQuote.productName') }}<input v-model="productName" type="text" /></label>

        <template v-if="quoteType === 'injection'">
          <div class="sq-stp">
            <button type="button" class="btn btn-sm btn-secondary" :disabled="parsing" @click="stpInput?.click()">
              {{ parsing ? t('simpleQuote.parsing') : t('simpleQuote.uploadStp') }}
            </button>
            <input ref="stpInput" type="file" accept=".stp,.step" hidden @change="onStpSelected" />
            <p class="sq-stp-hint">{{ t('simpleQuote.uploadStpHint') }}</p>
            <div v-if="geometry" class="sq-geo">
              <span>{{ t('simpleQuote.volume') }}: {{ geometry.volume_cm3 }} cm³</span>
              <span v-if="geometry.bbox_mm">{{ t('simpleQuote.dimensions') }}: {{ geometry.bbox_mm.join(' x ') }}</span>
              <span class="sq-geo-note">{{ t('simpleQuote.estimateNote') }}</span>
            </div>
            <div v-if="undercut && undercut.draw_direction" class="sq-suggest">
              <span>{{ t('simpleQuote.drawDirection') }}: {{ undercut.draw_direction }}</span>
              <span>{{ t('simpleQuote.sliderSuggest') }}: {{ undercut.suggested_sliders }}
                <em class="sq-badge">{{ t('simpleQuote.needReview') }}</em>
                <em class="sq-conf">{{ t('simpleQuote.confidence') }}: {{ t('simpleQuote.confidence' + (undercut.confidence === 'medium' ? 'Medium' : 'Low')) }}</em>
              </span>
            </div>
            <div v-if="materialSuggestion" class="sq-suggest">
              <span>{{ t('simpleQuote.materialSuggest') }}: {{ materialSuggestion.material }}
                <em class="sq-badge">{{ t('simpleQuote.needReview') }}</em>
                <em class="sq-conf">{{ t('simpleQuote.confidence') }}: {{ t('simpleQuote.confidenceLow') }}</em>
              </span>
            </div>
          </div>

          <div class="sq-stp">
            <button type="button" class="btn btn-sm btn-secondary" :disabled="ocrParsing" @click="drawingInput?.click()">
              {{ ocrParsing ? t('simpleQuote.ocrParsing') : t('simpleQuote.uploadDrawing') }}
            </button>
            <input ref="drawingInput" type="file" accept=".pdf,.png,.jpg,.jpeg" hidden @change="onDrawingSelected" />
            <p v-if="ocrError" class="page-message page-message--error">{{ ocrError }}</p>
            <div v-if="ocr" class="sq-suggest">
              <span v-if="ocr.material">{{ t('simpleQuote.materialSuggest') }}: {{ ocr.material.value }}
                <em class="sq-badge">{{ t('simpleQuote.needReview') }}</em>
              </span>
              <span v-if="ocr.precision">{{ t('simpleQuote.precisionSuggest') }}: ±{{ ocr.precision.value }}mm
                <em class="sq-badge">{{ t('simpleQuote.needReview') }}</em>
              </span>
              <span v-if="ocr.colors && ocr.colors.length">{{ t('simpleQuote.ocrColors') }}: {{ ocr.colors.join(', ') }}
                <em class="sq-badge">{{ t('simpleQuote.needReview') }}</em>
              </span>
            </div>
          </div>
          <div class="sq-row">
            <label>{{ t('simpleQuote.moldMaterial') }}
              <select v-model="injection.mold_material"><option v-for="m in moldMaterials" :key="m" :value="m">{{ m }}</option></select>
            </label>
            <label>{{ t('simpleQuote.fileName') }}<input v-model="injection.file_name" type="text" placeholder="part.stp" /></label>
          </div>
          <label class="checkbox"><input v-model="injection.is_precision" type="checkbox" /> {{ t('simpleQuote.precision') }}</label>

          <h3 class="sq-parts-title">{{ t('simpleQuote.family') }}</h3>
          <p v-if="familyMaterialMismatch" class="page-message page-message--error">{{ t('simpleQuote.familyMaterialHint') }}</p>
          <div v-for="(p, i) in injection.parts" :key="i" class="sq-part">
            <div class="sq-part-head">
              <span>{{ t('simpleQuote.part') }} {{ i + 1 }}</span>
              <button v-if="injection.parts.length > 1" type="button" class="btn btn-sm btn-secondary" @click="removePart(i)">{{ t('simpleQuote.removePart') }}</button>
            </div>
            <div class="sq-row">
              <label>{{ t('simpleQuote.material') }}
                <select v-model="p.material" @change="onMaterialChange(p)"><option v-for="m in injectionMaterials" :key="m" :value="m">{{ m }}</option></select>
              </label>
              <label>{{ t('simpleQuote.color') }}
                <select v-model="p.color">
                  <option value="normal">{{ t('simpleQuote.colorNormal') }}</option>
                  <option value="transparent">{{ t('simpleQuote.colorTransparent') }}</option>
                  <option value="semi">{{ t('simpleQuote.colorSemi') }}</option>
                  <option value="pantone">{{ t('simpleQuote.colorPantone') }}</option>
                </select>
              </label>
            </div>
            <div class="sq-row">
              <label>{{ t('simpleQuote.weight') }}<input v-model.number="p.weight_g" type="number" min="0" step="0.1" /></label>
              <label>{{ t('simpleQuote.cavity') }}<input v-model.number="p.cavity" type="number" min="1" /></label>
            </div>
            <div class="sq-row">
              <label>{{ t('simpleQuote.sliderCount') }}<input v-model.number="p.slider_count" type="number" min="0" /></label>
              <label>{{ t('simpleQuote.quantity') }}<input v-model.number="p.quantity" type="number" min="1" /></label>
            </div>
          </div>
          <button type="button" class="btn btn-sm btn-secondary sq-add" @click="addPart">+ {{ t('simpleQuote.addPart') }}</button>
        </template>

        <template v-else-if="quoteType === 'print3d'">
          <label>{{ t('simpleQuote.material') }}
            <select v-model="print3d.material"><option v-for="m in print3dMaterials" :key="m" :value="m">{{ m }}</option></select>
          </label>
          <label>{{ t('simpleQuote.weight') }}<input v-model.number="print3d.model_weight_g" type="number" min="0" /></label>
          <label>{{ t('simpleQuote.printHours') }}<input v-model.number="print3d.print_hours" type="number" min="0" step="0.5" /></label>
          <label>{{ t('simpleQuote.quantity') }}<input v-model.number="print3d.quantity" type="number" min="1" /></label>
          <label>{{ t('simpleQuote.postProcess') }}
            <select v-model="print3d.post_process"><option v-for="p in postProcesses" :key="p" :value="p">{{ p }}</option></select>
          </label>
        </template>

        <template v-else-if="quoteType === 'pcba'">
          <label>{{ t('simpleQuote.pcbQty') }}<input v-model.number="pcba.pcb_quantity" type="number" min="1" /></label>
          <label>{{ t('simpleQuote.arrayCount') }}<input v-model.number="pcba.array_count" type="number" min="1" /></label>
          <h3 class="sq-parts-title">{{ t('simpleQuote.components') }}</h3>
          <div v-for="(c, i) in pcba.components" :key="i" class="sq-part">
            <div class="sq-part-head">
              <span># {{ i + 1 }}</span>
              <button v-if="pcba.components.length > 1" type="button" class="btn btn-sm btn-secondary" @click="removeComponent(i)">{{ t('simpleQuote.removePart') }}</button>
            </div>
            <div class="sq-row">
              <label>{{ t('simpleQuote.package') }}
                <select v-model="c.package"><option v-for="p in pcbaPackages" :key="p" :value="p">{{ p }}</option></select>
              </label>
              <label>{{ t('simpleQuote.tech') }}
                <select v-model="c.tech"><option value="smt">SMT</option><option value="dip">DIP</option></select>
              </label>
            </div>
            <label>{{ t('simpleQuote.quantity') }}<input v-model.number="c.qty" type="number" min="1" /></label>
          </div>
          <button type="button" class="btn btn-sm btn-secondary sq-add" @click="addComponent">+ {{ t('simpleQuote.addComponent') }}</button>
        </template>

        <template v-else-if="quoteType === 'pcb'">
          <label>{{ t('pcbDev.baseType') }}
            <select v-model.number="pcbDev.base_item_no">
              <option v-for="opt in pcbBaseOptions" :key="opt.no" :value="opt.no">{{ t(opt.labelKey) }}</option>
            </select>
          </label>
          <fieldset class="sq-fieldset">
            <legend>{{ t('pcbDev.weights') }}</legend>
            <label v-for="w in pcbWeightOptions" :key="w.key" class="checkbox">
              <input v-model="pcbDev.weight_keys" type="checkbox" :value="w.key" /> {{ t(w.labelKey) }}
            </label>
          </fieldset>
          <fieldset class="sq-fieldset">
            <legend>{{ t('pcbDev.services') }}</legend>
            <label v-for="s in pcbServiceOptions" :key="s.no" class="checkbox">
              <input v-model="pcbDev.service_nos" type="checkbox" :value="s.no" /> {{ t(s.labelKey) }}
            </label>
          </fieldset>
          <label class="checkbox"><input v-model="pcbDev.ad_consent" type="checkbox" /> {{ t('pcbDev.adConsent') }}</label>
          <label>{{ t('pcbDev.shippingWeight') }}<input v-model.number="pcbDev.shipping_weight_kg" type="number" min="0" step="0.1" /></label>
          <p class="sq-stp-hint">{{ t('pcbDev.shippingHint') }}</p>
        </template>
        <template v-else-if="quoteType === 'software'">
          <label>Modules<input v-model.number="generic.module_count" type="number" min="0" /></label>
        </template>

        <p v-if="error" class="page-message page-message--error">{{ error }}</p>
        <button type="button" class="btn btn-primary" :disabled="submitting" @click="onGenerate">
          {{ t('simpleQuote.generate') }}
        </button>
      </section>

      <section class="sq-shipping card">
        <h2>{{ t('shipping.title') }}</h2>
        <p class="sq-stp-hint">{{ t('shipping.desc') }}</p>
        <label>{{ t('shipping.mode') }}
          <select v-model="shippingMode">
            <option value="air">{{ t('shipping.air') }}</option>
            <option value="lcl">{{ t('shipping.lcl') }}</option>
          </select>
        </label>
        <template v-if="shippingMode === 'air'">
          <div class="sq-row">
            <label>{{ t('shipping.weight') }}<input v-model.number="shipping.weight_kg" type="number" min="0" step="0.1" /></label>
            <label>{{ t('shipping.length') }}<input v-model.number="shipping.length_cm" type="number" min="0" /></label>
          </div>
          <div class="sq-row">
            <label>{{ t('shipping.width') }}<input v-model.number="shipping.width_cm" type="number" min="0" /></label>
            <label>{{ t('shipping.height') }}<input v-model.number="shipping.height_cm" type="number" min="0" /></label>
          </div>
        </template>
        <template v-else>
          <div class="sq-row">
            <label>CBM<input v-model.number="shipping.cbm" type="number" min="0" step="0.1" /></label>
            <label>{{ t('shipping.weight') }}<input v-model.number="shipping.weight_kg" type="number" min="0" /></label>
          </div>
          <label>{{ t('shipping.serviceDays') }}
            <select v-model.number="shipping.service_days"><option :value="4">4</option><option :value="5">5</option></select>
          </label>
          <label class="checkbox"><input v-model="shipping.has_battery" type="checkbox" /> {{ t('shipping.hasBattery') }}</label>
          <template v-if="!shipping.has_battery">
            <label class="checkbox"><input v-model="shipping.has_pickup" type="checkbox" /> {{ t('shipping.hasPickup') }}</label>
            <label class="checkbox"><input v-model="shipping.has_co" type="checkbox" /> {{ t('shipping.hasCo') }}</label>
          </template>
        </template>
        <p v-if="shippingError" class="page-message page-message--error">{{ shippingError }}</p>
        <button type="button" class="btn btn-secondary btn-sm" :disabled="shippingLoading" @click="onShippingEstimate">
          {{ shippingLoading ? t('shipping.calculating') : t('shipping.estimate') }}
        </button>
        <ul v-if="shippingResult" class="sq-breakdown">
          <li v-for="(item, i) in shippingResult.breakdown || []" :key="i">
            <span>{{ item.label }}</span><span>{{ item.amount }} {{ item.unit || 'KRW' }}</span>
          </li>
          <li><span>{{ t('shipping.total') }}</span><strong>KRW {{ fmt(shippingResult.fee_krw) }}</strong></li>
        </ul>
        <p v-if="shippingResult?.comparison" class="sq-stp-hint">
          {{ t('shipping.compareDays', { days: shippingResult.comparison.service_days, fee: fmt(shippingResult.comparison.fee_krw) }) }}
        </p>
      </section>

      <section v-if="result" class="sq-result card">
        <h2>{{ t('simpleQuote.result') }}</h2>
        <p class="sq-no">{{ result.quote_no }}</p>

        <template v-if="result.quote_type === 'injection'">
          <ul class="sq-breakdown">
            <li><span>{{ t('simpleQuote.moldFee') }}</span><span>{{ result.currency }} {{ fmt(result.result?.mold_fee) }}</span></li>
            <li><span>{{ t('simpleQuote.productTotal') }}</span><span>{{ result.currency }} {{ fmt(result.result?.product_total) }}</span></li>
          </ul>
          <table class="sq-parts-table">
            <thead><tr><th>{{ t('simpleQuote.material') }}</th><th>{{ t('simpleQuote.color') }}</th><th>{{ t('simpleQuote.weight') }}</th><th>{{ t('simpleQuote.unitPrice') }}</th></tr></thead>
            <tbody>
              <tr v-for="(p, i) in result.result?.parts || []" :key="i">
                <td>{{ p.material }}</td>
                <td>{{ t('simpleQuote.color' + (p.color === 'transparent' ? 'Transparent' : p.color === 'semi' ? 'Semi' : p.color === 'pantone' ? 'Pantone' : 'Normal')) }}</td>
                <td>{{ p.weight_g }}g</td>
                <td>{{ result.currency }} {{ fmt(p.unit_price, 4) }}</td>
              </tr>
            </tbody>
          </table>
          <p class="sq-total">{{ t('simpleQuote.total') }}: <strong>{{ result.currency }} {{ fmt(result.total_amount) }}</strong></p>
          <p v-if="result.result?.total_krw" class="sq-krw">{{ t('simpleQuote.krwConverted') }}: KRW {{ fmt(result.result.total_krw) }}</p>
          <p class="sq-moq">{{ t('simpleQuote.moqHint', { kg: result.result?.moq_kg || 25 }) }}</p>
        </template>

        <template v-else-if="result.quote_type === 'pcba'">
          <ul class="sq-breakdown">
            <li v-for="(item, i) in result.result?.breakdown || []" :key="i">
              <span>{{ item.label }}</span><span>{{ result.currency }} {{ fmt(item.amount) }}</span>
            </li>
          </ul>
          <p v-if="result.result?.warnings?.length" class="sq-stp-hint">{{ result.result.warnings.join('; ') }}</p>
          <p class="sq-total">{{ t('simpleQuote.total') }}: <strong>{{ result.currency }} {{ fmt(result.total_amount) }}</strong></p>
          <p v-if="result.result?.total_krw" class="sq-krw">{{ t('simpleQuote.krwConverted') }}: KRW {{ fmt(result.result.total_krw) }}</p>
        </template>

        <template v-else-if="result.quote_type === 'pcb'">
          <ul class="sq-breakdown">
            <li v-for="(item, i) in result.result?.breakdown || []" :key="i">
              <span>{{ item.label }}</span><span>{{ result.currency }} {{ fmt(item.amount) }}</span>
            </li>
          </ul>
          <p class="sq-total">{{ t('simpleQuote.total') }}: <strong>{{ result.currency }} {{ fmt(result.total_amount) }}</strong></p>
          <p class="sq-stp-hint">{{ t('pcbDev.vatExcluded') }}</p>
        </template>

        <template v-else>
          <ul class="sq-breakdown">
            <li v-for="(item, i) in result.result?.breakdown || []" :key="i">
              <span>{{ item.label }}</span><span>{{ result.currency }} {{ fmt(item.amount) }}</span>
            </li>
          </ul>
          <p class="sq-total">{{ t('simpleQuote.total') }}: <strong>{{ result.currency }} {{ fmt(result.total_amount) }}</strong></p>
        </template>

        <div class="sq-actions">
          <a v-if="result.pdf_url" :href="result.pdf_url" target="_blank" rel="noopener" class="btn btn-secondary btn-sm">PDF</a>
          <button v-if="!result.converted_rfq" type="button" class="btn btn-primary btn-sm" @click="onConvert">{{ t('simpleQuote.convert') }}</button>
        </div>
      </section>
    </div>
  </PageShell>
</template>

<style scoped lang="scss">
.sq-layout { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-2xl); align-items: start; }
.sq-shipping { display: flex; flex-direction: column; gap: var(--space-md); grid-column: 1 / -1; label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.875rem; } label.checkbox { flex-direction: row; align-items: center; gap: 0.5rem; } select, input { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); } }
.sq-fieldset { border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: var(--space-md); display: flex; flex-direction: column; gap: 0.35rem; legend { font-size: 0.85rem; font-weight: 600; } }
.card { padding: var(--space-xl); border: 1px solid var(--color-border); border-radius: var(--radius-md); }
.sq-form { display: flex; flex-direction: column; gap: var(--space-md); label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.875rem; } label.checkbox { flex-direction: row; align-items: center; gap: 0.5rem; } select, input { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); } }
.sq-row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md); }
.sq-stp { display: flex; flex-direction: column; gap: 0.375rem; padding: var(--space-md); border: 1px dashed var(--color-border); border-radius: var(--radius-sm); }
.sq-stp-hint { font-size: 0.78rem; color: var(--color-text-muted); margin: 0; }
.sq-geo { display: flex; flex-wrap: wrap; gap: var(--space-md); font-size: 0.82rem; }
.sq-geo-note { color: var(--color-steel); }
.sq-suggest { display: flex; flex-wrap: wrap; gap: var(--space-md); font-size: 0.82rem; margin-top: 0.25rem; }
.sq-badge { font-style: normal; font-size: 0.7rem; padding: 0.05rem 0.4rem; margin-left: 0.35rem; border-radius: var(--radius-sm); background: var(--color-warning-soft, #fff3cd); color: var(--color-warning-strong, #8a6d00); }
.sq-conf { font-style: normal; font-size: 0.72rem; color: var(--color-text-muted); margin-left: 0.35rem; }
.sq-parts-title { font-size: 0.95rem; margin: var(--space-sm) 0 0; }
.sq-part { border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: var(--space-md); display: flex; flex-direction: column; gap: var(--space-sm); }
.sq-part-head { display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; font-weight: 600; }
.sq-add { align-self: flex-start; }
.sq-result { display: flex; flex-direction: column; gap: var(--space-sm); }
.sq-no { font-size: 0.85rem; opacity: 0.6; margin: 0; }
.sq-breakdown { list-style: none; padding: 0; margin: 0; li { display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--color-border); font-size: 0.9rem; } }
.sq-parts-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; th, td { text-align: left; padding: 0.4rem 0.5rem; border-bottom: 1px solid var(--color-border); } th { color: var(--color-text-muted); font-weight: 500; } td:last-child, th:last-child { text-align: right; } }
.sq-total { font-size: 1.1rem; margin-top: var(--space-sm); }
.sq-krw { font-size: 0.9rem; color: var(--color-text-muted); margin: 0; }
.sq-moq { font-size: 0.8rem; color: var(--color-steel); margin: 0; }
.sq-actions { display: flex; gap: var(--space-md); margin-top: var(--space-md); }
@media (max-width: 768px) { .sq-layout { grid-template-columns: 1fr; } }
</style>
