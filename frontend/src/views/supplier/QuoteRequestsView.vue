<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchSupplierQuoteRequests } from '../../api'

const { t } = useI18n()
const items = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetchSupplierQuoteRequests()
    items.value = res.data.items || []
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ t('quoteRequest.title') }}</h1>
    <p class="page-lead">{{ t('quoteRequest.desc') }}</p>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <p v-else-if="!items.length" class="page-empty">{{ t('quoteRequest.empty') }}</p>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th>{{ t('quoteRequest.requestNo') }}</th>
          <th>{{ t('rfq.stepProcess') }}</th>
          <th>{{ t('rfq.quantity') }}</th>
          <th>{{ t('quoteRequest.deadline') }}</th>
          <th>{{ t('mypage.status') }}</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="q in items" :key="q.id">
          <td>{{ q.request_no }}</td>
          <td>{{ q.service_category_name }}</td>
          <td>{{ q.quantity }}</td>
          <td>{{ q.deadline || '—' }}</td>
          <td><span class="badge" :class="q.status">{{ q.status }}</span></td>
          <td><RouterLink :to="`/supplier/quote-requests/${q.id}`" class="link">{{ t('demandHall.view') }}</RouterLink></td>
        </tr>
      </tbody>
    </table>
  </PageShell>
</template>

<style scoped lang="scss">
.data-table { width: 100%; border-collapse: collapse; th, td { text-align: left; padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border); font-size: 0.9rem; } th { font-size: 0.72rem; text-transform: uppercase; opacity: 0.6; } }
.link { color: var(--color-steel); }
.badge { font-size: 0.72rem; padding: 0.15rem 0.5rem; border-radius: 999px; background: var(--color-border); }
.badge.quoted { background: #dbeafe; }
.badge.adopted { background: #dcfce7; }
</style>
