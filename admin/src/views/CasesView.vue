<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessageBox } from 'element-plus'
import MultiLangInput from '../components/MultiLangInput.vue'
import RichTextI18n from '../components/RichTextI18n.vue'
import { deleteCase, fetchCases, saveCase, updateCase } from '../api'
import { emptyI18n, normalizeI18n } from '../utils/i18nField'

const { t } = useI18n()
const items = ref([])
const dialog = ref(false)
const editingId = ref(null)

const emptyForm = () => ({
  title: emptyI18n(),
  summary: emptyI18n(),
  content: emptyI18n(),
  is_published: true,
})

const form = ref(emptyForm())

const load = async () => {
  const res = await fetchCases()
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
  form.value = {
    title: normalizeI18n(row.title),
    summary: normalizeI18n(row.summary),
    content: normalizeI18n(row.content),
    is_published: row.is_published,
  }
  dialog.value = true
}

const submit = async () => {
  if (editingId.value) await updateCase(editingId.value, form.value)
  else await saveCase(form.value)
  dialog.value = false
  await load()
}

const remove = async (row) => {
  await ElMessageBox.confirm(t('common.deleteConfirm'), t('common.delete'), {
    type: 'warning',
    confirmButtonText: t('common.delete'),
    cancelButtonText: t('common.cancel'),
  })
  await deleteCase(row.id)
  await load()
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('cases.title') }}</h2>
      <el-button type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
    </div>
    <el-table :data="items">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column :label="t('common.title')"><template #default="{ row }">{{ row.title?.ko }}</template></el-table-column>
      <el-table-column prop="is_published" :label="t('common.published')" />
      <el-table-column :label="t('common.actions')" width="180">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
          <el-button size="small" type="danger" @click="remove(row)">{{ t('common.delete') }}</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog
      v-model="dialog"
      :title="editingId ? t('cases.editTitle') : t('cases.createTitle')"
      width="860px"
      destroy-on-close
    >
      <el-form label-width="100px">
        <el-form-item :label="t('common.title')">
          <MultiLangInput v-model="form.title" />
        </el-form-item>
        <el-form-item :label="t('common.summary')">
          <MultiLangInput v-model="form.summary" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item :label="t('common.content')">
          <RichTextI18n v-model="form.content" />
        </el-form-item>
        <el-form-item :label="t('common.published')"><el-switch v-model="form.is_published" /></el-form-item>
      </el-form>
      <template #footer><el-button type="primary" @click="submit">{{ t('common.save') }}</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }</style>
