<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import InjectionQuoteSheet from '../../components/quote/InjectionQuoteSheet.vue'
import Print3dQuoteSheet from '../../components/quote/Print3dQuoteSheet.vue'
import { useLocaleCurrency } from '../../composables/useLocaleCurrency'
import { convertSimpleQuote, createSimpleQuote, fetchSimpleQuote, shippingEstimate } from '../../api'

const { t } = useI18n()
const { formatMoney, fromQuote } = useLocaleCurrency()
const route = useRoute()
const router = useRouter()

const quoteType = ref('injection')
const productName = ref('')
const error = ref('')
const result = ref(null)
const submitting = ref(false)

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
const pcbManufacturingMaterials = [
  { value: 'fr4', labelKey: 'pcbDev.mfgFr4' },
  { value: 'fpc', labelKey: 'pcbDev.mfgFpc' },
  { value: 'aluminum', labelKey: 'pcbDev.mfgAluminum' },
  { value: 'other', labelKey: 'pcbDev.mfgOther' },
]
const pcbProcessOptions = {
  fr4: {
    boardThickness: ['1.0', '1.2', '1.6', '2.0'],
    solderColor: ['绿色', '红色', '黄色', '蓝色', '白色', '哑黑色'],
    surfaceFinish: ['OSP', '有铅喷锡', '无铅喷锡', '沉金'],
    copperThickness: ['1oz'],
    solderMaskCoverage: ['过孔盖油', '过孔开窗', '过孔塞油', '过孔塞树脂+过孔电镀盖帽'],
    panelDesignCount: ['1', '2'],
    defaults: ['1.6', '绿色', '有铅喷锡', '1oz', '过孔盖油', '1'],
  },
  fpc: {
    boardThickness: ['0.11', '0.12', '0.20'],
    solderColor: ['页面默认'],
    surfaceFinish: ['沉金'],
    copperThickness: ['1oz'],
    solderMaskCoverage: ['页面默认'],
    panelDesignCount: ['1', '2'],
    defaults: ['0.11', '页面默认', '沉金', '1oz', '页面默认', '1'],
  },
  aluminum: {
    boardThickness: ['1.0', '1.2', '1.6'],
    solderColor: ['绿色', '红色', '黄色', '蓝色', '白色', '哑黑色'],
    surfaceFinish: ['无铅喷锡'],
    copperThickness: ['1oz'],
    solderMaskCoverage: ['页面默认'],
    panelDesignCount: ['1', '2'],
    defaults: ['1.6', '绿色', '无铅喷锡', '1oz', '页面默认', '1'],
  },
}
const pcbDev = ref({
  base_item_no: 2,
  weight_keys: ['mass_production', 'pcb_fr4', 'qty_2', 'size_100'],
  service_nos: [],
  ad_consent: false,
  shipping_weight_kg: 1,
  include_pcb_manufacturing: false,
  mfg_material: 'fr4',
  mfg_layers: 2,
  mfg_width_mm: 100,
  mfg_height_mm: 100,
  mfg_quantity: 5,
  mfg_board_thickness: '1.6',
  mfg_solder_color: '绿色',
  mfg_surface_finish: '有铅喷锡',
  mfg_copper_thickness: '1oz',
  mfg_solder_mask_coverage: '过孔盖油',
  mfg_panel_design_count: '1',
  mfg_smt_required: false,
})
const currentPcbProcessOptions = computed(() => {
  const options = pcbProcessOptions[pcbDev.value.mfg_material] || {
    boardThickness: [],
    solderColor: [],
    surfaceFinish: [],
    copperThickness: [],
    solderMaskCoverage: [],
    panelDesignCount: [],
    defaults: ['', '', '', '', '', ''],
  }
  let boardThickness = options.boardThickness
  if (pcbDev.value.mfg_material === 'fpc' && Number(pcbDev.value.mfg_layers) === 1) {
    boardThickness = ['0.11']
  }
  if (pcbDev.value.mfg_material === 'fr4' && Number(pcbDev.value.mfg_layers) === 4) {
    boardThickness = boardThickness.filter((value) => value !== '2.0')
  }
  return { ...options, boardThickness }
})

