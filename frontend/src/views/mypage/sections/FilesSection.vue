<script setup>
import { useI18n } from 'vue-i18n'

defineProps({
  files: { type: Array, default: () => [] },
})

const { t } = useI18n()
</script>

<template>
  <div>
    <p v-if="!files.length" class="page-empty">{{ t('mypage.empty') }}</p>
    <table v-else class="data-table">
      <thead><tr><th>{{ t('mypage.fileName') }}</th><th>{{ t('mypage.source') }}</th><th>{{ t('mypage.createdAt') }}</th><th></th></tr></thead>
      <tbody>
        <tr v-for="f in files" :key="`${f.source}-${f.id}`">
          <td>{{ f.file_name }}</td>
          <td>{{ f.source_no }}</td>
          <td>{{ (f.created_at || '').slice(0, 10) }}</td>
          <td><a :href="f.file_url" target="_blank" rel="noopener" class="link">{{ t('mypage.download') }}</a></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped lang="scss">
.data-table { width: 100%; border-collapse: collapse; th, td { text-align: left; padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border); font-size: 0.9rem; } th { font-size: 0.72rem; text-transform: uppercase; opacity: 0.6; } }
.link { color: var(--color-steel); cursor: pointer; }
</style>
