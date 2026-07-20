<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import TextTranslateBlock from '../TextTranslateBlock.vue'

const props = defineProps({
  updates: { type: Array, default: () => [] },
  projectId: { type: [Number, String], required: true },
  role: { type: String, required: true },
  showStage: { type: Boolean, default: false },
  stages: { type: Array, default: () => [] },
  internalOnlyLabel: { type: String, default: '' },
})

const { t, te } = useI18n()

const trOr = (key, fallback) => (te(key) ? t(key) : fallback)
const stageLabel = (name) => trOr(`workflow.stageNames.${name}`, name)

const stageNameById = computed(() => {
  const map = {}
  for (const s of props.stages || []) {
    map[s.id] = stageLabel(s.name)
  }
  return map
})

const formatTime = (value) => (value || '').slice(0, 16).replace('T', ' ')
</script>

<template>
  <ul class="timeline">
    <li v-for="u in updates" :key="u.id">
      <div class="tl-head">
        <span class="tl-time">{{ formatTime(u.created_at) }}</span>
        <span v-if="showStage && u.stage && stageNameById[u.stage]" class="tl-stage">
          {{ stageNameById[u.stage] }}
        </span>
        <span v-if="!u.is_customer_visible && internalOnlyLabel" class="tl-private">
          {{ internalOnlyLabel }}
        </span>
      </div>
      <p class="tl-content">{{ u.content }}</p>
      <TextTranslateBlock :project-id="projectId" :role="role" :text="u.content" />
    </li>
  </ul>
</template>

<style scoped lang="scss">
.timeline {
  list-style: none;
  padding: 0 0 0 var(--space-md);
  margin: 0;
  border-left: 2px solid var(--color-border);

  li {
    position: relative;
    padding: 0 0 var(--space-md) var(--space-md);

    &::before {
      content: '';
      position: absolute;
      left: calc(-1 * var(--space-md) - 5px);
      top: 0.35rem;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--color-steel);
      border: 2px solid var(--color-surface);
      box-shadow: 0 0 0 1px var(--color-border);
    }
  }
}

.tl-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
}

.tl-time {
  font-size: 0.72rem;
  opacity: 0.55;
}

.tl-stage {
  font-size: 0.68rem;
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  background: var(--color-steel-muted);
  color: var(--color-steel);
  font-weight: 600;
}

.tl-private {
  font-size: 0.68rem;
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  background: #fef3c7;
  color: #b45309;
  font-weight: 600;
}

.tl-content {
  margin: 0.35rem 0 0;
  font-size: 0.9rem;
  line-height: 1.5;
}
</style>
