<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  title: { type: String, required: true },
  count: { type: Number, default: null },
  empty: { type: Boolean, default: false },
  emptyText: { type: String, default: '' },
})

const { t } = useI18n()

const countLabel = computed(() => {
  if (props.count == null) return ''
  return t('projectActivity.itemCount', { n: props.count })
})
</script>

<template>
  <section class="activity-section">
    <header class="activity-section__head">
      <h2 class="activity-section__title">{{ title }}</h2>
      <span v-if="count != null" class="activity-section__count">{{ countLabel }}</span>
    </header>
    <div class="activity-section__body">
      <p v-if="empty" class="page-empty">{{ emptyText || t('mypage.empty') }}</p>
      <slot v-else />
    </div>
  </section>
</template>

<style scoped lang="scss">
.activity-section {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  overflow: hidden;
}

.activity-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-md) 0;
}

.activity-section__title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
}

.activity-section__count {
  font-size: 0.72rem;
  opacity: 0.55;
  white-space: nowrap;
}

.activity-section__body {
  padding: var(--space-md);

  .page-empty {
    margin: 0;
  }
}
</style>
