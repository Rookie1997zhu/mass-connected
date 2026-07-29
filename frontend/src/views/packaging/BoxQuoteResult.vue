<script setup>
import { useI18n } from 'vue-i18n'
import { useLocaleCurrency } from '../../composables/useLocaleCurrency'

defineProps({
  result: { type: Object, required: true },
})

const emit = defineEmits(['convert'])

const { t } = useI18n()
const { fromQuote } = useLocaleCurrency()
</script>

<template>
  <section class="pkg-result card">
    <h2>{{ t('simpleQuote.result') }}</h2>
    <p class="pkg-no">{{ result.quote_no }}</p>
    <ul class="pkg-breakdown">
      <li v-for="(item, i) in result.result?.breakdown || []" :key="i">
        <span>{{ item.label }}</span><span>{{ fromQuote(item.amount, result) }}</span>
      </li>
    </ul>
    <p class="pkg-total">{{ t('simpleQuote.total') }}: <strong>{{ fromQuote(result.total_amount, result) }}</strong></p>
    <p class="pkg-meta">{{ t('packaging.area') }}: {{ result.result?.unfold_area_m2 }} m²</p>
    <div class="pkg-actions">
      <a v-if="result.pdf_url" :href="result.pdf_url" target="_blank" rel="noopener" class="btn btn-secondary btn-sm">PDF</a>
      <button v-if="!result.converted_rfq" type="button" class="btn btn-primary btn-sm" @click="emit('convert')">{{ t('packaging.convert') }}</button>
    </div>
  </section>
</template>

<style scoped lang="scss">
.card {
  padding: var(--space-xl);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.pkg-result {
  grid-column: 1 / -1;
}

.pkg-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.pkg-breakdown {
  list-style: none;
  padding: 0;
  margin: 0;

  li {
    display: flex;
    justify-content: space-between;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--color-border);
    font-size: 0.9rem;
  }
}

.pkg-no {
  font-size: 0.85rem;
  opacity: 0.6;
  margin: 0;
}

.pkg-total {
  font-size: 1.1rem;
  margin-top: var(--space-sm);
}

.pkg-meta {
  font-size: 0.9rem;
  color: var(--color-text-muted);
  margin: 0;
}
</style>
