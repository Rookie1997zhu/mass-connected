<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../components/PageShell.vue'
import { fetchContentPage, fetchServiceCategories } from '../api'
import { sanitizeHtml } from '../utils/sanitize'

const { t, locale } = useI18n()
const route = useRoute()
const content = ref(null)
const processes = ref([])
const pageKey = computed(() => {
  const section = route.params.section || 'production'
  return `capabilities.${section}`
})

const pick = (field) => {
  if (!field || typeof field !== 'object') return field || ''
  return field[locale.value] || field.ko || field.en || ''
}

const renderedBody = computed(() => sanitizeHtml(pick(content.value?.body)))

async function load() {
  try {
    const res = await fetchContentPage(pageKey.value)
    content.value = res.data
  } catch {
    content.value = null
  }
}

onMounted(async () => {
  await load()
  try {
    const res = await fetchServiceCategories()
    processes.value = res.data.items || []
  } catch {
    processes.value = []
  }
})
watch(pageKey, load)
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ $t('nav.capabilities') }}</h1>
    <p v-if="!content" class="page-empty">{{ $t('common.empty') }}</p>
    <article v-else>
      <h2>{{ pick(content.title) }}</h2>
      <div class="rich-content" v-html="renderedBody" />
    </article>

    <section v-if="processes.length" class="process-section">
      <h2 class="process-title">{{ t('capabilities.processTitle') }}</h2>
      <div class="process-grid">
        <RouterLink
          v-for="p in processes"
          :key="p.id"
          :to="`/rfq/new?category=${p.slug}`"
          class="process-tile"
        >
          <span class="process-tile-name">{{ pick(p.name) }}</span>
          <span class="process-tile-cta">{{ t('capabilities.getQuote') }} →</span>
        </RouterLink>
      </div>
    </section>
  </PageShell>
</template>

<style scoped lang="scss">
.rich-content {
  line-height: 1.75;
  color: var(--color-text);

  :deep(p) { margin: 0 0 1rem; }
  :deep(ul), :deep(ol) { margin: 0 0 1rem; padding-left: 1.5rem; }
  :deep(h2), :deep(h3), :deep(h4) {
    margin: 1.5rem 0 0.75rem;
    color: var(--color-text-heading);
  }
  :deep(img) { max-width: 100%; height: auto; border-radius: var(--radius-md); }
  :deep(a) { color: var(--color-steel); }
}

.process-section {
  margin-top: var(--space-3xl);
  padding-top: var(--space-2xl);
  border-top: 1px solid var(--color-border);
}
.process-title {
  font-size: 1.25rem;
  margin-bottom: var(--space-lg);
}
.process-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--space-md);
}
.process-tile {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  padding: var(--space-lg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  text-decoration: none;
  transition: border-color 0.15s;

  &:hover { border-color: var(--color-steel); }
}
.process-tile-name {
  font-weight: 600;
  color: var(--color-text-heading);
}
.process-tile-cta {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-steel);
}
</style>
