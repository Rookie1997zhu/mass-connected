<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../components/PageShell.vue'
import { fetchCase } from '../api'
import { sanitizeHtml } from '../utils/sanitize'

const { locale } = useI18n()
const route = useRoute()
const item = ref(null)

const pick = (field) => {
  if (!field || typeof field !== 'object') return field || ''
  return field[locale.value] || field.ko || field.en || ''
}

const renderedContent = computed(() => sanitizeHtml(pick(item.value?.content)))

onMounted(async () => {
  try {
    const res = await fetchCase(route.params.id)
    item.value = res.data
  } catch {
    item.value = null
  }
})
</script>

<template>
  <PageShell>
    <p v-if="!item" class="page-empty">{{ $t('common.empty') }}</p>
    <article v-else>
      <h1 class="page-title">{{ pick(item.title) }}</h1>
      <div class="rich-content" v-html="renderedContent" />
    </article>
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
</style>
