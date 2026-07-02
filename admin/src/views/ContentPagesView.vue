<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import MultiLangInput from '../components/MultiLangInput.vue'
import RichTextI18n from '../components/RichTextI18n.vue'
import { CONTENT_PAGE_PRESETS } from '../constants/contentPagePresets'
import { fetchContentPages, saveContentPage, updateContentPage } from '../api'
import { emptyI18n, normalizeI18n } from '../utils/i18nField'

const { t } = useI18n()
const items = ref([])
const dialog = ref(false)
const editingId = ref(null)

const emptyForm = () => ({
  page_key: '',
  title: emptyI18n(),
  body: emptyI18n(),
})

const form = ref(emptyForm())

const presetOptions = computed(() =>
  CONTENT_PAGE_PRESETS.map((item) => ({
    value: item.key,
    label: t(item.labelKey),
  }))
)

const presetLabel = (pageKey) => {
  const preset = CONTENT_PAGE_PRESETS.find((item) => item.key === pageKey)
  return preset ? t(preset.labelKey) : pageKey
}

const load = async () => {
  const res = await fetchContentPages()
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
    page_key: row.page_key,
    title: normalizeI18n(row.title),
    body: normalizeI18n(row.body),
  }
  dialog.value = true
}

const submit = async () => {
  if (editingId.value) await updateContentPage(editingId.value, form.value)
  else await saveContentPage(form.value)
  dialog.value = false
  await load()
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('pages.title') }}</h2>
      <el-button type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
    </div>
    <el-table :data="items">
      <el-table-column prop="page_key" :label="t('common.key')">
        <template #default="{ row }">{{ presetLabel(row.page_key) }}</template>
      </el-table-column>
      <el-table-column :label="t('common.title')"><template #default="{ row }">{{ row.title?.ko }}</template></el-table-column>
      <el-table-column :label="t('common.actions')">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog
      v-model="dialog"
      :title="editingId ? t('pages.editTitle') : t('pages.createTitle')"
      width="860px"
      destroy-on-close
    >
      <el-form label-width="120px">
        <el-form-item :label="t('common.pageKey')">
          <el-select
            v-model="form.page_key"
            :placeholder="t('common.selectPageKey')"
            :disabled="Boolean(editingId)"
            style="width: 100%"
          >
            <el-option
              v-for="item in presetOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
          <p class="help-text">{{ t('pages.pageKeyHelp') }}</p>
        </el-form-item>
        <el-form-item :label="t('common.title')">
          <MultiLangInput v-model="form.title" />
        </el-form-item>
        <el-form-item :label="t('common.body')">
          <RichTextI18n v-model="form.body" />
        </el-form-item>
      </el-form>
      <template #footer><el-button type="primary" @click="submit">{{ t('common.save') }}</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.help-text { margin: 8px 0 0; font-size: 12px; color: #909399; line-height: 1.5; }
</style>
