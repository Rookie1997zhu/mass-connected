<script setup>
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

defineProps({
  rfqs: { type: Array, default: () => [] },
})

const { t } = useI18n()
</script>

<template>
  <div>
    <RouterLink to="/rfq/new" class="btn btn-primary btn-sm mb">＋ {{ t('rfq.createTitle') }}</RouterLink>
    <p v-if="!rfqs.length" class="page-empty">{{ t('mypage.empty') }}</p>
    <table v-else class="data-table">
      <thead><tr><th>No.</th><th>{{ t('rfq.stepProcess') }}</th><th>{{ t('mypage.status') }}</th><th></th></tr></thead>
      <tbody>
        <tr v-for="r in rfqs" :key="r.id">
          <td>{{ r.rfq_no }}</td>
          <td>{{ r.service_category_name }}</td>
          <td>{{ r.status }}</td>
          <td><RouterLink :to="`/my/rfqs/${r.id}`" class="link">{{ t('demandHall.view') }}</RouterLink></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped lang="scss">
.mb { margin-bottom: var(--space-md); }
.data-table { width: 100%; border-collapse: collapse; th, td { text-align: left; padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border); font-size: 0.9rem; } th { font-size: 0.72rem; text-transform: uppercase; opacity: 0.6; } }
.link { color: var(--color-steel); cursor: pointer; }
</style>
