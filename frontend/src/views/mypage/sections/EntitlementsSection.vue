<script setup>
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

defineProps({
  summary: { type: Object, default: null },
  ledgers: { type: Array, default: () => [] },
})

const { t } = useI18n()
</script>

<template>
  <div class="ent">
    <div class="head">
      <h2>{{ t('mypage.entitlements') }}</h2>
      <RouterLink to="/subscription" class="link">{{ t('subscription.title') }}</RouterLink>
    </div>

    <section v-if="summary?.subscription" class="card">
      <h3>{{ t('subscription.currentPlan') }}</h3>
      <p>
        {{ summary.subscription.plan?.name || '—' }}
        <span class="muted">({{ summary.subscription.status }})</span>
      </p>
      <p class="muted">
        {{ summary.subscription.starts_at?.slice(0, 10) }}
        →
        {{ summary.subscription.ends_at?.slice(0, 10) || '—' }}
      </p>
    </section>
    <p v-else class="page-empty">{{ t('subscription.noActive') }}</p>

    <section class="card">
      <h3>{{ t('subscription.quota') }}</h3>
      <p v-if="!(summary?.entitlements || []).length" class="page-empty">—</p>
      <ul v-else class="list">
        <li v-for="e in summary.entitlements" :key="e.feature_code">
          <strong>{{ e.feature_code }}</strong>
          <span>{{ e.remaining }} / {{ e.period_limit }}</span>
          <span class="muted">used {{ e.period_used }}</span>
        </li>
      </ul>
    </section>

    <section class="card">
      <h3>{{ t('subscription.usageLog') }}</h3>
      <p v-if="!ledgers.length" class="page-empty">—</p>
      <ul v-else class="list">
        <li v-for="row in ledgers" :key="row.id">
          <span>{{ row.feature_code }}</span>
          <span>{{ row.status }}</span>
          <time class="muted">{{ (row.created_at || '').slice(0, 19) }}</time>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped lang="scss">
.head { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; }
.head h2 { margin: 0; }
.link { font-size: 0.875rem; color: var(--color-steel, #3a5a7a); }
.card {
  margin-top: 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1rem 1.25rem;
}
.card h3 { margin: 0 0 0.5rem; font-size: 1rem; }
.list { list-style: none; margin: 0; padding: 0; }
.list li {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  padding: 0.45rem 0;
  border-bottom: 1px solid var(--color-border);
  font-size: 0.9rem;
}
.list li:last-child { border-bottom: 0; }
.muted { opacity: 0.6; }
</style>
