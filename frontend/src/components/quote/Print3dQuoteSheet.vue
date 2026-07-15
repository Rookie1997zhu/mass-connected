<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import StpViewer3d from './StpViewer3d.vue'
import { useLocaleCurrency } from '../../composables/useLocaleCurrency'
import {
  createPrint3dSliceJob,
  createSimpleQuote,
  fetchPrint3dOptions,
  fetchPrint3dSliceJob,
  previewSimpleQuote,
  stpParse,
} from '../../api'

const productName = defineModel('productName', { type: String, default: '' })
const props = defineProps({
  savedResult: { type: Object, default: null },
})
const emit = defineEmits(['generated', 'convert'])

const { t } = useI18n()
const router = useRouter()
const { fromQuote, fromPreview, displayCurrency } = useLocaleCurrency()

const fileInput = ref(null)
const parsing = ref(false)
const slicing = ref(false)
const submitting = ref(false)
const error = ref('')
const previewMesh = ref(null)
const options = ref({
  materials: [],
  qualities: [],
  post_processing: [],
  infill: { min: 5, max: 100, default: 20 },
})
const form = ref({
  material: 'PLA',
  quality: 'standard',
  infill_density: 20,
  support: false,
  quantity: 1,
  post_process: 'none',
  rush: false,
})
const job = ref(null)
const preview = ref(null)
const previewLoading = ref(false)
let pollTimer = null

const stageLabel = computed(() => {
  const status = job.value?.status
  if (!status) return ''
  return t(`simpleQuote.print3dStage.${status}`, status)
})

const weightDisplay = computed(() => job.value?.result?.filament_weight_g ?? '—')
const hoursDisplay = computed(() => job.value?.result?.print_hours ?? '—')
const canQuote = computed(() => job.value?.status === 'done')

const fileToBase64 = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const buffer = reader.result
      const bytes = new Uint8Array(buffer)
      let binary = ''
      for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i])
      resolve(btoa(binary))
    }
    reader.onerror = () => reject(reader.error)
    reader.readAsArrayBuffer(file)
  })

const loadOptions = async () => {
  try {
    const res = await fetchPrint3dOptions()
    options.value = res.data || options.value
    form.value.infill_density = options.value.infill?.default ?? 20
    if (options.value.materials?.[0]) form.value.material = options.value.materials[0].key
    if (options.value.qualities?.[0]) form.value.quality = options.value.qualities[0].key
    if (options.value.post_processing?.[0]) {
      form.value.post_process = options.value.post_processing[0].key
    }
  } catch (e) {
    error.value = e.message || t('simpleQuote.print3dOptionsFailed')
  }
}

const stopPoll = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const refreshPreview = async () => {
  if (!canQuote.value || !job.value?.id) {
    preview.value = null
    return
  }
  previewLoading.value = true
  try {
    const res = await previewSimpleQuote({
      quote_type: 'print3d',
      inputs: {
        slice_job_id: job.value.id,
        material: form.value.material,
        quantity: form.value.quantity,
        post_process: form.value.post_process,
        rush: form.value.rush,
      },
    })
    preview.value = res.data
  } catch (e) {
    preview.value = null
    error.value = e.message || t('simpleQuote.previewFailed')
  } finally {
    previewLoading.value = false
  }
}

const pollJob = async (id) => {
  stopPoll()
  slicing.value = true
  const tick = async () => {
    try {
      const res = await fetchPrint3dSliceJob(id)
      job.value = res.data
      if (res.data.preview_mesh?.data) previewMesh.value = res.data.preview_mesh
      if (res.data.status === 'done') {
        stopPoll()
        slicing.value = false
        await refreshPreview()
      } else if (res.data.status === 'failed') {
        stopPoll()
        slicing.value = false
        error.value = res.data.error_message || t('simpleQuote.sliceFailed')
      }
    } catch (e) {
      stopPoll()
      slicing.value = false
      error.value = e.message || t('simpleQuote.sliceFailed')
    }
  }
  await tick()
  pollTimer = setInterval(tick, 2000)
}

