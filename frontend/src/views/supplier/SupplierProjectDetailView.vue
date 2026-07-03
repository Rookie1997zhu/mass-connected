<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import {
  addSupplierProjectIssue,
  addSupplierProjectUpdate,
  fetchSupplierProject,
  updateSupplierProjectStage,
  uploadSupplierProjectFile,
} from '../../api'

const { t } = useI18n()
const route = useRoute()
const project = ref(null)
const loading = ref(true)
const submitting = ref(false)

const updateForm = ref({ content: '', is_customer_visible: true, stage: '' })
const issueForm = ref({ title: '', description: '', severity: 'medium' })

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

const onStageChange = async (stage, status) => {
  submitting.value = true
  try {
    await updateSupplierProjectStage(project.value.id, stage.id, { status })
    await load()
  } finally {
    submitting.value = false
  }
}

const onSubmitUpdate = async () => {
  if (!updateForm.value.content.trim()) return
  submitting.value = true
  try {
    await addSupplierProjectUpdate(project.value.id, {
      content: updateForm.value.content.trim(),
      is_customer_visible: updateForm.value.is_customer_visible,
      stage: updateForm.value.stage || null,
    })
    updateForm.value.content = ''
    await load()
  } finally {
    submitting.value = false
  }
}

const onSubmitIssue = async () => {
  if (!issueForm.value.title.trim()) return
  submitting.value = true
  try {
    await addSupplierProjectIssue(project.value.id, {
      title: issueForm.value.title.trim(),
      description: issueForm.value.description.trim(),
      severity: issueForm.value.severity,
    })
    issueForm.value = { title: '', description: '', severity: 'medium' }
    await load()
  } finally {
    submitting.value = false
  }
}

const onUploadFile = async (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('file_category', 'report')
    fd.append('visibility', 'all')
    await uploadSupplierProjectFile(project.value.id, fd)
    await load()
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <PageShell>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <template v-else-if="project">
      <h1 class="page-title">{{ project.title }}</h1>
      <p class="proj-no">{{ project.project_no }} · {{ project.status }}</p>
      <div class="progress-bar"><span :style="{ width: project.progress_percent + '%' }" /></div>
      <p class="proj-meta">{{ t('mypage.progress') }}: {{ project.progress_percent }}%</p>

      <h2 class="section-sub">{{ t('supplierProject.stages') }}</h2>
      <ol class="stage-list">
        <li v-for="s in project.stages" :key="s.id" :class="s.status">
          <span class="stage-dot" />
          <span class="stage-name">{{ s.name }}</span>
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
        </li>
      </ol>

      <h2 class="section-sub">{{ t('supplierProject.postUpdate') }}</h2>
      <form class="action-form" @submit.prevent="onSubmitUpdate">
        <textarea
          v-model="updateForm.content"
          rows="3"
          :placeholder="t('supplierProject.updatePlaceholder')"
          required
        />
        <div class="form-row">
          <label>
            <select v-model="updateForm.stage">
              <option value="">{{ t('supplierProject.noStage') }}</option>
              <option v-for="s in project.stages" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </label>
          <label class="checkbox-label">
            <input v-model="updateForm.is_customer_visible" type="checkbox" />
            {{ t('supplierProject.customerVisible') }}
          </label>
          <button type="submit" class="btn btn-primary btn-sm" :disabled="submitting">
            {{ t('supplierProject.submitUpdate') }}
          </button>
        </div>
      </form>

      <h2 class="section-sub">{{ t('supplierProject.reportIssue') }}</h2>
      <form class="action-form" @submit.prevent="onSubmitIssue">
        <input v-model="issueForm.title" type="text" :placeholder="t('supplierProject.issueTitle')" required />
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

      <h2 class="section-sub">{{ t('supplierProject.files') }}</h2>
      <label class="upload-label">
        {{ t('mypage.uploadFile') }}
        <input type="file" hidden @change="onUploadFile" />
      </label>
      <p v-if="!project.files?.length" class="page-empty">—</p>
      <ul v-else class="file-list">
        <li v-for="f in project.files" :key="f.id">
          <a :href="f.file_url" target="_blank" rel="noopener">{{ f.file_name }}</a>
          <span class="file-meta">{{ f.file_category }} · {{ f.visibility }}</span>
        </li>
      </ul>

      <h2 class="section-sub">{{ t('supplierProject.timeline') }}</h2>
      <p v-if="!project.updates?.length" class="page-empty">—</p>
      <ul v-else class="timeline">
        <li v-for="u in project.updates" :key="u.id">
          <span class="tl-time">{{ (u.created_at || '').slice(0, 16).replace('T', ' ') }}</span>
          <span v-if="!u.is_customer_visible" class="tl-private">{{ t('supplierProject.internalOnly') }}</span>
          <p>{{ u.content }}</p>
        </li>
      </ul>

      <h2 class="section-sub">{{ t('supplierProject.issues') }}</h2>
      <p v-if="!project.issues?.length" class="page-empty">—</p>
      <ul v-else class="issue-list">
        <li v-for="issue in project.issues" :key="issue.id">
          <strong>{{ issue.title }}</strong>
          <span class="issue-meta">{{ issue.severity }} · {{ issue.status }}</span>
          <p v-if="issue.description">{{ issue.description }}</p>
        </li>
      </ul>
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
.section-sub { font-size: 1.125rem; margin: var(--space-xl) 0 var(--space-md); }
.stage-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  li { display: flex; align-items: center; gap: var(--space-md); font-size: 0.9rem; }
}
.stage-dot { width: 12px; height: 12px; border-radius: 50%; background: var(--color-border); flex-shrink: 0; }
li.in_progress .stage-dot { background: var(--color-steel); }
li.completed .stage-dot { background: #15803d; }
.stage-name { flex: 1; }
.stage-select { font-size: 0.85rem; padding: 0.25rem 0.5rem; }
.action-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  max-width: 560px;
  textarea, input, select { width: 100%; padding: 0.5rem; font: inherit; border: 1px solid var(--color-border); border-radius: 4px; }
}
.form-row { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-md); }
.checkbox-label { display: flex; align-items: center; gap: 0.35rem; font-size: 0.85rem; }
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
  li { padding: 0.75rem 0; border-bottom: 1px solid var(--color-border); p { margin: 0.25rem 0 0; font-size: 0.85rem; opacity: 0.8; } }
}
.issue-meta { font-size: 0.72rem; opacity: 0.55; margin-left: 0.5rem; }
.upload-label { display: inline-block; margin-bottom: var(--space-md); color: var(--color-steel); cursor: pointer; font-size: 0.85rem; }
.file-list { list-style: none; padding: 0; margin: 0 0 var(--space-lg); li { padding: 0.5rem 0; border-bottom: 1px solid var(--color-border); a { color: var(--color-steel); } } }
.file-meta { font-size: 0.72rem; opacity: 0.55; margin-left: 0.5rem; }
</style>
