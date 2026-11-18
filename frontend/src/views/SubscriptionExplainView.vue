<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../components/PageShell.vue'
import { fetchPublicSubscriptionPlans } from '../api'
import { resolveApiMessage } from '../utils/apiErrors'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()
const loading = ref(true)
const error = ref('')
const items = ref([])
const note = ref('')

onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchPublicSubscriptionPlans()
    items.value = res.data?.items || []
    note.value = res.data?.note || ''
  } catch (e) {
    error.value = resolveApiMessage(e, t, 'subscription.loadFailed')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <PageShell>
    <div class="sub-page">
      <h1 class="page-title">{{ t('subscription.title') }}</h1>
      <p class="page-lead">{{ t('subscription.desc') }}</p>
      <p class="hint">{{ t('subscription.secondaryHint') }}</p>

      <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
      <p v-else-if="error" class="page-message page-message--error">{{ error }}</p>

      <template v-else>
        <p v-if="note" class="note">{{ note }}</p>
        <p v-if="!items.length" class="page-empty">{{ t('subscription.noPublishedPlans') }}</p>
        <ul v-else class="plan-list">
          <li v-for="p in items" :key="p.id" class="plan-item">
            <h2>{{ p.name }}</h2>
            <p class="meta">{{ p.code }} · {{ p.billing_period }}</p>
            <p v-if="p.description" class="body">{{ p.description }}</p>
            <p v-if="p.is_orderable" class="price">
              {{ p.price_amount }} {{ p.currency }}
            </p>
            <p v-else class="price muted">{{ t('subscription.pricePending') }}</p>
            <ul v-if="p.features_json && Object.keys(p.features_json).length" class="feats">
              <li v-for="(lim, code) in p.features_json" :key="code">
                {{ code }}：{{ lim }}
              </li>
            </ul>
          </li>
        </ul>

        <p class="actions">
          <RouterLink v-if="auth.isLoggedIn" to="/my?tab=entitlements" class="btn btn-primary">
            {{ t('subscription.myEntitlements') }}
          </RouterLink>
          <RouterLink v-else to="/login?redirect=/subscription" class="btn btn-secondary">
            {{ t('nav.login') }}
          </RouterLink>
          <RouterLink to="/buyer" class="btn btn-secondary">{{ t('subscription.backWorkbench') }}</RouterLink>
        </p>
      </template>
    </div>
  </PageShell>
</template>

<style scoped lang="scss">
.sub-page { max-width: 720px; }
.hint, .note { color: var(--color-text-muted, #6b7280); font-size: 0.9rem; }
.plan-list { list-style: none; padding: 0; margin: 1.5rem 0; display: flex; flex-direction: column; gap: 1rem; }
.plan-item {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1rem 1.25rem;
}
.plan-item h2 { margin: 0 0 0.35rem; font-size: 1.1rem; }
.meta, .muted { opacity: 0.65; font-size: 0.85rem; }
.body { margin: 0.5rem 0; }
.price { font-weight: 600; }
.feats { margin: 0.5rem 0 0; padding-left: 1.1rem; font-size: 0.9rem; }
.actions { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 1.5rem; }
</style>
