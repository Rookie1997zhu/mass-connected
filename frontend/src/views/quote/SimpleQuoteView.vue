<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import InjectionQuoteSheet from '../../components/quote/InjectionQuoteSheet.vue'
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

const buildInputs = () => {
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
  <PageShell :container-wide="quoteType === 'injection'">
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

    <div v-else class="sq-layout">
      <section class="sq-form card">
        <label>{{ t('simpleQuote.productName') }}<input v-model="productName" type="text" /></label>

        <template v-if="quoteType === 'print3d'">
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
.sq-total { font-size: 1.1rem; margin-top: var(--space-sm); }
.sq-krw { font-size: 0.9rem; color: var(--color-text-muted); margin: 0; }
.sq-actions { display: flex; gap: var(--space-md); margin-top: var(--space-md); }
@media (max-width: 768px) { .sq-layout { grid-template-columns: 1fr; } }
</style>
