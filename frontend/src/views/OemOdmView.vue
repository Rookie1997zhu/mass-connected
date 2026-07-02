<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../components/PageShell.vue'
import { fetchContentPage } from '../api'
import { sanitizeHtml } from '../utils/sanitize'

const { locale } = useI18n()
const content = ref(null)

const pick = (field) => {
  if (!field || typeof field !== 'object') return field || ''
  return field[locale.value] || field.ko || field.en || ''
}

const renderedBody = computed(() => sanitizeHtml(pick(content.value?.body)))

onMounted(async () => {
  try {
    const res = await fetchContentPage('oem-odm.services')
    content.value = res.data
  } catch {
    content.value = null
  }
})
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ $t('nav.oemOdm') }}</h1>
    <p v-if="!content" class="page-empty">{{ $t('common.empty') }}</p>
    <article v-else>
      <h2>{{ pick(content.title) }}</h2>
      <div class="rich-content" v-html="renderedBody" />
    </article>
    <RouterLink to="/contact" class="btn btn-primary" style="margin-top: var(--space-xl)">
      {{ $t('nav.contact') }}
    </RouterLink>
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
