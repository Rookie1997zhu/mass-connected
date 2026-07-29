<script setup>
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { downloadAuthedFile } from '../../../utils/downloadAuthedFile'

defineProps({
  contracts: { type: Array, default: () => [] },
})

const { t } = useI18n()
</script>

<template>
  <div>
    <p v-if="!contracts.length" class="page-empty">{{ t('mypage.empty') }}</p>
    <table v-else class="data-table">
      <thead><tr><th>No.</th><th>{{ t('mypage.status') }}</th><th></th></tr></thead>
      <tbody>
        <tr v-for="c in contracts" :key="c.id">
          <td>{{ c.contract_no }}</td>
          <td>{{ c.status }}</td>
          <td class="actions-cell">
            <RouterLink
              v-if="c.rfq"
              :to="`/my/rfqs/${c.rfq}?tab=contract`"
              class="link"
            >
              {{ c.status === 'pending_sign' ? t('mypage.goSignContract') : t('fulfillment.viewDeal') }}
            </RouterLink>
            <button
              v-if="c.status === 'signed' && c.pdf_url"
              type="button"
              class="link"
              @click="downloadAuthedFile(c.pdf_url, 'contract.pdf')"
            >
              {{ t('mypage.viewSignedPdf') }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped lang="scss">
.data-table { width: 100%; border-collapse: collapse; th, td { text-align: left; padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border); font-size: 0.9rem; } th { font-size: 0.72rem; text-transform: uppercase; opacity: 0.6; } }
.link { color: var(--color-steel); cursor: pointer; }
</style>
