<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import FilePreviewModal from '../../components/FilePreviewModal.vue'
import TextTranslateBlock from '../../components/TextTranslateBlock.vue'
import {
  addSupplierProjectIssue,
  addSupplierProjectUpdate,
  deleteSupplierProjectFile,
  downloadSupplierDefectReportTemplate,
  fetchSupplierProject,
  updateSupplierProjectStage,
  uploadSupplierProjectFile,
} from '../../api'

const { t, te } = useI18n()
const route = useRoute()

// 后端存量数据为中文（阶段名/标题前缀），展示层做本地化映射，未知值回退原文
const trOr = (key, fallback) => (te(key) ? t(key) : fallback)
const stageLabel = (name) => trOr(`workflow.stageNames.${name}`, name)
const projectStatusLabel = (status) => trOr(`workflow.projectStatus.${status}`, status)
const issueSeverityLabel = (v) => trOr(`workflow.issueSeverity.${v}`, v)
const issueStatusLabel = (v) => trOr(`workflow.issueStatus.${v}`, v)
const fileCategoryLabel = (v) => trOr(`fileCategory.${v}`, v)
const project = ref(null)
const loading = ref(true)
const submitting = ref(false)
const actionError = ref('')
const uploadError = ref('')
const fileActionError = ref('')
const deletingFileId = ref(null)
const previewFile = ref(null)
const previewOpen = ref(false)

const updateForm = ref({ content: '', is_customer_visible: true })
const issueForm = ref({ title: '', description: '', severity: 'medium' })
const uploadForm = ref({
  file_category: 'bom',
  file: null,
})

const stageOptions = [
  { value: 'pending', labelKey: 'supplierProject.stagePending' },
  { value: 'in_progress', labelKey: 'supplierProject.stageInProgress' },
  { value: 'completed', labelKey: 'supplierProject.stageCompleted' },
]

const severityOptions = [
  { value: 'low', labelKey: 'supplierProject.severityLow' },
  { value: 'medium', labelKey: 'supplierProject.severityMedium' },
  { value: 'high', labelKey: 'supplierProject.severityHigh' },
]

const fileCategories = [
  { value: 'bom', labelKey: 'fileCategory.bom' },
  { value: 'purchase_order', labelKey: 'fileCategory.purchase_order' },
  { value: 'defect_report', labelKey: 'fileCategory.defect_report' },
  { value: 'sample_image', labelKey: 'fileCategory.sample_image' },
  { value: 'report', labelKey: 'fileCategory.report' },
  { value: 'design', labelKey: 'fileCategory.design' },
  { value: 'other', labelKey: 'fileCategory.other' },
]

const load = async () => {
  const res = await fetchSupplierProject(route.params.id)
  project.value = res.data
}

onMounted(async () => {
  try {
    await load()
  } finally {
    loading.value = false
  }
})

const currentStage = computed(() => project.value?.current_stage || null)
const currentStageName = computed(() => {
  const name = currentStage.value?.name
  return name ? stageLabel(name) : '—'
})
const hasCurrentStage = computed(() => Boolean(currentStage.value?.id))

const displayTitle = computed(() => {
  const raw = project.value?.title || ''
  const m = raw.match(/^项目\s*(.+)$/)
  return m ? `${t('workflow.projectWord')} ${m[1]}` : raw
})

const filesByStage = computed(() => {
  const map = {}
  for (const f of project.value?.files || []) {
    const key = f.stage_id || 'none'
    if (!map[key]) map[key] = []
    map[key].push(f)
  }
  return map
})

/** Current-stage updates first; legacy rows without stage remain visible. */
const panelUpdates = computed(() => {
  const stageId = currentStage.value?.id
  const updates = project.value?.updates || []
  if (!stageId) return updates
  return updates.filter((u) => !u.stage || u.stage === stageId)
})

const onStageChange = async (stage, status) => {
  submitting.value = true
  actionError.value = ''
  try {
    await updateSupplierProjectStage(project.value.id, stage.id, { status })
    await load()
  } catch (e) {
    actionError.value = e.message || t('supplierProject.uploadFailed')
  } finally {
    submitting.value = false
  }
}

