<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchQuoteParams, saveQuoteParam, updateQuoteParam } from '../api'
import {
  groupQuoteParams,
  resolveParamLabel,
  resolveParamUnit,
} from '../utils/quoteParamGroups'

const { t } = useI18n()
const router = useRouter()

const QUOTE_TYPES = [
  { value: 'injection', labelKey: 'quoteParams.typeInjection' },
  { value: 'print3d', labelKey: 'quoteParams.typePrint3d' },
  { value: 'pcba', labelKey: 'quoteParams.typePcba' },
  { value: 'pcb', labelKey: 'quoteParams.typePcb' },
  { value: 'software', labelKey: 'quoteParams.typeSoftware' },
  { value: 'ic', labelKey: 'quoteParams.typeIc' },
  { value: 'paper_box', labelKey: 'quoteParams.typePaperBox' },
  { value: 'shipping', labelKey: 'quoteParams.typeShipping' },
]

const activeType = ref('injection')
const items = ref([])
const originalValues = ref({})
const dirtyIds = ref(new Set())
const search = ref('')
const loading = ref(false)
const saving = ref(false)
const dialog = ref(false)
const emptyForm = () => ({
  quote_type: activeType.value,
  param_key: '',
  value: 0,
  label: '',
  unit: '',
  note: '',
})
const form = ref(emptyForm())

const typeLabel = (value) => {
  const found = QUOTE_TYPES.find((x) => x.value === value)
  return found ? t(found.labelKey) : value
}

const sameValue = (a, b) => Number(a) === Number(b)

const filteredItems = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return items.value
  return items.value.filter((row) => {
    const label = resolveParamLabel(row, activeType.value)
    const hay = [row.param_key, row.label, label, row.note].filter(Boolean).join(' ').toLowerCase()
    return hay.includes(q)
  })
})

const groupedParams = computed(() => groupQuoteParams(activeType.value, filteredItems.value))

const dirtyCount = computed(() => dirtyIds.value.size)

const markDirty = (row) => {
  const next = new Set(dirtyIds.value)
  if (sameValue(row.value, originalValues.value[row.id])) {
    next.delete(row.id)
  } else {
    next.add(row.id)
  }
  dirtyIds.value = next
}

const load = async () => {
  loading.value = true
  try {
    const res = await fetchQuoteParams({ quote_type: activeType.value })
    const list = res.data.items || []
    items.value = list
    const originals = {}
    list.forEach((row) => {
      originals[row.id] = row.value
    })
    originalValues.value = originals
    dirtyIds.value = new Set()
  } finally {
    loading.value = false
  }
}

watch(activeType, () => {
  search.value = ''
  load()
})

onMounted(load)

const openCreate = () => {
  form.value = emptyForm()
  dialog.value = true
}

const submit = async () => {
  if (!form.value.param_key?.trim()) {
    ElMessage.warning(t('common.paramKey'))
    return
  }
  form.value.quote_type = activeType.value
  await saveQuoteParam(form.value)
  ElMessage.success(t('common.success'))
  dialog.value = false
  await load()
}

const savePage = async () => {
  if (!dirtyCount.value) {
    ElMessage.info(t('quoteParams.noDirty'))
    return
  }
  saving.value = true
  const rows = items.value.filter((row) => dirtyIds.value.has(row.id))
  const results = await Promise.allSettled(
    rows.map((row) => updateQuoteParam(row.id, { value: row.value })),
  )
  saving.value = false

  let ok = 0
  let fail = 0
  results.forEach((r, i) => {
    if (r.status === 'fulfilled') {
      ok += 1
      const row = rows[i]
      originalValues.value[row.id] = row.value
    } else {
      fail += 1
    }
  })

  const next = new Set(dirtyIds.value)
  rows.forEach((row, i) => {
    if (results[i].status === 'fulfilled') next.delete(row.id)
  })
  dirtyIds.value = next
  originalValues.value = { ...originalValues.value }

  if (fail) {
    ElMessage.error(t('quoteParams.saveFailCount', { ok, fail }))
  } else {
    ElMessage.success(t('quoteParams.savedCount', { count: ok }))
  }
}

const goPrint3dConfig = () => {
  router.push({ name: 'print3d-config' })
}
</script>

