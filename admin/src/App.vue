<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElConfigProvider } from 'element-plus'
import { RouterView } from 'vue-router'
import { getElementLocale } from './i18n/elementLocale'

const { locale } = useI18n()
const elementLocale = computed(() => getElementLocale(locale.value))
</script>

<template>
  <ElConfigProvider :locale="elementLocale">
    <RouterView />
  </ElConfigProvider>
</template>

<style>
body {
  margin: 0;
  font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Noto Sans KR', 'Noto Sans SC', sans-serif;
  background: #f9fafb;
}
</style>
