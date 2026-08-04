<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  fetchPrint3dConfig,
  previewPrint3dConfig,
  savePrint3dConfig,
} from '../api'

const { t } = useI18n()
const loading = ref(false)
const saving = ref(false)
const previewLoading = ref(false)
const preview = ref(null)
const paramMeta = ref({})

const form = reactive({
  params: {},
  materials: [],
  printers: [],
  qualities: [],
  post_processing: [],
})

const sample = reactive({
  material: 'PLA',
  printer: 'prusa_mk3s',
  quality: 'standard',
  infill_density: 20,
  quantity: 1,
  post_process: 'none',
  rush: false,
  model_weight_g: 30,
  print_hours: 4,
})

const load = async () => {
  loading.value = true
  try {
    const res = await fetchPrint3dConfig()
    const data = res.data || {}
    form.params = { ...(data.params || {}) }
    form.params.pricing_mode = Number(form.params.pricing_mode) || 0
    form.materials = data.materials || []
    form.printers = data.printers || []
    form.qualities = data.qualities || []
    form.post_processing = data.post_processing || []
    paramMeta.value = data.param_meta || {}
    if (form.materials[0]) sample.material = form.materials[0].key
    if (form.printers[0]) sample.printer = form.printers[0].key
    if (form.qualities[0]) sample.quality = form.qualities[0].key
  } catch (e) {
    ElMessage.error(e.message || t('common.failed'))
  } finally {
    loading.value = false
  }
}

const save = async () => {
  saving.value = true
  try {
    await savePrint3dConfig({
      params: form.params,
      materials: form.materials,
      printers: form.printers,
      qualities: form.qualities,
      post_processing: form.post_processing,
    })
    ElMessage.success(t('common.success'))
    await load()
  } catch (e) {
    ElMessage.error(e.message || t('common.failed'))
  } finally {
    saving.value = false
  }
}

const runPreview = async () => {
  previewLoading.value = true
  preview.value = null
  try {
    const res = await previewPrint3dConfig({ ...sample })
    preview.value = res.data
  } catch (e) {
    ElMessage.error(e.message || t('common.failed'))
  } finally {
    previewLoading.value = false
  }
}

const paramEntries = () => Object.keys(form.params || {})

const paramLabel = (key) => {
  const i18nKey = `print3dAdmin.paramLabels.${key}`
  const translated = t(i18nKey)
  if (translated && translated !== i18nKey) return translated
  return (paramMeta.value[key] && paramMeta.value[key][0]) || key
}

const paramUnit = (key) => (paramMeta.value[key] && paramMeta.value[key][1]) || ''

const BREAKDOWN_LABEL_MAP = {
  材料费: 'print3dAdmin.breakdown.material',
  电费: 'print3dAdmin.breakdown.electricity',
  设备折旧: 'print3dAdmin.breakdown.depreciation',
  '基础/其他': 'print3dAdmin.breakdown.baseOther',
  后处理费: 'print3dAdmin.breakdown.postProcess',
  设备使用费: 'print3dAdmin.breakdown.machine',
  加价后小计: 'print3dAdmin.breakdown.afterMarkup',
  税费: 'print3dAdmin.breakdown.tax',
}

const breakdownLabel = (label) => {
  const key = BREAKDOWN_LABEL_MAP[label]
  return key ? t(key) : label
}

// 默认打印机单选：开启某台时清除其他行的默认标记
const setDefaultPrinter = (row, value) => {
  if (!value) return
  form.printers.forEach((p) => {
    if (p !== row) p.is_default = false
  })
}

onMounted(load)
</script>

