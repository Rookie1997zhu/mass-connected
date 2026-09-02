<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { createOrder, fetchCart } from '../../api'
import { useLocaleCurrency } from '../../composables/useLocaleCurrency'
import { resolveApiMessage } from '../../utils/apiErrors'

const { t } = useI18n()
const { formatMoney } = useLocaleCurrency()
const router = useRouter()
const form = ref({ shipping_name: '', shipping_phone: '', shipping_address: '', remark: '' })
const cartItems = ref([])
const cartTotal = ref(0)
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetchCart()
    cartItems.value = res.data.items || []
    cartTotal.value = res.data.total_amount || cartItems.value.reduce(
      (sum, i) => sum + Number(i.line_total || i.unit_price * i.quantity || 0),
      0,
    )
  } finally {
    loading.value = false
  }
})

const submit = async () => {
  error.value = ''
  try {
    const res = await createOrder(form.value)
    router.push({ name: 'my-orders', query: { created: res.data.order_no } })
  } catch (e) {
    error.value = resolveApiMessage(e, t, 'orders.createFailed')
  }
}
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ t('checkout.title') }}</h1>
    <section v-if="!loading && cartItems.length" class="cart-summary card">
      <h2 class="section-sub">{{ t('cart.title') }}</h2>
      <ul class="cart-lines">
        <li v-for="item in cartItems" :key="item.id">
          <span>{{ item.product_name_text || item.product_name }}</span>
          <span>× {{ item.quantity }}</span>
          <span>{{ formatMoney({ amount: item.line_total || item.unit_price * item.quantity, currency: item.currency || 'KRW' }) }}</span>
        </li>
      </ul>
      <p class="cart-total">{{ t('cart.total') }}: {{ formatMoney({ amount: cartTotal, currency: 'KRW' }) }}</p>
    </section>
    <form class="checkout-form card" @submit.prevent="submit">
      <p v-if="error" class="page-message page-message--error">{{ error }}</p>
      <label>{{ t('checkout.name') }}<input v-model="form.shipping_name" required /></label>
      <label>{{ t('checkout.phone') }}<input v-model="form.shipping_phone" required /></label>
      <label>{{ t('checkout.address') }}<textarea v-model="form.shipping_address" rows="3" required /></label>
      <label>{{ t('checkout.remark') }}<textarea v-model="form.remark" rows="2" /></label>
      <button type="submit" class="btn btn-primary">{{ t('checkout.submit') }}</button>
    </form>
  </PageShell>
</template>

<style scoped lang="scss">
.cart-summary { max-width: 32rem; padding: var(--space-lg); margin-bottom: var(--space-lg); }
.section-sub { font-size: 1rem; margin: 0 0 var(--space-md); }
.cart-lines { list-style: none; padding: 0; margin: 0 0 var(--space-md); li { display: flex; justify-content: space-between; gap: 0.5rem; padding: 0.35rem 0; font-size: 0.9rem; border-bottom: 1px solid var(--color-border); } }
.cart-total { font-weight: 600; margin: 0; }
.checkout-form { max-width: 32rem; padding: var(--space-xl); display: flex; flex-direction: column; gap: var(--space-md); label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.875rem; font-weight: 500; } input, textarea { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); } }
</style>
