/** 默认 CNY→KRW 展示汇率（与后台 QuoteParam.rmb_to_krw / FALLBACK 兜底一致） */
export const DEFAULT_RMB_TO_KRW = 190

export type MoneyInput = {
  amount?: number | null
  currency?: string | null
  totalKrw?: number | null
  totalCny?: number | null
  rmbToKrw?: number | null
  amountCny?: number | null
  amountKrw?: number | null
}

export type ResolvedMoney = {
  amount: number
  currency: 'CNY' | 'KRW'
}

export type QuoteResultFx = {
  rmb_to_krw?: number
  cny_to_krw?: number
  total_cny?: number
  total_krw?: number
  total?: number
} | null | undefined

export type QuoteLineFx = {
  amount_cny?: number | null
  amount_krw?: number | null
} | null | undefined

/** 按页面语言决定展示币种：中文 CNY，韩文及其他默认 KRW（单币路径仍可用） */
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
    if (input.totalCny != null) {
      return { amount: Number(input.totalCny), currency: 'CNY' }
    }
    return { amount: amount / rate, currency: 'CNY' }
  }

  if (sourceCurrency === 'CNY') {
    const krw = input.totalKrw != null ? Number(input.totalKrw) : Math.round(amount * rate)
    return { amount: krw, currency: 'KRW' }
  }
  return { amount, currency: 'KRW' }
}

function formatNumber(amount: number, digits: number, locale?: string): string {
  return Number(amount || 0).toLocaleString(locale || undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits > 0 ? Math.min(digits, 4) : 0,
  })
}

export function formatLocaleMoney(
  input: MoneyInput,
  locale: string,
  digits = 0,
): ResolvedMoney & { formatted: string; text: string } {
  const resolved = resolveDisplayMoney(input, locale)
  const formatted = formatNumber(resolved.amount, digits, locale)
  return {
    ...resolved,
    formatted,
    text: `${resolved.currency} ${formatted}`,
  }
}

/** 始终并列 CNY + KRW；locale 仅影响数字千分位等格式 */
export function formatDualMoney(input: MoneyInput, locale?: string): string {
  const rate = Number(input.rmbToKrw || DEFAULT_RMB_TO_KRW) || DEFAULT_RMB_TO_KRW
  const sourceCurrency = (input.currency || 'KRW').toUpperCase()
  const amount = Number(input.amount || 0)

  let cny: number
  let krw: number

  if (input.amountCny != null && input.amountKrw != null) {
    cny = Number(input.amountCny)
    krw = Number(input.amountKrw)
  } else if (input.totalCny != null && input.totalKrw != null) {
    cny = Number(input.totalCny)
    krw = Number(input.totalKrw)
  } else if (sourceCurrency === 'CNY') {
    cny = amount
    krw = input.totalKrw != null ? Number(input.totalKrw) : Math.round(amount * rate)
  } else {
    krw = amount
    cny = input.totalCny != null ? Number(input.totalCny) : Math.round((amount / rate) * 100) / 100
  }

  const cnyText = formatNumber(cny, 2, locale)
  const krwText = formatNumber(krw, 0, locale)
  return `CNY ${cnyText} / KRW ${krwText}`
}

/** 从简单报价 result 对象提取汇率 */
export function quoteResultRate(result: QuoteResultFx) {
  return result?.rmb_to_krw ?? result?.cny_to_krw ?? DEFAULT_RMB_TO_KRW
}
