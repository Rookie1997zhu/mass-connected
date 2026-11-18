<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchPartner } from '../../api'
import { resolveApiMessage } from '../../utils/apiErrors'

const { t } = useI18n()
const route = useRoute()
const partner = ref(null)
const loading = ref(true)
const error = ref('')

const rfqLink = computed(() => {
  const firstId = partner.value?.process_ids?.[0]
  return firstId ? `/rfq/new?category=${firstId}` : '/rfq/new'
})

const locationText = computed(() =>
  [partner.value?.region, partner.value?.city, partner.value?.country].filter(Boolean).join(' · ') || '—',
)

onMounted(async () => {
  try {
    const res = await fetchPartner(route.params.id)
    partner.value = res.data
  } catch (e) {
    error.value = resolveApiMessage(e, t, 'partners.detailLoadFailed')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <PageShell>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <template v-else-if="partner">
      <p class="back">
        <RouterLink to="/partners">← {{ t('partners.directoryTitle') }}</RouterLink>
      </p>
      <h1 class="page-title">{{ partner.company_name }}</h1>
      <p v-if="partner.short_name" class="muted">{{ partner.short_name }}</p>
      <p class="muted">{{ locationText }}</p>
      <ul v-if="partner.process_names?.length" class="tags">
        <li v-for="(name, idx) in partner.process_names" :key="idx">{{ name }}</li>
      </ul>
      <p v-if="partner.intro" class="intro">{{ partner.intro }}</p>

      <div class="actions">
        <RouterLink :to="rfqLink" class="btn btn-primary">{{ t('partners.ctaFromCapability') }}</RouterLink>
      </div>

      <section class="facts">
        <h2 class="section-sub">{{ t('partners.capabilityFacts') }}</h2>
        <dl class="detail-grid">
          <div><dt>{{ t('quoteDetail.mainProducts') }}</dt><dd>{{ partner.main_products || '—' }}</dd></div>
          <div><dt>{{ t('quoteDetail.monthlyCapacity') }}</dt><dd>{{ partner.monthly_capacity || '—' }}</dd></div>
          <div><dt>{{ t('quoteDetail.establishedYear') }}</dt><dd>{{ partner.established_year || '—' }}</dd></div>
          <div><dt>{{ t('quoteDetail.employeeScale') }}</dt><dd>{{ partner.employee_scale || '—' }}</dd></div>
          <div><dt>{{ t('quoteDetail.factoryArea') }}</dt><dd>{{ partner.factory_area_sqm || '—' }}</dd></div>
          <div><dt>{{ t('quoteDetail.certifications') }}</dt><dd>{{ partner.quality_certifications || '—' }}</dd></div>
          <div class="full"><dt>{{ t('quoteDetail.equipment') }}</dt><dd>{{ partner.equipment_summary || '—' }}</dd></div>
        </dl>
      </section>

      <section>
        <h2 class="section-sub">{{ t('partners.publicAttachments') }}</h2>
        <ul v-if="partner.public_attachments?.length" class="att-list">
          <li v-for="a in partner.public_attachments" :key="a.id">
            <a :href="a.file_url" target="_blank" rel="noopener">{{ a.file_name }}</a>
            <span class="muted">{{ a.category }}</span>
          </li>
        </ul>
        <p v-else class="page-empty">{{ t('partners.noPublicAttachments') }}</p>
      </section>
    </template>
    <template v-else>
      <p class="page-empty">{{ error || t('partners.detailUnavailable') }}</p>
      <RouterLink to="/partners" class="btn btn-secondary">{{ t('partners.directoryTitle') }}</RouterLink>
    </template>
  </PageShell>
</template>

<style scoped lang="scss">
.back { margin-bottom: var(--space-md); a { color: var(--color-steel); text-decoration: none; } }
.muted { color: var(--color-text-muted); font-size: 0.875rem; }
.intro { margin: var(--space-md) 0; line-height: 1.6; }
.tags { display: flex; flex-wrap: wrap; gap: 0.375rem; list-style: none; padding: 0; margin: var(--space-md) 0; li { font-size: 0.75rem; padding: 0.125rem 0.5rem; background: var(--color-steel-muted); border-radius: var(--radius-sm); } }
.actions { margin: var(--space-lg) 0 var(--space-xl); }
.section-sub { margin: var(--space-xl) 0 var(--space-md); }
.detail-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-md); dt { font-size: 0.8125rem; color: var(--color-text-muted); } dd { margin: 0.25rem 0 0; white-space: pre-wrap; } .full { grid-column: 1 / -1; } }
.att-list { list-style: none; padding: 0; display: grid; gap: 0.5rem; li { display: flex; gap: 0.75rem; align-items: center; } a { color: var(--color-steel); } }
@media (max-width: 640px) { .detail-grid { grid-template-columns: 1fr; } }
</style>
