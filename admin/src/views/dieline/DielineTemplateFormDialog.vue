<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  form: { type: Object, required: true },
  editingId: { type: [String, Number], default: null },
  submitting: { type: Boolean, default: false },
  categories: { type: Array, default: () => [] },
})

const emit = defineEmits(['submit'])

const dialogVisible = defineModel({ type: Boolean, default: false })

const { t } = useI18n()

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

const categoryOptions = computed(() =>
  props.categories.map((c) => ({
    value: c.id,
    label: `${c.code} · ${c.name_i18n?.zh || c.name_i18n?.en || c.code}`,
    code: c.code,
  })),
)

const onCategoryChange = (id) => {
  const cat = props.categories.find((c) => c.id === id)
  props.form.category_code = cat?.code || ''
}

const onProductionAsset = (e) => {
  props.form.production_asset = e.target.files?.[0] || null
}

const onThumbnail = (e) => {
  props.form.thumbnail = e.target.files?.[0] || null
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

const submit = () => emit('submit')
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
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

      <el-form-item :label="t('dielineTemplates.geometryMode')">
        <el-select v-model="form.geometry_mode" style="width: 100%">
          <el-option :label="t('dielineTemplates.geometryFormula')" value="formula" />
          <el-option :label="t('dielineTemplates.geometryFixed')" value="fixed_asset" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('dielineTemplates.pointsCost')">
        <el-input-number v-model="form.points_cost" :min="0" :controls="false" />
      </el-form-item>
      <el-form-item :label="t('dielineTemplates.sortOrder')">
        <el-input-number v-model="form.sort_order" :min="0" :controls="false" />
      </el-form-item>
      <el-form-item :label="t('dielineTemplates.purchaseEnabled')">
        <el-switch v-model="form.purchase_enabled" />
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
      <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">{{ t('common.save') }}</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
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

@media (max-width: 820px) {
  .dim-row {
    grid-template-columns: 1fr;
  }
}
</style>