const onSubmitUpdate = async () => {
  if (!updateForm.value.content.trim()) return
  if (!hasCurrentStage.value) {
    actionError.value = t('supplierProject.noActiveStage')
    return
  }
  submitting.value = true
  actionError.value = ''
  try {
    await addSupplierProjectUpdate(project.value.id, {
      content: updateForm.value.content.trim(),
      is_customer_visible: updateForm.value.is_customer_visible,
      stage: currentStage.value.id,
    })
    updateForm.value.content = ''
    await load()
  } catch (e) {
    actionError.value = e.message || t('supplierProject.uploadFailed')
  } finally {
    submitting.value = false
  }
}

const onSubmitIssue = async () => {
  if (!issueForm.value.title.trim()) return
  submitting.value = true
  actionError.value = ''
  try {
    await addSupplierProjectIssue(project.value.id, {
      title: issueForm.value.title.trim(),
      description: issueForm.value.description.trim(),
      severity: issueForm.value.severity,
    })
    issueForm.value = { title: '', description: '', severity: 'medium' }
    await load()
  } catch (e) {
    actionError.value = e.message || t('supplierProject.uploadFailed')
  } finally {
    submitting.value = false
  }
}

const onFilePicked = (e) => {
  uploadForm.value.file = e.target.files?.[0] || null
}

const onUploadFile = async () => {
  uploadError.value = ''
  if (!uploadForm.value.file) {
    uploadError.value = t('supplierProject.fileRequired')
    return
  }
  if (!hasCurrentStage.value) {
    uploadError.value = t('supplierProject.noActiveStage')
    return
  }
  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('file', uploadForm.value.file)
    fd.append('file_category', uploadForm.value.file_category)
    fd.append('stage', String(currentStage.value.id))
    fd.append('visibility', 'all')
    await uploadSupplierProjectFile(project.value.id, fd)
    uploadForm.value.file = null
    await load()
  } catch (e) {
    uploadError.value = e.message || t('supplierProject.uploadFailed')
  } finally {
    submitting.value = false
  }
}

const onDownloadTemplate = async () => {
  const blob = await downloadSupplierDefectReportTemplate()
  const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob]))
  const a = document.createElement('a')
  a.href = url
  a.download = 'defect_report_template.docx'
  a.click()
  URL.revokeObjectURL(url)
}

const openPreview = (file) => {
  previewFile.value = file
  previewOpen.value = true
}

const onDeleteFile = async (fileId) => {
  if (!project.value?.id || deletingFileId.value) return
  fileActionError.value = ''
  deletingFileId.value = fileId
  try {
    await deleteSupplierProjectFile(project.value.id, fileId)
    await load()
  } catch (e) {
    fileActionError.value = e.message || t('supplierProject.fileDeleteFailed')
  } finally {
    deletingFileId.value = null
  }
}
</script>

