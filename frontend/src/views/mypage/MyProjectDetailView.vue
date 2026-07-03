<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchMyProject, toggleProjectTodo } from '../../api'

const { t } = useI18n()
const route = useRoute()
const project = ref(null)
const loading = ref(true)

const load = async () => {
  const res = await fetchMyProject(route.params.id)
  project.value = res.data
}

onMounted(async () => {
  try { await load() } finally { loading.value = false }
})

const onToggle = async (todo) => {
  await toggleProjectTodo(project.value.id, todo.id)
  await load()
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

      <h2 class="section-sub">{{ t('mypage.projects') }}</h2>
      <ol class="stage-list">
        <li v-for="s in project.stages" :key="s.id" :class="s.status">
          <span class="stage-dot" />
          <span class="stage-name">{{ s.name }}</span>
          <span class="stage-status">{{ s.status }}</span>
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
          <span class="todo-assignee">{{ td.assignee_type }}</span>
        </li>
      </ul>

      <h2 class="section-sub">{{ t('mypage.files') }}</h2>
      <p v-if="!project.files?.length" class="page-empty">—</p>
      <ul v-else class="file-list">
        <li v-for="f in project.files" :key="f.id">
          <a :href="f.file_url" target="_blank" rel="noopener">{{ f.file_name }}</a>
        </li>
      </ul>

      <h2 class="section-sub">{{ t('mypage.timeline') }}</h2>
      <p v-if="!project.updates?.length" class="page-empty">—</p>
      <ul v-else class="timeline">
        <li v-for="u in project.updates" :key="u.id">
          <span class="tl-time">{{ (u.created_at || '').slice(0, 16).replace('T', ' ') }}</span>
          <p>{{ u.content }}</p>
        </li>
      </ul>
    </template>
  </PageShell>
</template>

<style scoped lang="scss">
.proj-no { opacity: 0.6; font-size: 0.85rem; margin: 0 0 var(--space-md); }
.progress-bar { height: 8px; background: var(--color-border); border-radius: 4px; overflow: hidden; max-width: 480px; span { display: block; height: 100%; background: var(--color-steel); } }
.proj-meta { font-size: 0.85rem; opacity: 0.7; }
.section-sub { font-size: 1.125rem; margin: var(--space-xl) 0 var(--space-md); }
.stage-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-sm); li { display: flex; align-items: center; gap: var(--space-md); font-size: 0.9rem; } }
.stage-dot { width: 12px; height: 12px; border-radius: 50%; background: var(--color-border); flex-shrink: 0; }
li.in_progress .stage-dot { background: var(--color-steel); }
li.completed .stage-dot { background: #15803d; }
.stage-status { margin-left: auto; font-size: 0.75rem; opacity: 0.6; }
.todo-list { list-style: none; padding: 0; margin: 0; li { display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid var(--color-border); label { display: flex; align-items: center; gap: 0.5rem; } .done { text-decoration: line-through; opacity: 0.5; } } }
.todo-assignee { font-size: 0.72rem; opacity: 0.55; }
.timeline { list-style: none; padding-left: var(--space-md); margin: 0; border-left: 2px solid var(--color-border); li { padding: 0 0 var(--space-md) var(--space-md); p { margin: 0.25rem 0 0; font-size: 0.9rem; } } }
.tl-time { font-size: 0.72rem; opacity: 0.55; }
.file-list { list-style: none; padding: 0; margin: 0; li { padding: 0.5rem 0; border-bottom: 1px solid var(--color-border); a { color: var(--color-steel); } } }
</style>
