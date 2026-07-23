<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import FilePreviewModal from '../../components/FilePreviewModal.vue'
import ProjectActivityGrid from '../../components/project/ProjectActivityGrid.vue'
import ProjectActivitySection from '../../components/project/ProjectActivitySection.vue'
import ProjectTimeline from '../../components/project/ProjectTimeline.vue'
import ProjectIssueList from '../../components/project/ProjectIssueList.vue'
import ProjectFileCenter from '../../components/project/ProjectFileCenter.vue'
import { fetchMyProject, toggleProjectTodo } from '../../api'

const { t, te } = useI18n()
const route = useRoute()

// 后端存量数据为中文（阶段名/标题前缀），展示层做本地化映射，未知值回退原文
const trOr = (key, fallback) => (te(key) ? t(key) : fallback)
const stageLabel = (name) => trOr(`workflow.stageNames.${name}`, name)
const projectStatusLabel = (status) => trOr(`workflow.projectStatus.${status}`, status)
const project = ref(null)
const loading = ref(true)
const previewFile = ref(null)
const previewOpen = ref(false)

const openPlatformChat = (quoteRequestId) => {
  window.__openPlatformChat?.(quoteRequestId)
}

const load = async () => {
  const res = await fetchMyProject(route.params.id)
  project.value = res.data
}

onMounted(async () => {
  try {
    await load()
  } finally {
    loading.value = false
  }
})

const onToggle = async (todo) => {
  await toggleProjectTodo(project.value.id, todo.id)
  await load()
}

const currentStageName = computed(() => {
  const name = project.value?.current_stage?.name
  return name ? stageLabel(name) : '—'
})

const displayTitle = computed(() => {
  const raw = project.value?.title || ''
  const m = raw.match(/^项目\s*(.+)$/)
  return m ? `${t('workflow.projectWord')} ${m[1]}` : raw
})

const openPreview = (file) => {
  previewFile.value = file
  previewOpen.value = true
}
</script>

<template>
  <PageShell>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <template v-else-if="project">
      <h1 class="page-title">{{ displayTitle }}</h1>
      <p class="proj-no">
        {{ project.project_no }} · {{ projectStatusLabel(project.status) }}
        <span v-if="project.production_order_no"> · {{ project.production_order_no }}</span>
      </p>
      <div class="progress-bar"><span :style="{ width: project.progress_percent + '%' }" /></div>
      <p class="proj-meta">
        {{ t('mypage.progress') }}: {{ project.progress_percent }}% ·
        {{ t('workflow.currentStage') }}: <strong>{{ currentStageName }}</strong>
      </p>
      <p v-if="project.rfq" class="deal-link">
        <RouterLink :to="`/my/rfqs/${project.rfq}`">{{ t('fulfillment.viewDeal') }}</RouterLink>
        <button
          v-if="project.quote_request_id"
          type="button"
          class="btn btn-secondary btn-sm"
          @click="openPlatformChat(project.quote_request_id)"
        >
          {{ t('chat.openChat') }}
        </button>
      </p>

      <h2 class="section-sub">{{ t('workflow.title') }}</h2>
      <ol class="workflow-steps">
        <li
          v-for="s in project.stages"
          :key="s.id"
          :class="[s.status, { current: project.current_stage?.id === s.id }]"
        >
          <span class="step-index">{{ s.sort_order + 1 }}</span>
          <span class="step-name">{{ stageLabel(s.name) }}</span>
          <span class="step-status">{{ t(`workflow.status.${s.status}`) }}</span>
        </li>
      </ol>

      <h2 class="section-sub">{{ t('mypage.todos') }}</h2>
      <p v-if="!project.todos?.length" class="page-empty">—</p>
      <ul v-else class="todo-list">
        <li v-for="td in project.todos" :key="td.id">
          <label>
            <input
              type="checkbox"
              :checked="td.is_done"
              :disabled="td.assignee_type !== 'customer'"
              @change="onToggle(td)"
            />
            <span :class="{ done: td.is_done }">{{ td.title }}</span>
          </label>
          <span class="todo-assignee">{{ trOr(`workflow.assignee.${td.assignee_type}`, td.assignee_type) }}</span>
        </li>
      </ul>

      <ProjectActivityGrid>
        <template #main>
          <ProjectActivitySection
            :title="t('mypage.timeline')"
            :count="project.updates?.length || 0"
            :empty="!project.updates?.length"
          >
            <ProjectTimeline
              :updates="project.updates"
              :project-id="project.id"
              role="member"
            />
          </ProjectActivitySection>
        </template>
        <template #side>
          <ProjectActivitySection
            :title="t('mypage.issues')"
            :count="project.issues?.length || 0"
            :empty="!project.issues?.length"
          >
            <ProjectIssueList
              :issues="project.issues"
              :project-id="project.id"
              role="member"
            />
          </ProjectActivitySection>
          <ProjectActivitySection
            :title="t('mypage.files')"
            :count="project.files?.length || 0"
          >
            <ProjectFileCenter
              :files="project.files"
              :stages="project.stages"
              :current-stage-id="project.current_stage?.id"
              role="member"
              @preview="openPreview"
            />
          </ProjectActivitySection>
        </template>
      </ProjectActivityGrid>

      <FilePreviewModal
        :open="previewOpen"
        :file="previewFile"
        :project-id="project?.id"
        role="member"
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
.workflow-steps {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: var(--space-sm);
  li {
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-md);
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    font-size: 0.85rem;
  }
  li.current { border-color: var(--color-steel); background: var(--color-steel-muted); }
  li.completed { opacity: 0.85; }
  .step-index {
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 50%;
    background: var(--color-border);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
  }
  li.in_progress .step-index, li.current .step-index { background: var(--color-steel); color: #fff; }
  li.completed .step-index { background: #15803d; color: #fff; }
  .step-name { font-weight: 600; }
  .step-status { font-size: 0.72rem; opacity: 0.65; }
}
.todo-list {
  list-style: none;
  padding: 0;
  margin: 0;
  li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--color-border);
    label { display: flex; align-items: center; gap: 0.5rem; }
    .done { text-decoration: line-through; opacity: 0.5; }
  }
}
.todo-assignee { font-size: 0.72rem; opacity: 0.55; }
</style>
