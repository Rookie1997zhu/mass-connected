<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../components/PageShell.vue'
import { fetchDownloads, fetchFaqs } from '../api'

const { locale } = useI18n()
const route = useRoute()
const tab = computed(() => route.params.tab || 'download')
const downloads = ref([])
const faqs = ref([])

const pick = (field) => {
  if (!field || typeof field !== 'object') return field || ''
  return field[locale.value] || field.ko || field.en || ''
}

onMounted(async () => {
  try {
    const [d, f] = await Promise.all([fetchDownloads(), fetchFaqs()])
    downloads.value = d.data.items || []
    faqs.value = f.data.items || []
  } catch {
    downloads.value = []
    faqs.value = []
  }
})
</script>

<template>
  <PageShell>
    <h1 class="page-title">Support</h1>
    <nav class="support-tabs">
      <RouterLink to="/support/download" :class="{ active: tab === 'download' }">Download</RouterLink>
      <RouterLink to="/support/faq" :class="{ active: tab === 'faq' }">FAQ</RouterLink>
    </nav>
    <div v-if="tab === 'download'">
      <p v-if="!downloads.length" class="page-empty">{{ $t('common.empty') }}</p>
      <ul v-else class="page-list">
        <li v-for="item in downloads" :key="item.id" class="page-list-item">
          <a :href="item.url" target="_blank" rel="noopener">{{ pick(item.title) }}</a>
        </li>
      </ul>
    </div>
    <div v-else>
      <p v-if="!faqs.length" class="page-empty">{{ $t('common.empty') }}</p>
      <div v-else class="faq-list">
        <details v-for="item in faqs" :key="item.id" class="faq-item">
          <summary>{{ pick(item.question) }}</summary>
          <p>{{ pick(item.answer) }}</p>
        </details>
      </div>
    </div>
  </PageShell>
</template>

<style scoped lang="scss">
.support-tabs {
  display: flex;
  gap: var(--space-md);
  margin-bottom: var(--space-xl);

  a {
    padding: var(--space-sm) var(--space-md);
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--color-text);
    text-decoration: none;
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);

    &.active,
    &.router-link-active {
      background: var(--color-steel-muted);
      border-color: var(--color-steel);
      color: var(--color-steel);
    }
  }
}

.faq-list {
  display: grid;
  gap: var(--space-md);
}

.faq-item {
  padding: var(--space-lg);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);

  summary {
    font-weight: 600;
    cursor: pointer;
    color: var(--color-text-heading);
  }

  p {
    margin-top: var(--space-md);
    line-height: 1.7;
    color: var(--color-text);
  }
}
</style>
