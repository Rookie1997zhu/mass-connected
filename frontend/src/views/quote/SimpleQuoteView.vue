<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { convertSimpleQuote, createSimpleQuote, fetchSimpleQuote } from '../../api'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const quoteType = ref('injection')
const productName = ref('')
const error = ref('')
const result = ref(null)
const submitting = ref(false)

const injection = ref({ material: 'ABS', product_weight_g: 50, cavity: 1, quantity: 1000, mold_type: 'standard', packaging: true })
const print3d = ref({ material: 'PLA', model_weight_g: 30, print_hours: 4, quantity: 10, post_process: 'none', rush: false })
const generic = ref({ layers: 2, module_count: 3 })

const injectionMaterials = ['ABS', 'PC', 'PMMA', 'PP', 'PA66', 'POM', 'TPE', 'TPU']
const moldTypes = ['simple', 'standard', 'precision', 'hotrunner', 'slider']
const print3dMaterials = ['PLA', 'ABS', 'PETG', 'Resin', 'Nylon', 'TPU']
const postProcesses = ['none', 'sanding', 'paint']

const buildInputs = () => {
  if (quoteType.value === 'injection') return { ...injection.value }
  if (quoteType.value === 'print3d') return { ...print3d.value }
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

const onConvert = async () => {
  if (!result.value) return
  const res = await convertSimpleQuote(result.value.id, {})
  router.push(`/my/rfqs/${res.data.rfq_id}`)
}

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
            <option value="pcb">{{ t('simpleQuote.pcb') }}</option>
            <option value="software">{{ t('simpleQuote.software') }}</option>
            <option value="ic">{{ t('simpleQuote.ic') }}</option>
          </select>
        </label>
        <label>{{ t('simpleQuote.productName') }}<input v-model="productName" type="text" /></label>

        <template v-if="quoteType === 'injection'">
          <label>{{ t('simpleQuote.material') }}
            <select v-model="injection.material"><option v-for="m in injectionMaterials" :key="m" :value="m">{{ m }}</option></select>
          </label>
          <label>{{ t('simpleQuote.weight') }}<input v-model.number="injection.product_weight_g" type="number" min="0" /></label>
          <label>{{ t('simpleQuote.cavity') }}<input v-model.number="injection.cavity" type="number" min="1" /></label>
          <label>{{ t('simpleQuote.quantity') }}<input v-model.number="injection.quantity" type="number" min="1" /></label>
          <label>{{ t('simpleQuote.moldType') }}
            <select v-model="injection.mold_type"><option v-for="m in moldTypes" :key="m" :value="m">{{ m }}</option></select>
          </label>
          <label class="checkbox"><input v-model="injection.packaging" type="checkbox" /> {{ t('simpleQuote.packaging') }}</label>
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

        <template v-else-if="quoteType === 'pcb'">
          <label>Layers<input v-model.number="generic.layers" type="number" min="1" /></label>
        </template>
        <template v-else-if="quoteType === 'software'">
          <label>Modules<input v-model.number="generic.module_count" type="number" min="0" /></label>
        </template>

        <p v-if="error" class="page-message page-message--error">{{ error }}</p>
        <button type="button" class="btn btn-primary" :disabled="submitting" @click="onGenerate">
          {{ t('simpleQuote.generate') }}
        </button>
      </section>

      <section v-if="result" class="sq-result card">
        <h2>{{ t('simpleQuote.result') }}</h2>
        <p class="sq-no">{{ result.quote_no }}</p>
        <ul class="sq-breakdown">
          <li v-for="(item, i) in result.result?.breakdown || []" :key="i">
            <span>{{ item.label }}</span><span>{{ result.currency }} {{ Number(item.amount).toLocaleString() }}</span>
          </li>
        </ul>
        <p class="sq-total">{{ t('simpleQuote.total') }}: <strong>{{ result.currency }} {{ Number(result.total_amount).toLocaleString() }}</strong></p>
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
.card { padding: var(--space-xl); border: 1px solid var(--color-border); border-radius: var(--radius-md); }
.sq-form { display: flex; flex-direction: column; gap: var(--space-md); label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.875rem; } label.checkbox { flex-direction: row; align-items: center; gap: 0.5rem; } select, input { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); } }
.sq-result { display: flex; flex-direction: column; gap: var(--space-sm); }
.sq-no { font-size: 0.85rem; opacity: 0.6; margin: 0; }
.sq-breakdown { list-style: none; padding: 0; margin: 0; li { display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--color-border); font-size: 0.9rem; } }
.sq-total { font-size: 1.1rem; margin-top: var(--space-sm); }
.sq-actions { display: flex; gap: var(--space-md); margin-top: var(--space-md); }
@media (max-width: 768px) { .sq-layout { grid-template-columns: 1fr; } }
</style>