<template>
  <PageShell>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <template v-else-if="project">
      <h1 class="page-title">{{ displayTitle }}</h1>
      <p class="proj-no">{{ project.project_no }} · {{ projectStatusLabel(project.status) }}</p>
      <div class="progress-bar"><span :style="{ width: project.progress_percent + '%' }" /></div>
      <p class="proj-meta">
        {{ t('mypage.progress') }}: {{ project.progress_percent }}% ·
        {{ t('workflow.currentStage') }}: <strong>{{ currentStageName }}</strong>
      </p>
      <p v-if="project.quote_request_id" class="deal-link">
        <RouterLink :to="`/supplier/quote-requests/${project.quote_request_id}`">
          {{ t('fulfillment.viewDeal') }}
        </RouterLink>
      </p>

      <h2 class="section-sub">{{ t('workflow.title') }}</h2>
      <p class="hint">{{ t('supplierProject.stageAutoBindHint') }}</p>
      <p v-if="actionError" class="page-message page-message--error">{{ actionError }}</p>
      <ol class="workflow-steps">
        <li
          v-for="s in project.stages"
          :key="s.id"
          :class="[s.status, { current: currentStage?.id === s.id, expanded: currentStage?.id === s.id }]"
        >
          <div class="step-head">
            <span class="step-name">{{ stageLabel(s.name) }}</span>
            <select
              class="stage-select"
              :value="s.status"
              :disabled="submitting"
              @change="onStageChange(s, $event.target.value)"
            >
              <option v-for="opt in stageOptions" :key="opt.value" :value="opt.value">
                {{ t(opt.labelKey) }}
              </option>
            </select>
          </div>

          <div v-if="currentStage?.id === s.id" class="stage-panel">
            <section class="panel-block">
              <h3>{{ t('supplierProject.postUpdate') }}</h3>
              <form class="action-form" @submit.prevent="onSubmitUpdate">
                <textarea
                  v-model="updateForm.content"
                  rows="3"
                  :placeholder="t('supplierProject.updatePlaceholder')"
                  required
                />
                <div class="form-row">
                  <label class="checkbox-label">
                    <input v-model="updateForm.is_customer_visible" type="checkbox" />
                    {{ t('supplierProject.customerVisible') }}
                  </label>
                  <button
                    type="submit"
                    class="btn btn-primary btn-sm"
                    :disabled="submitting || !hasCurrentStage"
                  >
                    {{ t('supplierProject.submitUpdate') }}
                  </button>
                </div>
              </form>
            </section>

            <section class="panel-block">
              <h3>{{ t('supplierProject.reportIssue') }}</h3>
              <form class="action-form" @submit.prevent="onSubmitIssue">
                <input
                  v-model="issueForm.title"
                  type="text"
                  :placeholder="t('supplierProject.issueTitle')"
                  required
                />
                <textarea
                  v-model="issueForm.description"
                  rows="2"
                  :placeholder="t('supplierProject.issueDesc')"
                />
                <div class="form-row">
                  <select v-model="issueForm.severity">
                    <option v-for="opt in severityOptions" :key="opt.value" :value="opt.value">
                      {{ t(opt.labelKey) }}
                    </option>
                  </select>
                  <button type="submit" class="btn btn-secondary btn-sm" :disabled="submitting">
                    {{ t('supplierProject.submitIssue') }}
                  </button>
                </div>
              </form>
            </section>

            <section class="panel-block">
              <h3>{{ t('supplierProject.timeline') }}</h3>
              <p v-if="!panelUpdates.length" class="page-empty">{{ t('mypage.empty') }}</p>
              <ul v-else class="timeline">
                <li v-for="u in panelUpdates" :key="u.id">
                  <span class="tl-time">{{ (u.created_at || '').slice(0, 16).replace('T', ' ') }}</span>
                  <span v-if="!u.is_customer_visible" class="tl-private">{{ t('supplierProject.internalOnly') }}</span>
                  <p>{{ u.content }}</p>
                  <TextTranslateBlock :project-id="project.id" role="supplier" :text="u.content" />
                </li>
              </ul>
            </section>

            <section class="panel-block">
              <h3>{{ t('supplierProject.issues') }}</h3>
              <p v-if="!project.issues?.length" class="page-empty">{{ t('mypage.empty') }}</p>
              <ul v-else class="issue-list">
                <li v-for="issue in project.issues" :key="issue.id">
                  <strong>{{ issue.title }}</strong>
                  <span class="issue-meta">
                    {{ issueSeverityLabel(issue.severity) }} · {{ issueStatusLabel(issue.status) }}
                  </span>
                  <p v-if="issue.description">{{ issue.description }}</p>
                  <TextTranslateBlock
                    :project-id="project.id"
                    role="supplier"
                    :text="[issue.title, issue.description].filter(Boolean).join('\n')"
                  />
                </li>
              </ul>
            </section>

            <section class="panel-block">
              <h3>{{ t('supplierProject.files') }}</h3>
              <p class="hint">{{ t('supplierProject.fileBuyerVisibleHint') }}</p>
              <div class="upload-form">
                <label>
                  {{ t('fileCategory.label') }}
                  <select v-model="uploadForm.file_category">
                    <option v-for="c in fileCategories" :key="c.value" :value="c.value">
                      {{ t(c.labelKey) }}
                    </option>
                  </select>
                </label>
                <label>
                  {{ t('mypage.uploadFile') }}
                  <input type="file" @change="onFilePicked" />
                </label>
                <div class="form-row">
                  <button
                    type="button"
                    class="btn btn-primary btn-sm"
                    :disabled="submitting || !hasCurrentStage"
                    @click="onUploadFile"
                  >
                    {{ t('supplierProject.upload') }}
                  </button>
                  <button type="button" class="btn btn-secondary btn-sm" @click="onDownloadTemplate">
                    {{ t('supplierProject.downloadDefectTemplate') }}
                  </button>
                </div>
                <p v-if="uploadError" class="page-message page-message--error">{{ uploadError }}</p>
              </div>
            </section>
          </div>
        </li>
      </ol>
      <p v-if="!hasCurrentStage" class="page-empty">{{ t('supplierProject.noActiveStage') }}</p>

      <h2 class="section-sub">{{ t('supplierProject.files') }}</h2>
      <p v-if="fileActionError" class="page-message page-message--error">{{ fileActionError }}</p>
      <template v-for="s in project.stages" :key="'files-' + s.id">
        <h3 class="stage-file-title">{{ stageLabel(s.name) }}</h3>
        <p v-if="!(filesByStage[s.id] || []).length" class="page-empty">—</p>
        <ul v-else class="file-list">
          <li v-for="f in filesByStage[s.id]" :key="f.id">
            <span>{{ f.file_name }}</span>
            <span class="file-meta">{{ fileCategoryLabel(f.file_category) }}</span>
            <button
              v-if="f.is_previewable"
              type="button"
              class="btn btn-secondary btn-sm"
              @click="openPreview(f)"
            >
              {{ t('filePreview.preview') }}
            </button>
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              :disabled="deletingFileId === f.id"
              @click="onDeleteFile(f.id)"
            >
              {{ t('supplierProject.removeFile') }}
            </button>
          </li>
        </ul>
      </template>

      <FilePreviewModal
        :open="previewOpen"
        :file="previewFile"
        :project-id="project?.id"
        role="supplier"
        @close="previewOpen = false"
      />
    </template>
  </PageShell>
