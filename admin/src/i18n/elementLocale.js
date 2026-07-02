import ko from 'element-plus/es/locale/lang/ko'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'

const elementLocales = { ko, zh: zhCn, en }

export function getElementLocale(locale) {
  return elementLocales[locale] || ko
}
