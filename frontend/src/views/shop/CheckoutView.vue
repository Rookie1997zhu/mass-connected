<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { createOrder } from '../../api'

const { t } = useI18n()
const router = useRouter()
const form = ref({ shipping_name: '', shipping_phone: '', shipping_address: '', remark: '' })
const error = ref('')

const submit = async () => {
  error.value = ''
  try {
    const res = await createOrder(form.value)
    router.push({ name: 'my-orders', query: { created: res.data.order_no } })
  } catch (e) {
    error.value = e.message || t('orders.createFailed')
  }
}
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ t('checkout.title') }}</h1>
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
.checkout-form { max-width: 32rem; padding: var(--space-xl); display: flex; flex-direction: column; gap: var(--space-md); label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.875rem; font-weight: 500; } input, textarea { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); } }
</style>
