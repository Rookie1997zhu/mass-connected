<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  files: { type: Array, default: () => [] },
  stages: { type: Array, default: () => [] },
  currentStageId: { type: [Number, String], default: null },
  role: { type: String, required: true },
  deletingFileId: { type: [Number, String], default: null },
})

const emit = defineEmits(['preview', 'delete'])

const { t, te } = useI18n()

const trOr = (key, fallback) => (te(key) ? t(key) : fallback)
const stageLabel = (name) => trOr(`workflow.stageNames.${name}`, name)
const fileCategoryLabel = (v) => trOr(`fileCategory.${v}`, v)

const filesByStage = computed(() => {
  const map = {}
  for (const f of props.files || []) {
    const key = f.stage_id || 'none'
    if (!map[key]) map[key] = []
    map[key].push(f)
  }
  return map
})

const unassignedFiles = computed(() => filesByStage.value.none || [])

const isStageOpen = (stageId, stageFiles) => {
  if (stageId === props.currentStageId) return true
  return (stageFiles || []).length > 0
}

const onPreview = (file) => emit('preview', file)
const onDelete = (fileId) => emit('delete', fileId)
</script>

<template>
  <div class="file-center">
    <details
      v-for="s in stages"
      :key="'files-' + s.id"
      class="file-stage"
      :open="isStageOpen(s.id, filesByStage[s.id])"
    >
      <summary class="file-stage__summary">
        <span class="file-stage__name">{{ stageLabel(s.name) }}</span>
        <span class="file-stage__count">{{ (filesByStage[s.id] || []).length }}</span>
      </summary>
      <p v-if="!(filesByStage[s.id] || []).length" class="page-empty file-stage__empty">—</p>
      <ul v-else class="file-list">
        <li v-for="f in filesByStage[s.id]" :key="f.id">
          <span class="file-name">{{ f.file_name }}</span>
          <span class="file-meta">{{ fileCategoryLabel(f.file_category) }}</span>
          <div class="file-actions">
            <button
              v-if="f.is_previewable"
              type="button"
              class="btn btn-secondary btn-sm"
              @click="onPreview(f)"
            >
              {{ t('filePreview.preview') }}
            </button>
            <button
              v-if="role === 'supplier'"
              type="button"
              class="btn btn-secondary btn-sm"
              :disabled="deletingFileId === f.id"
              @click="onDelete(f.id)"
            >
              {{ t('supplierProject.removeFile') }}
            </button>
          </div>
        </li>
      </ul>
    </details>

    <details
      v-if="unassignedFiles.length"
      class="file-stage"
      open
    >
      <summary class="file-stage__summary">
        <span class="file-stage__name">{{ t('workflow.unassignedFiles') }}</span>
        <span class="file-stage__count">{{ unassignedFiles.length }}</span>
      </summary>
      <ul class="file-list">
        <li v-for="f in unassignedFiles" :key="f.id">
          <span class="file-name">{{ f.file_name }}</span>
          <span class="file-meta">{{ fileCategoryLabel(f.file_category) }}</span>
          <div class="file-actions">
            <button
              v-if="f.is_previewable"
              type="button"
              class="btn btn-secondary btn-sm"
              @click="onPreview(f)"
            >
              {{ t('filePreview.preview') }}
            </button>
            <button
              v-if="role === 'supplier'"
              type="button"
              class="btn btn-secondary btn-sm"
              :disabled="deletingFileId === f.id"
              @click="onDelete(f.id)"
            >
              {{ t('supplierProject.removeFile') }}
            </button>
          </div>
        </li>
      </ul>
    </details>

    <p
      v-if="!files?.length && !stages?.length"
      class="page-empty"
    >
      {{ t('mypage.empty') }}
    </p>
  </div>
</template>

<style scoped lang="scss">
.file-center {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.file-stage {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  overflow: hidden;

  &[open] .file-stage__summary {
    border-bottom: 1px solid var(--color-border);
  }
}

.file-stage__summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  padding: 0.55rem 0.75rem;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
  list-style: none;

  &::-webkit-details-marker {
    display: none;
  }

  &::before {
    content: '▸';
    margin-right: 0.35rem;
    font-size: 0.7rem;
    opacity: 0.55;
    transition: transform 0.15s ease;
  }
}

.file-stage[open] .file-stage__summary::before {
  transform: rotate(90deg);
}

.file-stage__name {
  flex: 1;
}

.file-stage__count {
  font-size: 0.68rem;
  opacity: 0.55;
  font-weight: 500;
}

.file-stage__empty {
  margin: 0;
  padding: 0.5rem 0.75rem;
  font-size: 0.85rem;
}

.file-list {
  list-style: none;
  padding: 0;
  margin: 0;

  li {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem 0.75rem;
    padding: 0.55rem 0.75rem;
    border-bottom: 1px solid var(--color-border);
    font-size: 0.85rem;

    &:last-child {
      border-bottom: none;
    }
  }
}

.file-name {
  flex: 1 1 100%;
  word-break: break-all;
  font-weight: 500;
}

.file-meta {
  font-size: 0.68rem;
  opacity: 0.55;
  flex: 1;
}

.file-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-left: auto;
}

@media (min-width: 960px) {
  .file-name {
    flex: 1 1 auto;
    min-width: 0;
  }
}
</style>
