<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  addSupplierAttachment,
  addSupplierTag,
  createSupplier,
  deleteSupplierAttachment,
  deleteSupplierTag,
  fetchSupplier,
  fetchSuppliers,
  updateSupplier,
} from '../api'

const { t } = useI18n()
const items = ref([])
const dialog = ref(false)
const editDialog = ref(false)
const editForm = ref({})
const newTag = ref('')
const emptyForm = () => ({ company_name: '', email: '', password: '', name: '', region: '', contact_phone: '' })
const form = ref(emptyForm())

const load = async () => {
  const res = await fetchSuppliers()
  items.value = res.data.items || []
}
onMounted(load)

const openCreate = () => {
  form.value = emptyForm()
  dialog.value = true
}

const openEdit = async (row) => {
  const res = await fetchSupplier(row.id)
  editForm.value = { ...res.data }
  newTag.value = ''
  editDialog.value = true
}

const submit = async () => {
  if (!form.value.company_name || !form.value.email || !form.value.password) {
    ElMessage.warning(t('common.createSupplier'))
    return
  }
  try {
    await createSupplier(form.value)
    ElMessage.success(t('common.success'))
    dialog.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message || 'error')
  }
}

const saveEdit = async () => {
  try {
    const { payment_terms: _ignored, ...payload } = editForm.value
    await updateSupplier(editForm.value.id, payload)
    ElMessage.success(t('common.success'))
    editDialog.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message || 'error')
  }
}

const onAddTag = async () => {
  if (!newTag.value.trim()) return
  await addSupplierTag(editForm.value.id, { tag_name: newTag.value.trim() })
  const res = await fetchSupplier(editForm.value.id)
  editForm.value = res.data
  newTag.value = ''
}

const onRemoveTag = async (tag) => {
  await deleteSupplierTag(editForm.value.id, { tag_id: tag.id })
  const res = await fetchSupplier(editForm.value.id)
  editForm.value = res.data
}

const attachPublic = ref(true)
const attachCategory = ref('company_profile')

const onUploadAttachment = async (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  const fd = new FormData()
  fd.append('file', file)
  fd.append('category', attachCategory.value)
  fd.append('is_public', attachPublic.value ? 'true' : 'false')
  await addSupplierAttachment(editForm.value.id, fd)
  const res = await fetchSupplier(editForm.value.id)
  editForm.value = res.data
  e.target.value = ''
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('nav.suppliers') }}</h2>
      <el-button type="primary" @click="openCreate">{{ t('common.createSupplier') }}</el-button>
    </div>
    <el-table :data="items">
      <el-table-column prop="company_name" :label="t('common.companyName')" />
      <el-table-column prop="email" :label="t('common.email')" />
      <el-table-column prop="region" :label="t('common.region')" width="120" />
      <el-table-column prop="score" :label="t('suppliers.score')" width="80" />
      <el-table-column prop="status" :label="t('common.status')" width="120" />
      <el-table-column :label="t('common.actions')" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="t('common.createSupplier')" width="480px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item :label="t('common.companyName')"><el-input v-model="form.company_name" /></el-form-item>
        <el-form-item :label="t('common.email')"><el-input v-model="form.email" /></el-form-item>
        <el-form-item :label="t('common.password')"><el-input v-model="form.password" type="password" show-password /></el-form-item>
        <el-form-item :label="t('common.name')"><el-input v-model="form.name" /></el-form-item>
        <el-form-item :label="t('common.region')"><el-input v-model="form.region" /></el-form-item>
        <el-form-item :label="t('common.phone')"><el-input v-model="form.contact_phone" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submit">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialog" :title="t('suppliers.editTitle')" width="640px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item :label="t('common.companyName')"><el-input v-model="editForm.company_name" /></el-form-item>
        <el-form-item :label="t('suppliers.shortName')"><el-input v-model="editForm.short_name" /></el-form-item>
        <el-form-item :label="t('common.region')"><el-input v-model="editForm.region" /></el-form-item>
        <el-form-item :label="t('suppliers.country')"><el-input v-model="editForm.country" /></el-form-item>
        <el-form-item :label="t('suppliers.city')"><el-input v-model="editForm.city" /></el-form-item>
        <el-form-item :label="t('suppliers.establishedYear')"><el-input-number v-model="editForm.established_year" :min="1900" :max="2100" /></el-form-item>
        <el-form-item :label="t('suppliers.employeeScale')"><el-input v-model="editForm.employee_scale" /></el-form-item>
        <el-form-item :label="t('suppliers.factoryArea')"><el-input-number v-model="editForm.factory_area_sqm" :min="0" /></el-form-item>
        <el-form-item :label="t('suppliers.mainProducts')"><el-input v-model="editForm.main_products" type="textarea" rows="2" /></el-form-item>
        <el-form-item :label="t('suppliers.monthlyCapacity')"><el-input v-model="editForm.monthly_capacity" /></el-form-item>
        <el-form-item :label="t('suppliers.certifications')"><el-input v-model="editForm.quality_certifications" type="textarea" rows="2" /></el-form-item>
        <el-form-item :label="t('suppliers.equipment')"><el-input v-model="editForm.equipment_summary" type="textarea" rows="2" /></el-form-item>
        <el-form-item :label="t('common.status')">
          <el-select v-model="editForm.status" style="width: 100%">
            <el-option value="approved" label="approved" />
            <el-option value="pending" label="pending" />
            <el-option value="suspended" label="suspended" />
            <el-option value="blacklist" label="blacklist" />
            <el-option value="observing" label="observing" />
            <el-option value="priority" label="priority" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('suppliers.score')"><el-input-number v-model="editForm.score" :min="0" :max="5" /></el-form-item>
        <el-form-item :label="t('suppliers.adminNote')"><el-input v-model="editForm.admin_note" type="textarea" rows="2" /></el-form-item>
        <el-form-item :label="t('suppliers.tags')">
          <div class="tag-row">
            <el-tag v-for="tag in editForm.tags || []" :key="tag.id" closable @close="onRemoveTag(tag)">{{ tag.tag_name }}</el-tag>
            <el-input v-model="newTag" size="small" style="width: 140px" @keyup.enter="onAddTag" />
            <el-button size="small" @click="onAddTag">{{ t('common.create') }}</el-button>
          </div>
        </el-form-item>
        <el-form-item :label="t('suppliers.attachments')">
          <div class="att-upload">
            <el-select v-model="attachCategory" style="width: 160px">
              <el-option value="company_profile" :label="t('suppliers.catCompanyProfile')" />
              <el-option value="certification" :label="t('suppliers.catCertification')" />
              <el-option value="equipment" :label="t('suppliers.catEquipment')" />
              <el-option value="case" :label="t('suppliers.catCase')" />
              <el-option value="qualification" :label="t('suppliers.catQualification')" />
            </el-select>
            <el-switch v-model="attachPublic" :active-text="t('suppliers.public')" />
            <input type="file" @change="onUploadAttachment" />
          </div>
          <ul class="att-list">
            <li v-for="a in editForm.attachments || []" :key="a.id">
              <a :href="a.file_url" target="_blank" rel="noopener">{{ a.file_name }}</a>
              <span class="att-meta">{{ a.category }} · {{ a.is_public ? t('suppliers.public') : t('suppliers.private') }}</span>
            </li>
          </ul>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveEdit">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.tag-row { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
.att-list { margin: 0.5rem 0 0; padding-left: 1rem; }
.att-upload { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
.att-meta { margin-left: 0.5rem; opacity: 0.65; font-size: 0.85rem; }
</style>
