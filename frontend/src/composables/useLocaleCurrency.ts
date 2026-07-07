import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  DEFAULT_RMB_TO_KRW,
  displayCurrencyForLocale,
  formatLocaleMoney,
  quoteResultRate,
  resolveDisplayMoney,
  type MoneyInput,
} from '../lib/localeCurrency'

export function useLocaleCurrency() {
  const { locale } = useI18n()

  const displayCurrency = computed(() => displayCurrencyForLocale(locale.value))

  const resolveMoney = (input: MoneyInput) => resolveDisplayMoney(input, locale.value)

  const formatMoney = (input: MoneyInput, digits = 0) =>
    formatLocaleMoney(input, locale.value, digits).text

  const formatMoneyParts = (input: MoneyInput, digits = 0) =>
    formatLocaleMoney(input, locale.value, digits)

  const fromQuote = (
    amount: number | null | undefined,
    quote: { currency?: string; result?: { rmb_to_krw?: number; total_krw?: number } | null } | null,
    digits = 0,
  ) => formatMoney(
    {
      amount,
      currency: quote?.currency,
      totalKrw: quote?.result?.total_krw,
      rmbToKrw: quoteResultRate(quote?.result),
    },
    digits,
  )

  const fromPreview = (
    amount: number | null | undefined,
    preview: { currency?: string; rmb_to_krw?: number; total_krw?: number } | null,
    digits = 0,
  ) => formatMoney(
    {
      amount,
      currency: preview?.currency,
      rmbToKrw: preview?.rmb_to_krw ?? DEFAULT_RMB_TO_KRW,
    },
    digits,
  )

  return {
    displayCurrency,
    resolveMoney,
    formatMoney,
    formatMoneyParts,
    fromQuote,
    fromPreview,
    quoteResultRate,
  }
}