const onFileSelected = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  error.value = ''
  job.value = null
  preview.value = null
  stopPoll()

  const name = (file.name || '').toLowerCase()
  parsing.value = true
  try {
    if (name.endsWith('.stl')) {
      const data = await fileToBase64(file)
      previewMesh.value = { format: 'stl', encoding: 'base64', data }
    } else if (name.endsWith('.stp') || name.endsWith('.step')) {
      const fd = new FormData()
      fd.append('file', file)
      const res = await stpParse(fd)
      previewMesh.value = res.data?.geometry?.preview_mesh || null
    } else {
      error.value = t('simpleQuote.print3dFileTypes')
      return
    }

    const fd = new FormData()
    fd.append('file', file)
    fd.append('material', form.value.material)
    fd.append('quality', form.value.quality)
    fd.append('infill_density', String(form.value.infill_density))
    fd.append('support', form.value.support ? 'true' : 'false')
    fd.append('quantity', String(form.value.quantity))
    fd.append('post_process', form.value.post_process)
    fd.append('rush', form.value.rush ? 'true' : 'false')
    const created = await createPrint3dSliceJob(fd)
    job.value = created.data
    await pollJob(created.data.id)
  } catch (e) {
    error.value = e.message || t('simpleQuote.sliceFailed')
  } finally {
    parsing.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

const onGenerate = async () => {
  if (!canQuote.value) return
  error.value = ''
  submitting.value = true
  try {
    const res = await createSimpleQuote({
      quote_type: 'print3d',
      product_name: productName.value,
      inputs: {
        slice_job_id: job.value.id,
        material: form.value.material,
        quality: form.value.quality,
        infill_density: form.value.infill_density,
        support: form.value.support,
        quantity: form.value.quantity,
        post_process: form.value.post_process,
        rush: form.value.rush,
      },
    })
    emit('generated', res.data)
    router.replace({ query: { id: res.data.id } })
  } catch (e) {
    error.value = e.message || t('simpleQuote.failed')
  } finally {
    submitting.value = false
  }
}

watch(
  () => [form.value.quantity, form.value.post_process, form.value.rush, form.value.material],
  () => {
    if (canQuote.value) refreshPreview()
  },
)

watch(
  () => props.savedResult,
  (val) => {
    if (val?.quote_type === 'print3d') preview.value = val.result
  },
  { immediate: true },
)

loadOptions()
onUnmounted(stopPoll)
</script>

<template>
  <div class="p3d-sheet">
    <aside class="p3d-left card">
      <StpViewer3d :preview-mesh="previewMesh" :loading="parsing || slicing" />
      <button
        type="button"
        class="btn btn-secondary"
        :disabled="parsing || slicing"
        @click="fileInput?.click()"
      >
        {{ parsing || slicing ? t('simpleQuote.parsing') : t('simpleQuote.uploadModel') }}
      </button>
      <input
        ref="fileInput"
        type="file"
        accept=".stl,.stp,.step"
        hidden
        @change="onFileSelected"
      />
      <p class="hint">{{ t('simpleQuote.print3dFileTypes') }}</p>
      <div v-if="job" class="stage">
        <span>{{ t('simpleQuote.sliceStatus') }}: {{ stageLabel }}</span>
        <span v-if="job.error_code" class="err">{{ job.error_message }}</span>
      </div>
    </aside>

    <section class="p3d-form card">
      <label>{{ t('simpleQuote.productName') }}<input v-model="productName" type="text" /></label>
      <label>{{ t('simpleQuote.material') }}
        <select v-model="form.material">
          <option v-for="m in options.materials" :key="m.key" :value="m.key">{{ m.name || m.key }}</option>
        </select>
      </label>
      <label>{{ t('simpleQuote.quality') }}
        <select v-model="form.quality">
          <option v-for="q in options.qualities" :key="q.key" :value="q.key">
            {{ q.name || q.key }}{{ q.layer_height ? ` (${q.layer_height}mm)` : '' }}
          </option>
        </select>
      </label>
      <label>{{ t('simpleQuote.infill') }}
        <input v-model.number="form.infill_density" type="number" min="5" max="100" />
      </label>
      <label class="check"><input v-model="form.support" type="checkbox" /> {{ t('simpleQuote.support') }}</label>
      <label>{{ t('simpleQuote.quantity') }}
        <input v-model.number="form.quantity" type="number" min="1" />
      </label>
      <label>{{ t('simpleQuote.postProcess') }}
        <select v-model="form.post_process">
          <option v-for="p in options.post_processing" :key="p.key" :value="p.key">{{ p.name || p.key }}</option>
        </select>
      </label>
      <label class="check"><input v-model="form.rush" type="checkbox" /> {{ t('simpleQuote.rush') }}</label>

      <div class="metrics">
        <div>{{ t('simpleQuote.weight') }}: <strong>{{ weightDisplay }}</strong> g</div>
        <div>{{ t('simpleQuote.printHours') }}: <strong>{{ hoursDisplay }}</strong> h</div>
        <p class="hint">{{ t('simpleQuote.sliceTrustedHint') }}</p>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
      <button
        type="button"
        class="btn btn-primary"
        :disabled="!canQuote || submitting"
        @click="onGenerate"
      >
        {{ submitting ? t('simpleQuote.generating') : t('simpleQuote.generate') }}
      </button>
    </section>

    <aside class="p3d-result card">
      <h3>{{ t('simpleQuote.result') }}</h3>
      <div v-if="previewLoading">{{ t('simpleQuote.previewing') }}</div>
      <template v-else-if="preview || savedResult?.result">
        <p class="total">
          {{ t('simpleQuote.total') }}:
          <template v-if="savedResult">
            {{ fromQuote(savedResult.total_amount ?? savedResult.result?.total, savedResult) }}
          </template>
          <template v-else>
            {{ fromPreview(preview?.total, { currency: 'KRW', ...preview }) }}
          </template>
          <small>({{ displayCurrency }})</small>
        </p>
        <p>{{ t('simpleQuote.unitPrice') }}: {{ (preview || savedResult?.result)?.unit_price }}</p>
        <ul>
          <li v-for="(row, i) in (preview || savedResult?.result)?.breakdown || []" :key="i">
            {{ row.label }}: {{ row.amount }}
          </li>
        </ul>
        <button
          v-if="savedResult?.id"
          type="button"
          class="btn btn-secondary"
          @click="emit('convert')"
        >
          {{ t('simpleQuote.convert') }}
        </button>
      </template>
      <p v-else class="hint">{{ t('simpleQuote.print3dResultHint') }}</p>
    </aside>
  </div>
</template>

<style scoped lang="scss">
.p3d-sheet {
  display: grid;
  /* 默认两列：预览 | 参数，保证「打印机」等字段首屏可见 */
  grid-template-columns: minmax(0, 1.15fr) minmax(280px, 0.95fr);
  gap: 1rem;
  align-items: start;
}
.p3d-result {
  grid-column: 1 / -1;
}
@media (min-width: 1100px) {
  .p3d-sheet {
    grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.95fr) minmax(240px, 0.85fr);
  }
  .p3d-result {
    grid-column: auto;
  }
}
@media (max-width: 720px) {
  .p3d-sheet {
    grid-template-columns: 1fr;
  }
  .p3d-result {
    grid-column: auto;
  }
}
.p3d-left,
.p3d-form,
.p3d-result {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-width: 0;
}
label {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-text-heading, #111);
}
label.check {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
  font-weight: 400;
}
.p3d-form input[type='text'],
.p3d-form input[type='number'],
.p3d-form select {
  width: 100%;
  box-sizing: border-box;
  min-height: 2.5rem;
  padding: 0.55rem 0.75rem;
  font-size: 0.9375rem;
  font-family: inherit;
  border: 1px solid var(--color-border-strong, #c5c9d0);
  border-radius: var(--radius-md, 8px);
  background: var(--color-bg, #fff);
  color: var(--color-text-heading, #111);
}
.p3d-form input:focus,
.p3d-form select:focus {
  outline: none;
  border-color: var(--color-steel, #3d5a80);
  box-shadow: 0 0 0 3px var(--color-steel-muted, rgba(61, 90, 128, 0.15));
}
.hint { color: var(--color-text-muted, #666); font-size: 0.85rem; margin: 0; }
.error, .err { color: #c0392b; }
.metrics { padding: 0.75rem; background: #f6f7f9; border-radius: 6px; }
.total { font-size: 1.1rem; font-weight: 600; }
.stage { font-size: 0.9rem; display: flex; flex-direction: column; gap: 0.25rem; }
</style>
