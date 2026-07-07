<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { addToCart, fetchProduct } from '../../api'
import { useAuthStore } from '../../stores/auth'
import { useLocaleCurrency } from '../../composables/useLocaleCurrency'

const { t } = useI18n()
const { formatMoney } = useLocaleCurrency()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const product = ref(null)
const quantity = ref(1)
const message = ref('')

onMounted(async () => {
  const res = await fetchProduct(route.params.id)
  product.value = res.data
})

const addCart = async () => {
  if (!auth.isLoggedIn) {
    router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  await addToCart({ product_id: product.value.id, quantity: quantity.value })
  message.value = t('shop.addedToCart')
}
</script>

<template>
  <PageShell v-if="product">
    <div class="detail-layout">
      <div class="detail-cover">
        <img v-if="product.cover_url" :src="product.cover_url" :alt="product.name_text" />
      </div>
      <div class="detail-info">
        <h1 class="page-title">{{ product.name_text }}</h1>
        <p class="price">{{ formatMoney({ amount: product.price_amount, currency: product.currency || 'KRW' }) }}</p>
        <p class="desc">{{ product.description_text }}</p>
        <p>{{ t('shop.stock') }}: {{ product.stock }}</p>
        <label>{{ t('shop.quantity') }}
          <input v-model.number="quantity" type="number" min="1" :max="product.stock" />
        </label>
        <button type="button" class="btn btn-primary" @click="addCart">{{ t('shop.addToCart') }}</button>
        <p v-if="message" class="page-message page-message--success">{{ message }}</p>
      </div>
    </div>
  </PageShell>
</template>

<style scoped lang="scss">
.detail-layout { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-2xl); }
.detail-cover img { width: 100%; border-radius: var(--radius-md); }
.price { font-size: 1.5rem; font-weight: 700; color: var(--color-steel); }
.desc { color: var(--color-text-muted); line-height: 1.7; }
label { display: flex; flex-direction: column; gap: 0.375rem; margin: var(--space-md) 0; }
input { max-width: 8rem; padding: 0.5rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
@media (max-width: 768px) { .detail-layout { grid-template-columns: 1fr; } }
</style>
