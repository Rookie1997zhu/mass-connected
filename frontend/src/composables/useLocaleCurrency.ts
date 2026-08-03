import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  DEFAULT_RMB_TO_KRW,
  displayCurrencyForLocale,
  formatDualMoney,
  formatLocaleMoney,
  quoteResultRate,
  resolveDisplayMoney,
  type MoneyInput,
  type QuoteLineFx,
  type QuoteResultFx,
} from '../lib/localeCurrency'

export function useLocaleCurrency() {
  const { locale } = useI18n()

  const displayCurrency = computed(() => displayCurrencyForLocale(locale.value))

  const resolveMoney = (input: MoneyInput) => resolveDisplayMoney(input, locale.value)

  const formatMoney = (input: MoneyInput, digits = 0) =>
    formatLocaleMoney(input, locale.value, digits).text

  const formatMoneyParts = (input: MoneyInput, digits = 0) =>
    formatLocaleMoney(input, locale.value, digits)

  const dualMoney = (input: MoneyInput) => formatDualMoney(input, locale.value)

  const fromQuote = (
    amount: number | null | undefined,
    quote: { currency?: string; total_amount?: number; result?: QuoteResultFx } | null,
    digits = 0,
    line?: QuoteLineFx,
  ) => {
    const result = quote?.result
    const rate = quoteResultRate(result)
    const num = amount == null ? null : Number(amount)
    const isTotal =
      num != null &&
      (num === Number(quote?.total_amount) || num === Number(result?.total))

    return formatDualMoney(
      {
        amount: num,
        currency: quote?.currency,
        rmbToKrw: rate,
        amountCny: line?.amount_cny,
        amountKrw: line?.amount_krw,
        totalCny: isTotal ? result?.total_cny : undefined,
        totalKrw: isTotal ? result?.total_krw : undefined,
      },
      locale.value,
    )
  }

  const fromPreview = (
    amount: number | null | undefined,
    preview: {
      currency?: string
      rmb_to_krw?: number
      cny_to_krw?: number
      total_krw?: number
      total_cny?: number
      total?: number
      amount_cny?: number
      amount_krw?: number
    } | null,
    digits = 0,
  ) => {
    const rate = preview?.rmb_to_krw ?? preview?.cny_to_krw ?? DEFAULT_RMB_TO_KRW
    const num = amount == null ? null : Number(amount)
    const isTotal = num != null && num === Number(preview?.total)
    return formatDualMoney(
      {
        amount: num,
        currency: preview?.currency,
        rmbToKrw: rate,
        amountCny: preview?.amount_cny,
        amountKrw: preview?.amount_krw,
        totalCny: isTotal ? preview?.total_cny : undefined,
        totalKrw: isTotal ? preview?.total_krw : undefined,
      },
      locale.value,
    )
  }

  return {
    displayCurrency,
    resolveMoney,
    formatMoney,
    formatMoneyParts,
    dualMoney,
    formatDualMoney: dualMoney,
    fromQuote,
    fromPreview,
    quoteResultRate,
  }
}
