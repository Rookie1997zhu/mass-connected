export const emptyI18n = () => ({ ko: '', zh: '', en: '' })

export const normalizeI18n = (value) => ({
  ko: value?.ko || '',
  zh: value?.zh || '',
  en: value?.en || '',
})
