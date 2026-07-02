<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import MultiLangInput from '../components/MultiLangInput.vue'
import { fetchCategories, saveCategory, updateCategory } from '../api'
import { emptyI18n, normalizeI18n } from '../utils/i18nField'

const { t } = useI18n()
const items = ref([])
const dialog = ref(false)
const editingId = ref(null)
const emptyForm = () => ({ name: emptyI18n(), slug: '', sort_order: 0, is_active: true })
const form = ref(emptyForm())

const load = async () => {
  const res = await fetchCategories()
  items.value = res.data.items || []
}
onMounted(load)

const openCreate = () => {
  editingId.value = null
  form.value = emptyForm()
  dialog.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.value = { name: normalizeI18n(row.name), slug: row.slug, sort_order: row.sort_order, is_active: row.is_active }
  dialog.value = true
}

const submit = async () => {
  if (editingId.value) await updateCategory(editingId.value, form.value)
  else await saveCategory(form.value)
  dialog.value = false
  await load()
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('categories.title') }}</h2>
      <el-button type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
    </div>
    <el-table :data="items">
      <el-table-column prop="slug" :label="t('common.slug')" />
      <el-table-column :label="t('common.name')">
        <template #default="{ row }">{{ row.name?.ko || row.name?.zh || row.name?.en }}</template>
      </el-table-column>
      <el-table-column prop="sort_order" :label="t('serviceCategories.sortOrder')" width="90" />
      <el-table-column :label="t('common.active')" width="90">
        <template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? t('common.active') : '—' }}</el-tag></template>
      </el-table-column>
      <el-table-column :label="t('common.actions')" width="100">
        <template #default="{ row }"><el-button size="small" @click="openEdit(row)">{{ t('common.edit') }}</el-button></template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="dialog" :title="editingId ? t('categories.editTitle') : t('categories.createTitle')" width="560px">
      <el-form label-width="100px">
        <el-form-item :label="t('common.slug')"><el-input v-model="form.slug" /></el-form-item>
        <el-form-item :label="t('common.name')"><MultiLangInput v-model="form.name" /></el-form-item>
        <el-form-item :label="t('serviceCategories.sortOrder')"><el-input-number v-model="form.sort_order" :min="0" /></el-form-item>
        <el-form-item :label="t('common.active')"><el-switch v-model="form.is_active" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialog = false">{{ t('common.cancel') }}</el-button><el-button type="primary" @click="submit">{{ t('common.save') }}</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>.toolbar { display: flex; justify-content: space-between; margin-bottom: 1rem; }</style>