watch(() => pcbDev.value.mfg_material, (material) => {
  if (material === 'aluminum') {
    pcbDev.value.mfg_layers = 1
  } else if (material === 'fr4' && ![2, 4].includes(Number(pcbDev.value.mfg_layers))) {
    pcbDev.value.mfg_layers = 2
  } else if (material === 'fpc' && ![1, 2].includes(Number(pcbDev.value.mfg_layers))) {
    pcbDev.value.mfg_layers = 2
  }
  const options = pcbProcessOptions[material]
  if (options) {
    [
      pcbDev.value.mfg_board_thickness,
      pcbDev.value.mfg_solder_color,
      pcbDev.value.mfg_surface_finish,
      pcbDev.value.mfg_copper_thickness,
      pcbDev.value.mfg_solder_mask_coverage,
      pcbDev.value.mfg_panel_design_count,
    ] = options.defaults
  }
})
watch(() => pcbDev.value.mfg_layers, () => {
  const allowed = currentPcbProcessOptions.value.boardThickness
  if (!allowed.includes(pcbDev.value.mfg_board_thickness)) {
    pcbDev.value.mfg_board_thickness = allowed[0] || ''
  }
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

const buildInputs = () => {
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
      include_pcb_manufacturing: pcbDev.value.include_pcb_manufacturing,
      mfg_material: pcbDev.value.mfg_material,
      mfg_layers: Number(pcbDev.value.mfg_layers) || 0,
      mfg_width_mm: Number(pcbDev.value.mfg_width_mm) || 0,
      mfg_height_mm: Number(pcbDev.value.mfg_height_mm) || 0,
      mfg_quantity: Number(pcbDev.value.mfg_quantity) || 0,
      mfg_board_thickness: pcbDev.value.mfg_board_thickness,
      mfg_solder_color: pcbDev.value.mfg_solder_color,
      mfg_surface_finish: pcbDev.value.mfg_surface_finish,
      mfg_copper_thickness: pcbDev.value.mfg_copper_thickness,
      mfg_solder_mask_coverage: pcbDev.value.mfg_solder_mask_coverage,
      mfg_panel_design_count: pcbDev.value.mfg_panel_design_count,
      mfg_smt_required: pcbDev.value.mfg_smt_required,
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

const onInjectionGenerated = (data) => {
  result.value = data
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
  <PageShell :container-wide="quoteType === 'injection' || quoteType === 'print3d'">
    <h1 class="page-title">{{ t('simpleQuote.title') }}</h1>
    <p class="page-lead">{{ t('simpleQuote.desc') }}</p>

    <label class="sq-type-select">{{ t('simpleQuote.type') }}
      <select v-model="quoteType">
        <option value="injection">{{ t('simpleQuote.injection') }}</option>
        <option value="print3d">{{ t('simpleQuote.print3d') }}</option>
        <option value="pcba">{{ t('simpleQuote.pcba') }}</option>
        <option value="pcb">{{ t('simpleQuote.pcbDev') }}</option>
        <option value="software">{{ t('simpleQuote.software') }}</option>
        <option value="ic">{{ t('simpleQuote.ic') }}</option>
      </select>
    </label>

    <InjectionQuoteSheet
      v-if="quoteType === 'injection'"
      v-model:product-name="productName"
      :saved-result="result?.quote_type === 'injection' ? result : null"
      @generated="onInjectionGenerated"
      @convert="onConvert"
    />

    <Print3dQuoteSheet
      v-else-if="quoteType === 'print3d'"
      v-model:product-name="productName"
      :saved-result="result?.quote_type === 'print3d' ? result : null"
      @generated="onInjectionGenerated"
      @convert="onConvert"
    />

    <div v-else class="sq-layout">
      <section class="sq-form card">
        <label>{{ t('simpleQuote.productName') }}<input v-model="productName" type="text" /></label>

        <template v-if="quoteType === 'pcba'">
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
          <fieldset class="sq-fieldset">
            <legend>{{ t('pcbDev.mfgTitle') }}</legend>
            <label class="checkbox">
              <input v-model="pcbDev.include_pcb_manufacturing" type="checkbox" /> {{ t('pcbDev.mfgInclude') }}
            </label>
            <template v-if="pcbDev.include_pcb_manufacturing">
              <label>{{ t('pcbDev.mfgMaterial') }}
                <select v-model="pcbDev.mfg_material">
                  <option v-for="m in pcbManufacturingMaterials" :key="m.value" :value="m.value">{{ t(m.labelKey) }}</option>
                </select>
              </label>
              <div class="sq-row">
                <label>{{ t('pcbDev.mfgLayers') }}<input v-model.number="pcbDev.mfg_layers" type="number" min="1" /></label>
                <label>{{ t('pcbDev.mfgQuantity') }}<input v-model.number="pcbDev.mfg_quantity" type="number" min="1" /></label>
              </div>
              <div class="sq-row">
                <label>{{ t('pcbDev.mfgWidth') }}<input v-model.number="pcbDev.mfg_width_mm" type="number" min="1" /></label>
                <label>{{ t('pcbDev.mfgHeight') }}<input v-model.number="pcbDev.mfg_height_mm" type="number" min="1" /></label>
              </div>
              <div class="sq-row">
                <label>{{ t('pcbDev.mfgBoardThickness') }}
                  <select v-model="pcbDev.mfg_board_thickness">
                    <option v-for="value in currentPcbProcessOptions.boardThickness" :key="value" :value="value">{{ value }}mm</option>
                  </select>
                </label>
                <label>{{ t('pcbDev.mfgCopperThickness') }}
                  <select v-model="pcbDev.mfg_copper_thickness">
                    <option v-for="value in currentPcbProcessOptions.copperThickness" :key="value" :value="value">{{ value }}</option>
                  </select>
                </label>
              </div>
              <div class="sq-row">
                <label>{{ t('pcbDev.mfgSolderColor') }}
                  <select v-model="pcbDev.mfg_solder_color">
                    <option v-for="value in currentPcbProcessOptions.solderColor" :key="value" :value="value">{{ t(`pcbDev.process.${value}`) }}</option>
                  </select>
                </label>
                <label>{{ t('pcbDev.mfgSurfaceFinish') }}
                  <select v-model="pcbDev.mfg_surface_finish">
                    <option v-for="value in currentPcbProcessOptions.surfaceFinish" :key="value" :value="value">{{ t(`pcbDev.process.${value}`) }}</option>
                  </select>
                </label>
              </div>
              <div class="sq-row">
                <label>{{ t('pcbDev.mfgSolderMaskCoverage') }}
                  <select v-model="pcbDev.mfg_solder_mask_coverage">
                    <option v-for="value in currentPcbProcessOptions.solderMaskCoverage" :key="value" :value="value">{{ t(`pcbDev.process.${value}`) }}</option>
                  </select>
                </label>
                <label>{{ t('pcbDev.mfgPanelDesignCount') }}
                  <select v-model="pcbDev.mfg_panel_design_count">
                    <option v-for="value in currentPcbProcessOptions.panelDesignCount" :key="value" :value="value">{{ value }}</option>
                  </select>
                </label>
              </div>
              <label class="checkbox sq-smt-label">
                <input v-model="pcbDev.mfg_smt_required" type="checkbox" />
                <span>{{ t('pcbDev.mfgSmtRequired') }}</span>
                <span class="sq-stp-hint">{{ t('pcbDev.smtNotIncludedHint') }}</span>
              </label>
              <p class="sq-stp-hint">{{ t('pcbDev.mfgHint') }}</p>
            </template>
          </fieldset>
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
            <span>{{ item.label }}</span><span>{{ formatMoney({ amount: item.amount, currency: item.unit || 'KRW' }) }}</span>
          </li>
          <li><span>{{ t('shipping.total') }}</span><strong>{{ formatMoney({ amount: shippingResult.fee_krw, currency: 'KRW' }) }}</strong></li>
        </ul>
        <p v-if="shippingResult?.comparison" class="sq-stp-hint">
          {{ t('shipping.compareDays', { days: shippingResult.comparison.service_days, fee: formatMoney({ amount: shippingResult.comparison.fee_krw, currency: 'KRW' }) }) }}
        </p>
      </section>

      <section v-if="result" class="sq-result card">
        <h2>{{ t('simpleQuote.result') }}</h2>
        <p class="sq-no">{{ result.quote_no }}</p>

        <template v-if="result.quote_type === 'pcba'">
          <ul class="sq-breakdown">
            <li v-for="(item, i) in result.result?.breakdown || []" :key="i">
              <span>{{ item.label }}</span><span>{{ fromQuote(item.amount, result) }}</span>
            </li>
          </ul>
          <p v-if="result.result?.warnings?.length" class="sq-stp-hint">{{ result.result.warnings.join('; ') }}</p>
          <p class="sq-total">{{ t('simpleQuote.total') }}: <strong>{{ fromQuote(result.total_amount, result) }}</strong></p>
        </template>

        <template v-else-if="result.quote_type === 'pcb'">
          <ul class="sq-breakdown">
            <li v-for="(item, i) in result.result?.breakdown || []" :key="i">
              <span>{{ item.label }}</span><span>{{ fromQuote(item.amount, result) }}</span>
            </li>
          </ul>
          <div v-if="result.result?.pcb_manufacturing?.enabled" class="sq-manufacturing">
            <strong>{{ t('pcbDev.mfgTitle') }}</strong>
            <p v-if="!result.result.pcb_manufacturing.requires_manual_review">
              {{ t('pcbDev.mfgAutoQuoted') }}:
              CNY {{ fmt(result.result.pcb_manufacturing.customer_quote_cny, 2) }}
              /
              KRW {{ fmt(result.result.pcb_manufacturing.customer_quote_krw) }}
            </p>
            <p
              v-if="!result.result.pcb_manufacturing.requires_manual_review"
              class="sq-mfg-mode"
              :class="{ 'is-estimated': result.result.pcb_manufacturing.is_estimated }"
            >
              {{ t('pcbDev.mfgPricingMode') }}:
              {{ t(result.result.pcb_manufacturing.is_estimated ? 'pcbDev.mfgEstimated' : 'pcbDev.mfgExact') }}
              <template v-if="result.result.pcb_manufacturing.is_estimated">
                · {{ t('pcbDev.mfgConfidence') }}
                {{ fmt((result.result.pcb_manufacturing.confidence || 0) * 100, 1) }}%
              </template>
            </p>
            <p v-if="result.result.pcb_manufacturing.is_estimated" class="sq-stp-hint">
              {{ t('pcbDev.mfgEstimateNote') }}
            </p>
            <p v-if="result.result.pcb_manufacturing.selected_process" class="sq-stp-hint">
              {{ t('pcbDev.mfgProcess') }}:
              {{ result.result.pcb_manufacturing.selected_process.board_thickness }}mm ·
              {{ t(`pcbDev.process.${result.result.pcb_manufacturing.selected_process.solder_color}`) }} ·
              {{ t(`pcbDev.process.${result.result.pcb_manufacturing.selected_process.surface_finish}`) }} ·
              {{ result.result.pcb_manufacturing.selected_process.copper_thickness }}
              <template v-if="result.result.pcb_manufacturing.selected_process.solder_mask_coverage">
                · {{ t(`pcbDev.process.${result.result.pcb_manufacturing.selected_process.solder_mask_coverage}`) }}
              </template>
              <template v-if="result.result.pcb_manufacturing.selected_process.panel_design_count">
                · {{ t('pcbDev.mfgPanelDesignCount') }} {{ result.result.pcb_manufacturing.selected_process.panel_design_count }}
              </template>
            </p>
            <p v-if="result.result.pcb_manufacturing.smt_required" class="sq-stp-hint">
              {{ t('pcbDev.mfgSmtRequired') }} · {{ t('pcbDev.smtNotIncludedHint') }}
            </p>
            <p v-if="result.result.pcb_manufacturing.risk_status" class="sq-stp-hint">
              {{ t('pcbDev.mfgRiskStatus') }}: {{ result.result.pcb_manufacturing.risk_status }}
            </p>
            <p v-if="result.result.pcb_manufacturing.requires_manual_review">
              {{ t('pcbDev.mfgManualReview') }}:
              {{ (result.result.pcb_manufacturing.manual_review_reasons || []).join(' / ') }}
            </p>
            <p class="sq-stp-hint">
              {{ t('pcbDev.mfgVersion') }}: {{ result.result.pcb_manufacturing.active_price_version || result.result.pcb_manufacturing.price_version || '-' }}
              /
              {{ t('pcbDev.mfgValidationStatus') }}: {{ result.result.pcb_manufacturing.validation_status || '-' }}
              /
              {{ t('pcbDev.mfgAcceptanceStatus') }}: {{ result.result.pcb_manufacturing.acceptance_status || t('pcbDev.mfgAcceptanceLegacy') }}
            </p>
            <p
              v-if="result.result.pcb_manufacturing.acceptance_status && result.result.pcb_manufacturing.acceptance_status !== 'passed'"
              class="sq-stp-hint"
            >
              {{ t('pcbDev.mfgAcceptanceFailedHint') }}
              ({{ t('pcbDev.mfgFallbackVersion') }}: {{ result.result.pcb_manufacturing.fallback_version || 'jlc-cn-pcb-v6-20260712' }})
            </p>
          </div>
          <p class="sq-total">{{ t('simpleQuote.total') }}: <strong>{{ fromQuote(result.total_amount, result) }}</strong></p>
          <p class="sq-stp-hint">{{ t('pcbDev.vatExcluded') }}</p>
        </template>

        <template v-else>
          <ul class="sq-breakdown">
            <li v-for="(item, i) in result.result?.breakdown || []" :key="i">
              <span>{{ item.label }}</span><span>{{ fromQuote(item.amount, result) }}</span>
            </li>
          </ul>
          <p class="sq-total">{{ t('simpleQuote.total') }}: <strong>{{ fromQuote(result.total_amount, result) }}</strong></p>
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
.sq-type-select {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  font-size: 0.875rem;
  max-width: 320px;
  margin-bottom: var(--space-lg);
  select { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
}

.sq-mfg-mode {
  display: inline-flex;
  width: fit-content;
  margin: 0.25rem 0;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--primary, #2563eb) 10%, transparent);
  font-size: 0.82rem;
  font-weight: 600;
}

.sq-mfg-mode.is-estimated {
  background: color-mix(in srgb, #d97706 12%, transparent);
  color: #92400e;
}
.sq-layout { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-2xl); align-items: start; }
.sq-shipping { display: flex; flex-direction: column; gap: var(--space-md); grid-column: 1 / -1; label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.875rem; } label.checkbox { flex-direction: row; align-items: center; gap: 0.5rem; } select, input { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); } }
.sq-fieldset { border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: var(--space-md); display: flex; flex-direction: column; gap: 0.35rem; legend { font-size: 0.85rem; font-weight: 600; } }
.card { padding: var(--space-xl); border: 1px solid var(--color-border); border-radius: var(--radius-md); }
.sq-form { display: flex; flex-direction: column; gap: var(--space-md); label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.875rem; } label.checkbox { flex-direction: row; align-items: center; gap: 0.5rem; } select, input { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); } }
.sq-row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md); }
.sq-stp-hint { font-size: 0.78rem; color: var(--color-text-muted); margin: 0; }
.sq-parts-title { font-size: 0.95rem; margin: var(--space-sm) 0 0; }
.sq-part { border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: var(--space-md); display: flex; flex-direction: column; gap: var(--space-sm); }
.sq-part-head { display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; font-weight: 600; }
.sq-add { align-self: flex-start; }
.sq-result { display: flex; flex-direction: column; gap: var(--space-sm); }
.sq-no { font-size: 0.85rem; opacity: 0.6; margin: 0; }
.sq-breakdown { list-style: none; padding: 0; margin: 0; li { display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--color-border); font-size: 0.9rem; } }
.sq-manufacturing { border: 1px dashed var(--color-border); border-radius: var(--radius-sm); padding: var(--space-md); font-size: 0.88rem; p { margin: 0.35rem 0 0; } }
.sq-total { font-size: 1.1rem; margin-top: var(--space-sm); }
.sq-krw { font-size: 0.9rem; color: var(--color-text-muted); margin: 0; }
.sq-smt-label { gap: 0.5rem; align-items: center; flex-wrap: wrap; .sq-stp-hint { margin: 0; } }
.sq-actions { display: flex; gap: var(--space-md); margin-top: var(--space-md); }
@media (max-width: 768px) { .sq-layout { grid-template-columns: 1fr; } }
</style>