<template>
  <div>
    <div class="toolbar">
      <div>
        <h2>{{ t('nav.quoteParams') }}</h2>
        <p class="page-hint">{{ t('quoteParams.pageHint') }}</p>
      </div>
      <div class="toolbar-actions">
        <el-button @click="openCreate">{{ t('quoteParams.createParam') }}</el-button>
        <el-button
          type="primary"
          :disabled="!dirtyCount"
          :loading="saving"
          @click="savePage"
        >
          {{ t('quoteParams.savePage') }}
          <span v-if="dirtyCount" class="dirty-badge">{{ dirtyCount }}</span>
        </el-button>
      </div>
    </div>

    <el-tabs v-model="activeType" class="type-tabs">
      <el-tab-pane
        v-for="opt in QUOTE_TYPES"
        :key="opt.value"
        :label="t(opt.labelKey)"
        :name="opt.value"
      />
    </el-tabs>

    <el-alert
      v-if="activeType === 'print3d'"
      type="info"
      show-icon
      :closable="false"
      class="print3d-guide"
    >
      <template #title>
        <div class="guide-row">
          <span>{{ t('quoteParams.print3dGuide') }}</span>
          <el-button type="primary" link @click="goPrint3dConfig">
            {{ t('quoteParams.print3dGuideAction') }}
          </el-button>
        </div>
      </template>
    </el-alert>

    <div class="filters">
      <el-input
        v-model="search"
        clearable
        :placeholder="t('quoteParams.searchPlaceholder')"
        style="width: 280px"
      />
      <span class="count">{{ filteredItems.length }} / {{ items.length }}</span>
      <span v-if="dirtyCount" class="save-hint">{{ t('quoteParams.savePageHint') }}</span>
    </div>

    <div v-loading="loading" class="groups">
      <el-empty v-if="!groupedParams.length" :description="t('quoteParams.empty')" />
      <el-card
        v-for="group in groupedParams"
        :key="group.id"
        shadow="never"
        class="group-card"
      >
        <template #header>
          <span class="group-title">{{ t(group.titleKey) }}</span>
          <span class="group-count">{{ group.items.length }}</span>
        </template>
        <div
          v-for="row in group.items"
          :key="row.id"
          class="param-row"
          :class="{ dirty: dirtyIds.has(row.id) }"
        >
          <div class="param-meta">
            <div class="param-label">{{ resolveParamLabel(row, activeType) }}</div>
            <div class="param-key">{{ row.param_key }}</div>
          </div>
          <div class="param-value">
            <el-input-number
              v-model="row.value"
              size="small"
              :controls="false"
              @change="markDirty(row)"
            />
            <span class="unit">{{ resolveParamUnit(row, activeType) }}</span>
          </div>
        </div>
      </el-card>
    </div>

    <el-dialog v-model="dialog" :title="t('quoteParams.createParam')" width="480px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item :label="t('common.quoteType')">
          <el-input :model-value="typeLabel(activeType)" disabled />
        </el-form-item>
        <el-form-item :label="t('common.paramKey')">
          <el-input v-model="form.param_key" />
        </el-form-item>
        <el-form-item :label="t('common.summary')">
          <el-input v-model="form.label" />
        </el-form-item>
        <el-form-item :label="t('common.value')">
          <el-input-number v-model="form.value" :controls="false" />
        </el-form-item>
        <el-form-item :label="t('quoteParams.unit')">
          <el-input v-model="form.unit" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submit">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 0.5rem;
}
.toolbar h2 { margin: 0; }
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}
.dirty-badge {
  margin-left: 0.35rem;
  font-variant-numeric: tabular-nums;
}
.page-hint {
  margin: 0.35rem 0 0;
  font-size: 0.85rem;
  color: #909399;
  max-width: 560px;
  line-height: 1.45;
}
.type-tabs { margin-bottom: 0.75rem; }
.print3d-guide { margin-bottom: 0.75rem; }
.guide-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1rem;
}
.filters {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}
.count { font-size: 0.85rem; color: #909399; }
.save-hint { font-size: 0.85rem; color: #e6a23c; }
.groups {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-height: 120px;
}
.group-card :deep(.el-card__header) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 10px 16px;
}
.group-title { font-weight: 600; }
.group-count {
  font-size: 0.8rem;
  color: #909399;
}
.param-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 0;
  border-bottom: 1px solid #f0f2f5;
}
.param-row:last-child { border-bottom: none; }
.param-row.dirty {
  background: #fdf6ec;
  margin: 0 -12px;
  padding-left: 12px;
  padding-right: 12px;
  border-radius: 4px;
}
.param-meta { min-width: 0; flex: 1; }
.param-label {
  font-size: 0.95rem;
  color: #303133;
  line-height: 1.35;
}
.param-key {
  margin-top: 0.15rem;
  font-size: 0.75rem;
  color: #c0c4cc;
  word-break: break-all;
}
.param-value {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}
.unit {
  min-width: 4.5rem;
  font-size: 0.8rem;
  color: #909399;
}
</style>