<template>
  <div v-loading="loading" class="p3d-admin">
    <div class="toolbar">
      <h2>{{ t('nav.print3dConfig') }}</h2>
      <el-button type="primary" :loading="saving" @click="save">{{ t('common.save') }}</el-button>
    </div>

    <el-card class="block" shadow="never">
      <template #header>{{ t('print3dAdmin.params') }}</template>
      <el-form label-width="200px">
        <el-form-item :label="t('print3dAdmin.pricingMode')">
          <el-select v-model="form.params.pricing_mode" style="width: 240px">
            <el-option :label="t('print3dAdmin.modeCustom')" :value="0" />
            <el-option :label="t('print3dAdmin.modePerGram')" :value="1" />
          </el-select>
        </el-form-item>
        <el-form-item
          v-for="key in paramEntries().filter((k) => k !== 'pricing_mode')"
          :key="key"
          :label="paramLabel(key)"
        >
          <el-input-number v-model="form.params[key]" :controls="false" style="width: 220px" />
          <span class="unit">{{ paramUnit(key) }}</span>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="block" shadow="never">
      <template #header>{{ t('print3dAdmin.materials') }}</template>
      <el-table :data="form.materials" size="small">
        <el-table-column prop="key" label="Key" width="100" />
        <el-table-column :label="t('common.name')" min-width="120">
          <template #default="{ row }"><el-input v-model="row.name" size="small" /></template>
        </el-table-column>
        <el-table-column label="g/cm³" width="100">
          <template #default="{ row }"><el-input-number v-model="row.density_g_cm3" size="small" :controls="false" /></template>
        </el-table-column>
        <el-table-column :label="t('print3dAdmin.pricePerKg')" width="120">
          <template #default="{ row }"><el-input-number v-model="row.price_per_kg" size="small" :controls="false" /></template>
        </el-table-column>
        <el-table-column :label="t('print3dAdmin.perGram')" width="110">
          <template #default="{ row }"><el-input-number v-model="row.per_gram_price" size="small" :controls="false" /></template>
        </el-table-column>
        <el-table-column :label="t('print3dAdmin.enabled')" width="80">
          <template #default="{ row }"><el-switch v-model="row.enabled" /></template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="block" shadow="never">
      <template #header>{{ t('print3dAdmin.printers') }}</template>
      <el-table :data="form.printers" size="small">
        <el-table-column prop="key" label="Key" width="140" />
        <el-table-column :label="t('common.name')" min-width="160">
          <template #default="{ row }"><el-input v-model="row.name" size="small" /></template>
        </el-table-column>
        <el-table-column :label="t('print3dAdmin.markup')" width="120">
          <template #default="{ row }"><el-input-number v-model="row.markup_multiplier" size="small" :step="0.05" :controls="false" /></template>
        </el-table-column>
        <el-table-column :label="t('print3dAdmin.defaultPrinter')" width="90">
          <template #default="{ row }">
            <el-switch v-model="row.is_default" @change="(val) => setDefaultPrinter(row, val)" />
          </template>
        </el-table-column>
        <el-table-column :label="t('print3dAdmin.enabled')" width="80">
          <template #default="{ row }"><el-switch v-model="row.enabled" /></template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="block" shadow="never">
      <template #header>{{ t('print3dAdmin.qualities') }}</template>
      <el-table :data="form.qualities" size="small">
        <el-table-column prop="key" label="Key" width="120" />
        <el-table-column :label="t('common.name')" min-width="140">
          <template #default="{ row }"><el-input v-model="row.name" size="small" /></template>
        </el-table-column>
        <el-table-column :label="t('print3dAdmin.layerHeight')" width="120">
          <template #default="{ row }"><el-input-number v-model="row.layer_height" size="small" :step="0.05" :controls="false" /></template>
        </el-table-column>
        <el-table-column :label="t('print3dAdmin.enabled')" width="80">
          <template #default="{ row }"><el-switch v-model="row.enabled" /></template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="block" shadow="never">
      <template #header>{{ t('print3dAdmin.postProcessing') }}</template>
      <el-table :data="form.post_processing" size="small">
        <el-table-column prop="key" label="Key" width="120" />
        <el-table-column :label="t('common.name')" min-width="140">
          <template #default="{ row }"><el-input v-model="row.name" size="small" /></template>
        </el-table-column>
        <el-table-column :label="t('common.value')" width="120">
          <template #default="{ row }"><el-input-number v-model="row.price" size="small" :controls="false" /></template>
        </el-table-column>
        <el-table-column :label="t('print3dAdmin.enabled')" width="80">
          <template #default="{ row }"><el-switch v-model="row.enabled" /></template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="block" shadow="never">
      <template #header>{{ t('print3dAdmin.samplePreview') }}</template>
      <el-form inline>
        <el-form-item :label="t('print3dAdmin.weight')">
          <el-input-number v-model="sample.model_weight_g" :min="0" />
        </el-form-item>
        <el-form-item :label="t('print3dAdmin.hours')">
          <el-input-number v-model="sample.print_hours" :min="0" :step="0.1" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="previewLoading" @click="runPreview">{{ t('print3dAdmin.runPreview') }}</el-button>
        </el-form-item>
      </el-form>
      <div v-if="preview" class="preview-box">
        <p>{{ t('print3dAdmin.unitPrice') }}: {{ preview.unit_price }} / {{ t('print3dAdmin.total') }}: {{ preview.total }}</p>
        <ul>
          <li v-for="(row, i) in preview.breakdown || []" :key="i">{{ breakdownLabel(row.label) }}: {{ row.amount }}</li>
        </ul>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.block { margin-bottom: 1rem; }
.unit { margin-left: 0.5rem; color: #888; }
.preview-box { margin-top: 0.5rem; padding: 0.75rem; background: #f7f8fa; border-radius: 6px; }
</style>
