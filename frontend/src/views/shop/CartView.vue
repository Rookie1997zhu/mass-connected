<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchCart, removeCartItem, updateCartItem } from '../../api'

const { t } = useI18n()
const items = ref([])
const total = ref(0)
const loading = ref(true)

const load = async () => {
  const res = await fetchCart()
  items.value = res.data.items || []
  total.value = res.data.total_amount || 0
}

onMounted(async () => {
  try {
    await load()
  } finally {
    loading.value = false
  }
})

const updateQty = async (item) => {
  await updateCartItem(item.id, { quantity: item.quantity })
  await load()
}

const remove = async (id) => {
  await removeCartItem(id)
  await load()
}
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ t('cart.title') }}</h1>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <p v-else-if="!items.length" class="page-empty">{{ t('cart.empty') }}</p>
    <template v-else>
      <table class="cart-table">
        <thead>
          <tr>
            <th>{{ t('shop.product') }}</th>
            <th>{{ t('shop.price') }}</th>
            <th>{{ t('shop.quantity') }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>{{ item.product_name }}</td>
            <td>KRW {{ Number(item.unit_price_amount).toLocaleString() }}</td>
            <td>
              <input v-model.number="item.quantity" type="number" min="1" @change="updateQty(item)" />
            </td>
            <td><button type="button" class="btn btn-sm btn-secondary" @click="remove(item.id)">{{ t('cart.remove') }}</button></td>
          </tr>
        </tbody>
      </table>
      <div class="cart-footer">
        <strong>{{ t('cart.total') }}: KRW {{ Number(total).toLocaleString() }}</strong>
        <RouterLink to="/shop/checkout" class="btn btn-primary">{{ t('cart.checkout') }}</RouterLink>
      </div>
    </template>
  </PageShell>
</template>

<style scoped lang="scss">
.cart-table { width: 100%; border-collapse: collapse; th, td { padding: 0.75rem; border-bottom: 1px solid var(--color-border); text-align: left; } input { width: 4rem; padding: 0.375rem; } }
.cart-footer { display: flex; justify-content: space-between; align-items: center; margin-top: var(--space-xl); }
</style>
