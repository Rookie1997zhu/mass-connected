<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { fetchDownloads, saveDownload } from '../api'

const { t } = useI18n()
const items = ref([])
const dialog = ref(false)
const submitting = ref(false)
const form = ref({
  title: { ko: '', en: '', zh: '' },
  file_type: 'pdf',
  locale: 'ko',
  sort_order: 0,
  is_active: true,
  file: null,
})

const load = async () => {
  const res = await fetchDownloads()
  items.value = res.data.items || []
}
onMounted(load)

const openCreate = () => {
  form.value = {
    title: { ko: '', en: '', zh: '' },
    file_type: 'pdf',
    locale: 'ko',
    sort_order: 0,
    is_active: true,
    file: null,
  }
  dialog.value = true
}

const onFile = (e) => {
  form.value.file = e.target.files?.[0] || null
}

const submit = async () => {
  if (!form.value.title.ko?.trim()) {
    ElMessage.warning(t('downloads.titleRequired'))
    return
  }
  if (!form.value.file) {
    ElMessage.warning(t('downloads.fileRequired'))
    return
  }
  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('title', JSON.stringify(form.value.title))
    fd.append('file', form.value.file)
    fd.append('file_type', form.value.file_type)
    fd.append('locale', form.value.locale)
    fd.append('sort_order', String(form.value.sort_order))
    fd.append('is_active', form.value.is_active ? 'true' : 'false')
    await saveDownload(fd)
    ElMessage.success(t('common.success'))
    dialog.value = false
    await load()
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('downloads.title') }}</h2>
      <el-button type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
    </div>
    <el-table :data="items">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column :label="t('common.title')">
        <template #default="{ row }">{{ row.title?.ko || row.title?.en || '—' }}</template>
      </el-table-column>
      <el-table-column prop="file_type" :label="t('downloads.fileType')" width="100" />
      <el-table-column prop="locale" label="Locale" width="80" />
      <el-table-column prop="sort_order" :label="t('navigation.sortOrder')" width="90" />
      <el-table-column prop="is_active" :label="t('common.active')" width="80" />
      <el-table-column :label="t('common.download')" width="120">
        <template #default="{ row }">
          <a v-if="row.url" :href="row.url" target="_blank" rel="noopener">{{ t('common.download') }}</a>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="t('downloads.createTitle')" width="520px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item :label="t('common.titleKo')">
          <el-input v-model="form.title.ko" />
        </el-form-item>
        <el-form-item :label="t('downloads.fileType')">
          <el-select v-model="form.file_type" style="width: 100%">
            <el-option value="pdf" label="PDF" />
            <el-option value="doc" label="DOC" />
            <el-option value="other" label="Other" />
          </el-select>
        </el-form-item>
        <el-form-item label="Locale">
          <el-select v-model="form.locale" style="width: 100%">
            <el-option value="ko" label="ko" />
            <el-option value="zh" label="zh" />
            <el-option value="en" label="en" />
            <el-option value="ja" label="ja" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('navigation.sortOrder')">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
        <el-form-item :label="t('common.active')">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        <el-form-item :label="t('downloads.file')">
          <input type="file" @change="onFile" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
</style>
