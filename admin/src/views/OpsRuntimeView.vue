<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchOpsRuntime } from '../api'
import AdminPageHeader from '../components/AdminPageHeader.vue'
import { useAuthStore } from '../stores/auth'
import { formatBytes } from '../utils/formatOps'

const { t } = useI18n()
const auth = useAuthStore()
const isSuperAdmin = computed(() => auth.user?.role === 'super_admin')
const runtime = ref(null)
const errorText = ref('')
const loading = ref(false)

const statusLabel = (status) => t(`ops.status.${status || 'error'}`)

const loadRuntime = async () => {
  loading.value = true
  errorText.value = ''
  try {
    const res = await fetchOpsRuntime()
    runtime.value = res.data
  } catch (error) {
    errorText.value = error?.message || t('ops.loadFailed')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (isSuperAdmin.value) loadRuntime()
})
</script>

<template>
  <div v-if="!isSuperAdmin" class="forbidden">{{ t('ops.forbidden') }}</div>
  <div v-else>
    <AdminPageHeader :title="t('nav.opsRuntime')" :note="t('ops.scopeNote')" />
    <p v-if="loading" class="muted">{{ t('common.loading') }}</p>
    <p v-else-if="errorText" class="error">{{ errorText }}</p>
    <template v-else-if="runtime">
      <div class="stat-grid">
        <div class="stat-card">
          <span class="stat-num">{{ runtime.cpu?.percent ?? '—' }}%</span>
          <span class="stat-label">{{ t('ops.cpu') }}</span>
          <span class="stat-sub">{{ t('ops.load1m') }} {{ runtime.cpu?.load_1m ?? '—' }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ formatBytes(runtime.memory?.used_bytes) }}</span>
          <span class="stat-label">{{ t('ops.memory') }}</span>
          <span class="stat-sub">{{ t('ops.total') }} {{ formatBytes(runtime.memory?.total_bytes) }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ formatBytes(runtime.disk?.used_bytes) }}</span>
          <span class="stat-label">{{ t('ops.disk') }}</span>
          <span class="stat-sub">{{ t('ops.total') }} {{ formatBytes(runtime.disk?.total_bytes) }}</span>
        </div>
      </div>
      <div class="panel">
        <el-table :data="runtime.services" size="small">
          <el-table-column :label="t('ops.service')" min-width="160">
            <template #default="{ row }">{{ t(`ops.services.${row.key}`) }}</template>
          </el-table-column>
          <el-table-column :label="t('ops.health')" width="120">
            <template #default="{ row }">
              <span class="status" :class="row.status">{{ statusLabel(row.status) }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('ops.latency')" width="120">
            <template #default="{ row }">
              {{ row.latency_ms == null ? '—' : `${row.latency_ms} ms` }}
            </template>
          </el-table-column>
        </el-table>
      </div>
      <p v-if="!runtime.history?.length" class="muted block">{{ t('ops.noHistory') }}</p>
    </template>
  </div>
</template>

<style scoped>
.muted { color: #6b7280; }
.error, .forbidden { color: #b91c1c; }
.forbidden { padding: 1rem 0; }
.block { margin-top: 0.75rem; }
.status.ok { color: #047857; }
.status.error { color: #b91c1c; }
.status.disabled, .status.unknown { color: #6b7280; }
</style>
