<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchDemandHall, fetchServiceCategories } from '../../api'
import { useAuthStore } from '../../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()
const items = ref([])
const categories = ref([])
const categoryId = ref('')
const loading = ref(true)

const load = async () => {
  const params = {}
  if (categoryId.value) params.service_category_id = categoryId.value
  const res = await fetchDemandHall(params)
  items.value = res.data.items || []
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
    <h1 class="page-title">{{ t('demandHall.title') }}</h1>
    <p class="page-lead">{{ t('demandHall.desc') }}</p>

    <div class="filters">
      <select v-model="categoryId" @change="onFilter">
        <option value="">{{ t('demandHall.allCategories') }}</option>
        <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name?.zh || c.name?.ko }}</option>
      </select>
    </div>

    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <p v-else-if="!items.length" class="page-empty">{{ t('common.empty') }}</p>
    <div v-else class="demand-list">
      <RouterLink v-for="item in items" :key="item.id" :to="`/demand-hall/${item.id}`" class="demand-card card">
        <div class="demand-head">
          <strong>{{ item.rfq_no }}</strong>
          <span class="badge">{{ item.status }}</span>
        </div>
        <p>{{ item.service_category_name }} · {{ t('rfq.quantity') }}: {{ item.quantity }}</p>
        <p class="muted">{{ item.material || '—' }}</p>
        <div class="demand-foot">
          <p class="quotes-count">{{ t('demandHall.quotesCount', { count: item.quotes_count }) }}</p>
          <span v-if="auth.isSupplier" class="grab-badge">{{ t('demandHall.grab') }}</span>
        </div>
      </RouterLink>
    </div>
  </PageShell>
</template>

<style scoped lang="scss">
.page-lead { color: var(--color-text-muted); margin-bottom: var(--space-lg); }
.filters { margin-bottom: var(--space-lg); select { padding: 0.5rem; border-radius: var(--radius-sm); border: 1px solid var(--color-border); } }
.demand-list { display: grid; gap: var(--space-md); }
.demand-card { display: block; text-decoration: none; color: inherit; padding: var(--space-lg); transition: box-shadow var(--duration-fast); &:hover { box-shadow: var(--shadow-md); } }
.demand-head { display: flex; justify-content: space-between; margin-bottom: 0.5rem; }
.badge { font-size: 0.75rem; padding: 0.125rem 0.5rem; background: var(--color-steel-muted); border-radius: var(--radius-sm); }
.muted { color: var(--color-text-muted); font-size: 0.875rem; }
.demand-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem; }
.quotes-count { font-size: 0.8125rem; color: var(--color-steel); margin: 0; }
.grab-badge { font-size: 0.75rem; padding: 0.125rem 0.5rem; background: var(--color-steel); color: #fff; border-radius: var(--radius-sm); }
</style>
