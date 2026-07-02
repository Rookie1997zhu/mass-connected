<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchMyRfqs } from '../../api'

const { t } = useI18n()
const items = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetchMyRfqs()
    items.value = res.data.items || []
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <PageShell>
    <div class="list-head">
      <h1 class="page-title">{{ t('myRfqs.title') }}</h1>
      <RouterLink to="/rfq/new" class="btn btn-primary btn-sm">{{ t('rfq.createTitle') }}</RouterLink>
    </div>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <p v-else-if="!items.length" class="page-empty">{{ t('common.empty') }}</p>
    <ul v-else class="page-list">
      <li v-for="item in items" :key="item.id" class="rfq-row">
        <RouterLink :to="`/my/rfqs/${item.id}`" class="rfq-link">
          <span class="rfq-no">{{ item.rfq_no }}</span>
          <span>{{ item.service_category_name }}</span>
          <span class="rfq-meta">{{ t('rfq.quantity') }}: {{ item.quantity }}</span>
          <span class="rfq-meta">{{ t('myRfqs.quotes') }}: {{ item.quotes_count }}</span>
          <span class="rfq-status">{{ item.status }}</span>
        </RouterLink>
      </li>
    </ul>
  </PageShell>
</template>

<style scoped lang="scss">
.list-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-md);
  flex-wrap: wrap;
}
.rfq-row { list-style: none; }
.rfq-link {
  display: flex;
  gap: var(--space-lg);
  align-items: center;
  flex-wrap: wrap;
  padding: var(--space-md) 0;
  text-decoration: none;
  color: var(--color-text-heading);
  border-bottom: 1px solid var(--color-border);
}
.rfq-no { font-weight: 700; }
.rfq-meta { color: var(--color-text); opacity: 0.7; font-size: 0.875rem; }
.rfq-status {
  margin-left: auto;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-steel);
}
</style>
