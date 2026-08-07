<script setup>
import { useI18n } from 'vue-i18n'
import { localizeNotificationTitle } from '../../../lib/notificationI18n'

defineProps({
  notifications: { type: Array, default: () => [] },
})

defineEmits(['mark-read', 'mark-all-read'])

const { t, te } = useI18n()
const titleOf = (n) => localizeNotificationTitle(n?.title, t, te)
</script>

<template>
  <div>
    <button type="button" class="btn btn-secondary btn-sm mb" @click="$emit('mark-all-read')">{{ t('mypage.markAllRead') }}</button>
    <p v-if="!notifications.length" class="page-empty">{{ t('mypage.empty') }}</p>
    <ul v-else class="notif-list">
      <li v-for="n in notifications" :key="n.id" :class="{ unread: !n.is_read }" @click="$emit('mark-read', n)">
        <strong>{{ titleOf(n) }}</strong>
        <p>{{ n.content }}</p>
        <span class="notif-time">{{ (n.created_at || '').slice(0, 16).replace('T', ' ') }}</span>
      </li>
    </ul>
  </div>
</template>

<style scoped lang="scss">
.mb { margin-bottom: var(--space-md); }
.notif-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-sm); li { border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-md); cursor: pointer; p { margin: 0.25rem 0; font-size: 0.875rem; opacity: 0.75; } } li.unread { border-left: 3px solid var(--color-steel); } }
.notif-time { font-size: 0.72rem; opacity: 0.55; }
</style>
