<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchPartners, fetchServiceCategories } from '../../api'
import { resolveApiMessage } from '../../utils/apiErrors'

const { t, locale } = useI18n()
const items = ref([])
const categories = ref([])
const categoryId = ref('')
const keyword = ref('')
const page = ref(1)
const pagination = ref(null)
const loading = ref(true)
const error = ref('')

const pick = (field) => {
  if (!field || typeof field !== 'object') return field || ''
  return field[locale.value] || field.ko || field.en || Object.values(field)[0] || ''
}

const load = async () => {
  error.value = ''
  const params = { page: page.value, page_size: 12 }
  if (categoryId.value) params.service_category_id = categoryId.value
  if (keyword.value.trim()) params.q = keyword.value.trim()
  try {
    const res = await fetchPartners(params)
    items.value = res.data.items || []
    pagination.value = res.data.pagination || null
  } catch (e) {
    items.value = []
    pagination.value = null
    error.value = resolveApiMessage(e, t, 'common.failed')
  }
}

onMounted(async () => {
  try {
    const catRes = await fetchServiceCategories()
    categories.value = catRes.data.items || []
    await load()
  } finally {
    loading.value = false
  }
})

const onFilter = async () => {
  page.value = 1
  loading.value = true
  try {
    await load()
  } finally {
    loading.value = false
  }
}

const goPage = async (next) => {
  if (!pagination.value) return
  if (next < 1 || next > pagination.value.total_pages) return
  page.value = next
  loading.value = true
  try {
    await load()
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ t('partners.directoryTitle') }}</h1>
    <p class="page-lead">{{ t('partners.directoryDesc') }}</p>

    <div class="filters">
      <input
        v-model="keyword"
        type="search"
        :placeholder="t('partners.searchPlaceholder')"
        @keyup.enter="onFilter"
      />
      <select v-model="categoryId" @change="onFilter">
        <option value="">{{ t('demandHall.allCategories') }}</option>
        <option v-for="c in categories" :key="c.id" :value="c.id">{{ pick(c.name) }}</option>
      </select>
      <button type="button" class="btn btn-secondary btn-sm" @click="onFilter">{{ t('common.view') }}</button>
    </div>

    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <p v-else-if="error" class="page-message page-message--error">{{ error }}</p>
    <p v-else-if="!items.length" class="page-empty">{{ t('partners.directoryEmpty') }}</p>
    <div v-else class="partner-list">
      <RouterLink
        v-for="item in items"
        :key="item.id"
        :to="`/partners/${item.id}`"
        class="partner-card card"
      >
        <h2>{{ item.company_name }}</h2>
        <p v-if="item.region" class="muted">{{ item.region }}</p>
        <p v-if="item.intro" class="intro">{{ item.intro }}</p>
        <ul v-if="item.process_names?.length" class="tags">
          <li v-for="(name, idx) in item.process_names" :key="idx">{{ name }}</li>
        </ul>
      </RouterLink>
    </div>

    <div v-if="pagination && pagination.total_pages > 1" class="pager">
      <button type="button" class="btn btn-secondary btn-sm" :disabled="page <= 1" @click="goPage(page - 1)">
        {{ t('rfq.prev') }}
      </button>
      <span>{{ page }} / {{ pagination.total_pages }}</span>
      <button
        type="button"
        class="btn btn-secondary btn-sm"
        :disabled="page >= pagination.total_pages"
        @click="goPage(page + 1)"
      >
        {{ t('rfq.next') }}
      </button>
    </div>

    <p class="cta">
      {{ t('partners.directoryCta') }}
      <RouterLink to="/register?type=enterprise">{{ t('register.enterprise') }}</RouterLink>
    </p>
  </PageShell>
</template>

<style scoped lang="scss">
.page-lead { color: var(--color-text-muted); margin-bottom: var(--space-lg); }
.filters {
  display: flex; flex-wrap: wrap; gap: var(--space-sm); margin-bottom: var(--space-lg);
  input, select { padding: 0.5rem; border-radius: var(--radius-sm); border: 1px solid var(--color-border); min-width: 12rem; }
}
.partner-list { display: grid; gap: var(--space-md); grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
.partner-card {
  display: block; text-decoration: none; color: inherit; padding: var(--space-lg);
  h2 { margin: 0 0 0.5rem; font-size: 1.125rem; }
}
.muted { color: var(--color-text-muted); font-size: 0.875rem; margin: 0 0 0.5rem; }
.intro {
  font-size: 0.9375rem; margin: 0 0 0.75rem; line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}
.tags { display: flex; flex-wrap: wrap; gap: 0.375rem; list-style: none; padding: 0; margin: 0; li { font-size: 0.75rem; padding: 0.125rem 0.5rem; background: var(--color-steel-muted); border-radius: var(--radius-sm); } }
.pager { display: flex; gap: var(--space-md); align-items: center; justify-content: center; margin-top: var(--space-xl); }
.cta { margin-top: var(--space-xl); text-align: center; color: var(--color-text-muted); a { color: var(--color-steel); font-weight: 600; margin-left: 0.25rem; } }
</style>
