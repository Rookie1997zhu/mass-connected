<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchCategories, fetchProducts } from '../../api'
import { useLocaleCurrency } from '../../composables/useLocaleCurrency'

const { t, locale } = useI18n()
const { formatMoney } = useLocaleCurrency()
const categories = ref([])
const products = ref([])
const categoryId = ref('')
const loading = ref(true)

const pick = (field) => {
  if (!field || typeof field !== 'object') return field || ''
  return field[locale.value] || field.ko || field.en || Object.values(field)[0] || ''
}

const load = async () => {
  const params = {}
  if (categoryId.value) params.category_id = categoryId.value
  const res = await fetchProducts(params)
  products.value = res.data.items || []
}

onMounted(async () => {
  try {
    const catRes = await fetchCategories()
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
    <h1 class="page-title">{{ t('shop.title') }}</h1>
    <p class="page-lead">{{ t('shop.desc') }}</p>

    <div class="shop-layout">
      <aside class="shop-sidebar card">
        <h2>{{ t('shop.categories') }}</h2>
        <button type="button" :class="{ active: !categoryId }" @click="categoryId = ''; onFilter()">
          {{ t('shop.all') }}
        </button>
        <button
          v-for="c in categories"
          :key="c.id"
          type="button"
          :class="{ active: String(categoryId) === String(c.id) }"
          @click="categoryId = c.id; onFilter()"
        >
          {{ pick(c.name) }}
        </button>
      </aside>

      <section class="shop-main">
        <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
        <p v-else-if="!products.length" class="page-empty">{{ t('common.empty') }}</p>
        <div v-else class="product-grid">
          <RouterLink
            v-for="p in products"
            :key="p.id"
            :to="`/shop/products/${p.id}`"
            class="product-card card"
          >
            <div class="product-cover">
              <img v-if="p.cover_url" :src="p.cover_url" :alt="p.name_text" />
              <div v-else class="cover-placeholder" />
            </div>
            <h3>{{ p.name_text }}</h3>
            <p class="price">{{ formatMoney({ amount: p.price_amount, currency: p.currency || 'KRW' }) }}</p>
          </RouterLink>
        </div>
      </section>
    </div>
  </PageShell>
</template>

<style scoped lang="scss">
.page-lead { color: var(--color-text-muted); margin-bottom: var(--space-xl); }
.shop-layout { display: grid; grid-template-columns: 220px 1fr; gap: var(--space-xl); }
.shop-sidebar { padding: var(--space-lg); display: flex; flex-direction: column; gap: 0.5rem; button { text-align: left; padding: 0.5rem 0.75rem; border: none; background: none; border-radius: var(--radius-sm); cursor: pointer; &.active, &:hover { background: var(--color-steel-muted); color: var(--color-steel); } } }
.product-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--space-lg); }
.product-card { text-decoration: none; color: inherit; overflow: hidden; padding: 0; h3 { padding: var(--space-md); margin: 0; font-size: 1rem; } .price { padding: 0 var(--space-md) var(--space-md); color: var(--color-steel); font-weight: 600; } }
.product-cover img, .cover-placeholder { width: 100%; aspect-ratio: 4/3; object-fit: cover; background: var(--color-steel-muted); display: block; }
@media (max-width: 768px) { .shop-layout { grid-template-columns: 1fr; } }
</style>
