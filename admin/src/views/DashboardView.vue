<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<template>
  <div>
    <h2>{{ t('dashboard.title') }}</h2>
    <p>{{ t('dashboard.desc') }}</p>
  </div>
</template>
