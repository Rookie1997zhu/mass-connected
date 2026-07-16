<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import http from '../api/http'
import {
  translateMemberProjectFile,
  translateSupplierProjectFile,
} from '../api'
import { toApiPath } from '../utils/downloadAuthedFile'

const props = defineProps({
  file: { type: Object, default: null },
  open: { type: Boolean, default: false },
  projectId: { type: [Number, String], default: null },
  role: { type: String, default: '' }, // 'member' | 'supplier'
})
const emit = defineEmits(['close'])

const { t, locale } = useI18n()
const MAX_ROWS = 200
const MAX_COLS = 50

const loading = ref(false)
const loadingHint = ref('')
const error = ref('')
const sheetNames = ref([])
const activeSheet = ref('')
const tableRows = ref([])
const objectUrl = ref('')
const previewKind = ref('')
let renderSheetFn = null

const translateLoading = ref(false)
const translateError = ref('')
const translatedText = ref('')
const translateTruncated = ref(false)
const translateMethod = ref('')

const title = computed(() => props.file?.file_name || t('filePreview.title'))

const showTranslatePanel = computed(() => {
  if (!props.projectId || !props.role) return false
  return Boolean(props.file?.is_translatable)
})

const reset = () => {
  loading.value = false
  loadingHint.value = ''
  error.value = ''
  sheetNames.value = []
  activeSheet.value = ''
  tableRows.value = []
  if (objectUrl.value) URL.revokeObjectURL(objectUrl.value)
  objectUrl.value = ''
  previewKind.value = ''
  renderSheetFn = null
  translateLoading.value = false
  translateError.value = ''
  translatedText.value = ''
  translateTruncated.value = false
  translateMethod.value = ''
}

const close = () => {
  reset()
  emit('close')
}

const fetchBlobFromUrl = async (fileUrl, timeout = 60000) => {
  const path = toApiPath(fileUrl)
  if (path.startsWith('/media/')) {
    const res = await fetch(path)
    if (!res.ok) throw new Error(`load failed: ${res.status}`)
    return res.blob()
  }
  const data = await http.get(path, { responseType: 'blob', timeout })
  return data instanceof Blob ? data : new Blob([data])
}

const fetchBlob = async () => fetchBlobFromUrl(props.file.file_url)

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
  if (!props.file?.file_url && !props.file?.preview_pdf_url) return
  reset()
  loading.value = true
  try {
    const ext = (props.file.file_ext || props.file.file_name?.split('.').pop() || '').toLowerCase()

    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) {
      const blob = await fetchBlob()
      previewKind.value = 'image'
      objectUrl.value = URL.createObjectURL(blob)
    } else if (props.file.preview_pdf_url) {
      if (props.file.preview_mode === 'pdf_convert') {
        loadingHint.value = t('filePreview.converting')
      }
      const blob = await fetchBlobFromUrl(props.file.preview_pdf_url, 90000)
      previewKind.value = 'pdf'
      objectUrl.value = URL.createObjectURL(blob)
    } else if (ext === 'pdf') {
      const blob = await fetchBlob()
      previewKind.value = 'pdf'
      objectUrl.value = URL.createObjectURL(blob)
    } else if (['xlsx', 'xls', 'csv'].includes(ext)) {
      const blob = await fetchBlob()
      previewKind.value = 'excel'
      await parseExcel(blob)
    } else {
      previewKind.value = 'unsupported'
      error.value = t('filePreview.unsupported')
    }
  } catch (e) {
    error.value = e.message || t('filePreview.convertFailed')
    previewKind.value = 'unsupported'
  } finally {
    loading.value = false
    loadingHint.value = ''
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

const onTranslateFile = async () => {
  if (!props.projectId || !props.file?.id) return
  translateLoading.value = true
  translateError.value = ''
  try {
    const payload = { target_lang: locale.value }
    const api =
      props.role === 'supplier' ? translateSupplierProjectFile : translateMemberProjectFile
    const res = await api(props.projectId, props.file.id, payload)
    translatedText.value = res.data?.translated_text || ''
    translateTruncated.value = Boolean(res.data?.truncated)
    translateMethod.value = res.data?.extraction_method || ''
    if (!translatedText.value) {
      translateError.value = t('aiTranslate.translateFailed')
    }
  } catch (e) {
    const code = e?.code || e?.response?.data?.code
    if (code === 'TRANSLATE_NOT_CONFIGURED') {
      translateError.value = t('aiTranslate.notConfigured')
    } else {
      translateError.value = e.message || t('aiTranslate.translateFailed')
    }
  } finally {
    translateLoading.value = false
  }
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
      <div class="preview-body">
        <p v-if="loading" class="page-empty">
          {{ loadingHint || t('common.loading') }}
        </p>
        <p v-else-if="error" class="page-message page-message--error">{{ error }}</p>
        <p v-else-if="previewKind === 'unsupported'" class="page-message">
          {{ t('filePreview.complexFormatHint') }}
        </p>
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

        <section v-if="showTranslatePanel && !loading" class="translate-panel">
          <p class="hint">{{ t('filePreview.translateFileHint') }}</p>
          <button
            type="button"
            class="btn btn-secondary btn-sm"
            :disabled="translateLoading"
            @click="onTranslateFile"
          >
            {{ translateLoading ? t('aiTranslate.translating') : t('filePreview.translateFile') }}
          </button>
          <p v-if="translateMethod === 'pdf_ocr'" class="hint warn">
            {{ t('filePreview.translateScannedHint') }}
          </p>
          <p v-if="translateTruncated" class="hint warn">
            {{ t('filePreview.translateTruncated') }}
          </p>
          <p v-if="translateError" class="translate-error">{{ translateError }}</p>
          <p v-if="translatedText" class="translate-result">{{ translatedText }}</p>
        </section>
      </div>
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
.preview-actions { display: flex; gap: 0.5rem; flex-shrink: 0; }
.preview-body {
  overflow: auto;
  flex: 1;
  min-height: 0;
}
.excel-wrap, .image-wrap, .pdf-wrap { padding: 0.75rem 1rem 1rem; }
.hint { font-size: 0.75rem; opacity: 0.65; margin: 0 0 0.5rem; }
.hint.warn { color: #b45309; opacity: 1; }
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
.table-scroll { overflow: auto; max-height: 50vh; }
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
.image-wrap img { max-width: 100%; max-height: 60vh; display: block; margin: 0 auto; }
.pdf-wrap iframe { width: 100%; height: 60vh; border: 0; }
.translate-panel {
  padding: 0.75rem 1rem 1rem;
  border-top: 1px solid var(--color-border);
}
.translate-result {
  margin: 0.5rem 0 0;
  font-size: 0.85rem;
  white-space: pre-wrap;
  max-height: 28vh;
  overflow: auto;
  padding: 0.5rem 0.65rem;
  background: var(--color-steel-muted, rgba(0, 0, 0, 0.04));
  border-radius: 4px;
}
.translate-error {
  margin: 0.35rem 0 0;
  font-size: 0.78rem;
  color: #b91c1c;
}
</style>
