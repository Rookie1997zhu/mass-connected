/** 默认 CNY→KRW 展示汇率（与后台 QuoteParam.rmb_to_krw 兜底一致） */
export const DEFAULT_RMB_TO_KRW = 190

export type MoneyInput = {
  amount?: number | null
  currency?: string | null
  totalKrw?: number | null
  rmbToKrw?: number | null
}

export type ResolvedMoney = {
  amount: number
  currency: 'CNY' | 'KRW'
}

/** 按页面语言决定展示币种：中文 CNY，韩文及其他默认 KRW */
export function displayCurrencyForLocale(locale: string): 'CNY' | 'KRW' {
  return locale === 'zh' ? 'CNY' : 'KRW'
}

export function resolveDisplayMoney(input: MoneyInput, locale: string): ResolvedMoney {
  const amount = Number(input.amount || 0)
  const sourceCurrency = (input.currency || 'KRW').toUpperCase()
  const rate = Number(input.rmbToKrw || DEFAULT_RMB_TO_KRW) || DEFAULT_RMB_TO_KRW
  const target = displayCurrencyForLocale(locale)

  if (target === 'CNY') {
    if (sourceCurrency === 'CNY') return { amount, currency: 'CNY' }
    return { amount: amount / rate, currency: 'CNY' }
  }

  if (sourceCurrency === 'CNY') {
    const krw = input.totalKrw != null && input.totalKrw !== ''
      ? Number(input.totalKrw)
      : Math.round(amount * rate)
    return { amount: krw, currency: 'KRW' }
  }
  return { amount, currency: 'KRW' }
}

export function formatLocaleMoney(
  input: MoneyInput,
  locale: string,
  digits = 0,
): ResolvedMoney & { formatted: string; text: string } {
  const resolved = resolveDisplayMoney(input, locale)
  const formatted = Number(resolved.amount || 0).toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits > 0 ? Math.min(digits, 4) : 0,
  })
  return {
    ...resolved,
    formatted,
    text: `${resolved.currency} ${formatted}`,
  }
}

/** 从简单报价 result 对象提取汇率 */
export function quoteResultRate(result: { rmb_to_krw?: number } | null | undefined) {
  return result?.rmb_to_krw ?? DEFAULT_RMB_TO_KRW
}
