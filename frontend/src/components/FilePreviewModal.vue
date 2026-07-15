<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import http from '../api/http'
import { toApiPath } from '../utils/downloadAuthedFile'

const props = defineProps({
  file: { type: Object, default: null },
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const { t } = useI18n()
const MAX_ROWS = 200
const MAX_COLS = 50

const loading = ref(false)
const error = ref('')
const sheetNames = ref([])
const activeSheet = ref('')
const tableRows = ref([])
const objectUrl = ref('')
const previewKind = ref('')
let renderSheetFn = null

const title = computed(() => props.file?.file_name || t('filePreview.title'))

const reset = () => {
  loading.value = false
  error.value = ''
  sheetNames.value = []
  activeSheet.value = ''
  tableRows.value = []
  if (objectUrl.value) URL.revokeObjectURL(objectUrl.value)
  objectUrl.value = ''
  previewKind.value = ''
  renderSheetFn = null
}

const close = () => {
  reset()
  emit('close')
}

const fetchBlob = async () => {
  const path = toApiPath(props.file.file_url)
  if (path.startsWith('/media/')) {
    const res = await fetch(path)
    if (!res.ok) throw new Error(`load failed: ${res.status}`)
    return res.blob()
  }
  const data = await http.get(path, { responseType: 'blob' })
  return data instanceof Blob ? data : new Blob([data])
}

const parseExcel = async (blob) => {
  const XLSX = await import('xlsx')
  const buf = await blob.arrayBuffer()
  const workbook = XLSX.read(buf, { type: 'array' })
  sheetNames.value = workbook.SheetNames || []
  activeSheet.value = sheetNames.value[0] || ''
  renderSheetFn = (name) => {
    const sheet = workbook.Sheets[name]
    if (!sheet) {
      tableRows.value = []
      return
    }
    const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '', blankrows: false })
    tableRows.value = rows.slice(0, MAX_ROWS).map((row) => {
      const arr = Array.isArray(row) ? row : []
      return arr.slice(0, MAX_COLS).map((cell) => String(cell ?? ''))
    })
  }
  renderSheetFn(activeSheet.value)
}

const onSheetChange = (name) => {
  activeSheet.value = name
  if (renderSheetFn) renderSheetFn(name)
}

const load = async () => {
  if (!props.file?.file_url) return
  reset()
  loading.value = true
  try {
    const ext = (props.file.file_ext || props.file.file_name?.split('.').pop() || '').toLowerCase()
    const blob = await fetchBlob()
    if (['xlsx', 'xls', 'csv'].includes(ext)) {
      previewKind.value = 'excel'
      await parseExcel(blob)
    } else if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) {
      previewKind.value = 'image'
      objectUrl.value = URL.createObjectURL(blob)
    } else if (ext === 'pdf') {
      previewKind.value = 'pdf'
      objectUrl.value = URL.createObjectURL(blob)
    } else {
      previewKind.value = 'unsupported'
      error.value = t('filePreview.unsupported')
    }
  } catch (e) {
    error.value = e.message || t('filePreview.loadFailed')
    previewKind.value = 'unsupported'
  } finally {
    loading.value = false
  }
}

const downloadOriginal = async () => {
  if (!props.file?.file_url) return
  const blob = await fetchBlob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = props.file.file_name || 'file'
  a.click()
  URL.revokeObjectURL(url)
}

watch(
  () => [props.open, props.file?.id],
  ([isOpen]) => {
    if (isOpen && props.file) load()
    else if (!isOpen) reset()
  },
)
</script>

<template>
  <div v-if="open" class="preview-overlay" @click.self="close">
    <div class="preview-dialog" role="dialog" aria-modal="true">
      <header class="preview-head">
        <h3>{{ title }}</h3>
        <div class="preview-actions">
          <button type="button" class="btn btn-secondary btn-sm" @click="downloadOriginal">
            {{ t('filePreview.download') }}
          </button>
          <button type="button" class="btn btn-secondary btn-sm" @click="close">
            {{ t('common.close') }}
          </button>
        </div>
      </header>
      <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
      <p v-else-if="error" class="page-message page-message--error">{{ error }}</p>
      <template v-else>
        <div v-if="previewKind === 'excel'" class="excel-wrap">
          <p class="hint">{{ t('filePreview.excelHint', { rows: MAX_ROWS, cols: MAX_COLS }) }}</p>
          <div v-if="sheetNames.length > 1" class="sheet-tabs">
            <button
              v-for="name in sheetNames"
              :key="name"
              type="button"
              class="sheet-tab"
              :class="{ active: name === activeSheet }"
              @click="onSheetChange(name)"
            >
              {{ name }}
            </button>
          </div>
          <div class="table-scroll">
            <table v-if="tableRows.length" class="preview-table">
              <tbody>
                <tr v-for="(row, ri) in tableRows" :key="ri">
                  <td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="page-empty">—</p>
          </div>
        </div>
        <div v-else-if="previewKind === 'image'" class="image-wrap">
          <img :src="objectUrl" :alt="title" />
        </div>
        <div v-else-if="previewKind === 'pdf'" class="pdf-wrap">
          <iframe :src="objectUrl" title="pdf" />
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped lang="scss">
.preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}
.preview-dialog {
  background: var(--color-surface, #fff);
  border-radius: var(--radius-md, 8px);
  width: min(960px, 100%);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.preview-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--color-border);
  h3 { margin: 0; font-size: 1rem; }
}
.preview-actions { display: flex; gap: 0.5rem; }
.excel-wrap, .image-wrap, .pdf-wrap { padding: 0.75rem 1rem 1rem; overflow: auto; }
.hint { font-size: 0.75rem; opacity: 0.65; margin: 0 0 0.5rem; }
.sheet-tabs { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0.75rem; }
.sheet-tab {
  border: 1px solid var(--color-border);
  background: transparent;
  border-radius: 999px;
  padding: 0.2rem 0.65rem;
  font-size: 0.8rem;
  cursor: pointer;
  &.active { border-color: var(--color-steel); color: var(--color-steel); }
}
.table-scroll { overflow: auto; max-height: 60vh; }
.preview-table {
  border-collapse: collapse;
  font-size: 0.8rem;
  td {
    border: 1px solid var(--color-border);
    padding: 0.25rem 0.5rem;
    white-space: nowrap;
    max-width: 240px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}
.image-wrap img { max-width: 100%; max-height: 70vh; display: block; margin: 0 auto; }
.pdf-wrap iframe { width: 100%; height: 70vh; border: 0; }
</style>
