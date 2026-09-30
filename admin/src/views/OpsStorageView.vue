<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchOpsStorage } from '../api'
import AdminPageHeader from '../components/AdminPageHeader.vue'
import { useAuthStore } from '../stores/auth'
import { formatBytes, formatTime } from '../utils/formatOps'

const { t } = useI18n()
const auth = useAuthStore()
const isSuperAdmin = computed(() => auth.user?.role === 'super_admin')
const storage = ref(null)
const errorText = ref('')
const loading = ref(false)
const recounting = ref(false)
const page = ref(1)
const pageSize = 20

const loadStorage = async (recount = false) => {
  if (recount) recounting.value = true
  else loading.value = true
  errorText.value = ''
  try {
    const res = await fetchOpsStorage({
      recount: recount ? 1 : 0,
      page: page.value,
      page_size: pageSize,
    })
    storage.value = res.data
  } catch (error) {
    errorText.value = error?.message || t('ops.loadFailed')
  } finally {
    loading.value = false
    recounting.value = false
  }
}

const onRecount = () => {
  page.value = 1
  loadStorage(true)
}

const onPage = (next) => {
  page.value = next
  loadStorage(false)
}

onMounted(() => {
  if (isSuperAdmin.value) loadStorage(false)
})
</script>

<template>
  <div v-if="!isSuperAdmin" class="forbidden">{{ t('ops.forbidden') }}</div>
  <div v-else>
    <AdminPageHeader :title="t('nav.opsStorage')" :note="t('ops.storageNote')">
      <el-button type="primary" :loading="recounting" @click="onRecount">
        {{ t('ops.recount') }}
      </el-button>
    </AdminPageHeader>
    <p v-if="loading" class="muted">{{ t('common.loading') }}</p>
    <p v-else-if="errorText" class="error">{{ errorText }}</p>
    <template v-else-if="storage">
      <p v-if="!storage.cached" class="muted">{{ t('ops.storageEmpty') }}</p>
      <template v-else>
        <p class="muted">{{ t('ops.countedAt') }} {{ formatTime(storage.counted_at) }}</p>
        <div class="stat-grid">
          <div class="stat-card">
            <span class="stat-num">{{ formatBytes(storage.local?.bytes) }}</span>
            <span class="stat-label">{{ t('ops.localSize') }}</span>
            <span class="stat-sub">{{ storage.local?.file_count ?? 0 }} {{ t('ops.files') }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-num">
              {{ storage.oss?.status === 'disabled' ? t('ops.status.disabled') : formatBytes(storage.oss?.bytes) }}
            </span>
            <span class="stat-label">{{ t('ops.ossSize') }}</span>
            <span class="stat-sub">
              <template v-if="storage.oss?.status === 'disabled'">{{ t('ops.ossOff') }}</template>
              <template v-else-if="storage.oss?.status === 'error'">{{ t('ops.status.error') }}</template>
              <template v-else>{{ storage.oss?.file_count ?? 0 }} {{ t('ops.files') }}</template>
            </span>
          </div>
        </div>
      </template>
      <h3>{{ t('ops.orphans') }}</h3>
      <p class="muted">{{ t('ops.orphanHint') }}</p>
      <div class="panel">
        <el-table :data="storage.orphans?.items || []" size="small">
          <el-table-column prop="key" :label="t('ops.fileKey')" min-width="240" />
          <el-table-column :label="t('ops.location')" width="120">
            <template #default="{ row }">{{ t(`ops.places.${row.location}`) }}</template>
          </el-table-column>
          <el-table-column :label="t('ops.size')" width="120">
            <template #default="{ row }">{{ formatBytes(row.bytes) }}</template>
          </el-table-column>
          <el-table-column :label="t('ops.modifiedAt')" width="180">
            <template #default="{ row }">{{ formatTime(row.modified_at) }}</template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-if="storage.orphans?.total > pageSize"
          class="pager"
          layout="prev, pager, next"
          :page-size="pageSize"
          :total="storage.orphans.total"
          :current-page="page"
          @current-change="onPage"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.muted { color: #6b7280; }
.error, .forbidden { color: #b91c1c; }
.forbidden { padding: 1rem 0; }
h3 { margin: 1.5rem 0 0.35rem; font-size: 15px; }
.pager { margin-top: 0.75rem; }
</style>
