<script setup>
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

defineProps({
  projects: { type: Array, default: () => [] },
})

const { t, te } = useI18n()
const trOr = (key, fallback) => (te(key) ? t(key) : fallback)
const projectStatusLabel = (status) => trOr(`workflow.projectStatus.${status}`, status)
const stageLabel = (name) => trOr(`workflow.stageNames.${name}`, name)
const displayProjectTitle = (raw) => {
  const m = (raw || '').match(/^项目\s*(.+)$/)
  return m ? `${t('workflow.projectWord')} ${m[1]}` : raw
}
</script>

<template>
  <div>
    <p v-if="!projects.length" class="page-empty">{{ t('mypage.empty') }}</p>
    <div v-else class="card-list">
      <div v-for="p in projects" :key="p.id" class="proj-card">
        <RouterLink :to="`/my/projects/${p.id}`" class="proj-card-main">
          <div class="proj-head"><strong>{{ p.project_no }}</strong><span>{{ projectStatusLabel(p.status) }}</span></div>
          <p class="proj-title">{{ displayProjectTitle(p.title) }}</p>
          <div class="progress-bar"><span :style="{ width: p.progress_percent + '%' }" /></div>
          <p class="proj-meta">
            {{ t('mypage.progress') }}: {{ p.progress_percent }}%
            <span v-if="p.current_stage"> · {{ t('workflow.currentStage') }}: {{ stageLabel(p.current_stage.name) }}</span>
          </p>
        </RouterLink>
        <RouterLink
          v-if="p.rfq"
          :to="`/my/rfqs/${p.rfq}`"
          class="link deal-link"
        >
          {{ t('fulfillment.viewDeal') }}
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.link { color: var(--color-steel); cursor: pointer; }
.card-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--space-lg); }
.proj-card { border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-lg); text-decoration: none; color: inherit; display: flex; flex-direction: column; gap: 0.5rem; }
.proj-card-main { text-decoration: none; color: inherit; display: flex; flex-direction: column; gap: 0.5rem; }
.deal-link { font-size: 0.85rem; }
.proj-head { display: flex; justify-content: space-between; font-size: 0.8rem; }
.proj-title { margin: 0; font-weight: 600; }
.progress-bar { height: 6px; background: var(--color-border); border-radius: 3px; overflow: hidden; span { display: block; height: 100%; background: var(--color-steel); } }
.proj-meta { font-size: 0.8rem; opacity: 0.65; margin: 0; }
</style>