</template>

<style scoped lang="scss">
.proj-no { opacity: 0.6; font-size: 0.85rem; margin: 0 0 var(--space-md); }
.progress-bar {
  height: 8px;
  background: var(--color-border);
  border-radius: 4px;
  overflow: hidden;
  max-width: 480px;
  span { display: block; height: 100%; background: var(--color-steel); }
}
.proj-meta { font-size: 0.85rem; opacity: 0.7; }
.deal-link { margin: 0.5rem 0 0; a { color: var(--color-steel); font-weight: 600; text-decoration: none; } }
.section-sub { font-size: 1.125rem; margin: var(--space-xl) 0 var(--space-md); }
.hint { font-size: 0.8rem; opacity: 0.7; margin: 0 0 var(--space-md); }
.workflow-steps {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  li {
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 0.75rem 1rem;
  }
  li.current { border-color: var(--color-steel); }
  li.expanded { padding-bottom: 1rem; }
}
.step-head {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}
.step-name { flex: 1; font-weight: 600; }
.stage-select { font-size: 0.85rem; padding: 0.25rem 0.5rem; }
.stage-panel {
  margin-top: var(--space-md);
  padding-top: var(--space-md);
  border-top: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}
.panel-block {
  h3 {
    margin: 0 0 var(--space-sm);
    font-size: 0.95rem;
  }
}
.action-form, .upload-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  max-width: 560px;
  textarea, input, select {
    width: 100%;
    padding: 0.5rem;
    font: inherit;
    border: 1px solid var(--color-border);
    border-radius: 4px;
  }
  label { display: flex; flex-direction: column; gap: 0.35rem; font-size: 0.85rem; }
}
.form-row { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-md); }
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.85rem;
  flex-direction: row !important;
}
.timeline {
  list-style: none;
  padding-left: var(--space-md);
  margin: 0;
  border-left: 2px solid var(--color-border);
  li { padding: 0 0 var(--space-md) var(--space-md); p { margin: 0.25rem 0 0; font-size: 0.9rem; } }
}
.tl-time { font-size: 0.72rem; opacity: 0.55; }
.tl-private { font-size: 0.72rem; margin-left: 0.5rem; color: #b45309; }
.issue-list {
  list-style: none;
  padding: 0;
  margin: 0;
  li {
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--color-border);
    p { margin: 0.25rem 0 0; font-size: 0.85rem; opacity: 0.8; }
  }
}
.issue-meta { font-size: 0.72rem; opacity: 0.55; margin-left: 0.5rem; }
.stage-file-title { font-size: 0.95rem; margin: var(--space-md) 0 var(--space-sm); }
.file-list {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--space-lg);
  li {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--color-border);
  }
}
.file-meta { font-size: 0.72rem; opacity: 0.55; margin-right: auto; }
</style>
