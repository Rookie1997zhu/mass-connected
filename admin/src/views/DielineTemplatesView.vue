<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  deleteDielineCategory,
  deleteDielineTemplate,
  fetchDielineCategories,
  fetchDielineTemplates,
  saveDielineCategory,
  saveDielineTemplate,
  updateDielineCategory,
  updateDielineTemplate,
} from '../api'
import DielineListSection from './dieline/DielineListSection.vue'
import DielineTemplateFormDialog from './dieline/DielineTemplateFormDialog.vue'
import DielineAssetWorkbenchDialog from './dieline/DielineAssetWorkbenchDialog.vue'

const { t } = useI18n()
const items = ref([])
const categories = ref([])
const dialog = ref(false)
const categoryDialog = ref(false)
const assetDialog = ref(false)
const submitting = ref(false)
const categorySubmitting = ref(false)
const editingId = ref(null)
const editingCategoryId = ref(null)
const assetTemplate = ref(null)

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
  geometry_mode: 'formula',
  points_cost: 0,
  purchase_enabled: false,
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
    geometry_mode: row.geometry_mode || 'formula',
    points_cost: Number(row.points_cost) || 0,
    purchase_enabled: row.purchase_enabled ?? row.quote_enabled,
    preview_enabled: row.preview_enabled,
    sort_order: row.sort_order,
    is_active: row.is_active,
    thumbnail: null,
    production_asset: null,
    production_asset_url: row.production_asset_url || null,
  }
  dialog.value = true
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
  fd.append('geometry_mode', f.geometry_mode || 'formula')
  fd.append('points_cost', String(Number(f.points_cost) || 0))
  fd.append('purchase_enabled', f.purchase_enabled ? 'true' : 'false')
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

const openAssets = (row) => {
  assetTemplate.value = row
  assetDialog.value = true
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
</script>

<template>
  <div>
    <DielineListSection
      :categories="categories"
      :items="items"
      @create-category="openCategoryCreate"
      @edit-category="openCategoryEdit"
      @delete-category="removeCategory"
      @create-template="openCreate"
      @edit-template="openEdit"
      @open-assets="openAssets"
      @delete-template="remove"
    />

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

    <DielineTemplateFormDialog
      v-model="dialog"
      :form="form"
      :editing-id="editingId"
      :submitting="submitting"
      :categories="categories"
      @submit="submit"
    />

    <DielineAssetWorkbenchDialog
      v-model="assetDialog"
      :template="assetTemplate"
      @activated="load"
    />
  </div>
</template>
