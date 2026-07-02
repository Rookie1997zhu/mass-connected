<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../components/PageShell.vue'
import { fetchCases } from '../api'

const { locale, t } = useI18n()
const items = ref([])

const pick = (field) => {
  if (!field || typeof field !== 'object') return field || ''
  return field[locale.value] || field.ko || field.en || ''
}

onMounted(async () => {
  try {
    const res = await fetchCases()
    items.value = res.data.items || []
  } catch {
    items.value = []
  }
})
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ t('nav.cases') }}</h1>
    <p v-if="!items.length" class="page-empty">{{ $t('common.empty') }}</p>
    <div v-else class="grid-3">
      <article v-for="item in items" :key="item.id" class="card">
        <RouterLink :to="`/cases/${item.id}`" class="card-link">
          <div class="card-thumb"><span class="card-thumb-label">CASE</span></div>
          <div class="card-body">
            <h3 class="card-title">{{ pick(item.title) }}</h3>
          </div>
        </RouterLink>
      </article>
    </div>
  </PageShell>
</template>
