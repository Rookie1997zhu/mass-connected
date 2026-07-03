<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchSupplierProjects } from '../../api'

const { t } = useI18n()
const items = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetchSupplierProjects()
    items.value = res.data.items || []
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ t('supplierProject.title') }}</h1>
    <p class="page-lead">{{ t('supplierProject.desc') }}</p>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <p v-else-if="!items.length" class="page-empty">{{ t('supplierProject.empty') }}</p>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th>{{ t('supplierProject.projectNo') }}</th>
          <th>{{ t('supplierProject.projectTitle') }}</th>
          <th>{{ t('mypage.status') }}</th>
          <th>{{ t('mypage.progress') }}</th>
          <th>{{ t('supplierProject.expectedDelivery') }}</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in items" :key="p.id">
          <td>{{ p.project_no }}</td>
          <td>{{ p.title }}</td>
          <td><span class="badge" :class="p.status">{{ p.status }}</span></td>
          <td>{{ p.progress_percent }}%</td>
          <td>{{ p.expected_delivery_date || '—' }}</td>
          <td>
            <RouterLink :to="`/supplier/projects/${p.id}`" class="link">{{ t('demandHall.view') }}</RouterLink>
          </td>
        </tr>
      </tbody>
    </table>
  </PageShell>
</template>

<style scoped lang="scss">
.data-table {
  width: 100%;
  border-collapse: collapse;
  th, td {
    text-align: left;
    padding: var(--space-sm) var(--space-md);
    border-bottom: 1px solid var(--color-border);
    font-size: 0.9rem;
  }
  th {
    font-size: 0.72rem;
    text-transform: uppercase;
    opacity: 0.6;
  }
}
.link { color: var(--color-steel); }
.badge {
  font-size: 0.72rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: var(--color-border);
}
.badge.in_progress { background: #dbeafe; }
.badge.completed { background: #dcfce7; }
</style>
