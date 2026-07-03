<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { adjustUserPoints, fetchMembers, fetchUserPoints } from '../api'

const { t } = useI18n()
const items = ref([])
const search = ref('')
const loading = ref(false)
const adjustDialog = ref(false)
const adjustSubmitting = ref(false)
const selectedMember = ref(null)
const wallet = ref(null)
const transactions = ref([])
const adjustForm = ref({ amount: 0, description: '' })

const load = async () => {
  loading.value = true
  try {
    const res = await fetchMembers({ search: search.value || undefined })
    items.value = res.data.items || []
  } finally {
    loading.value = false
  }
}

onMounted(load)

const onSearch = async () => {
  await load()
}

const openAdjust = async (row) => {
  selectedMember.value = row
  adjustForm.value = { amount: 0, description: '' }
  adjustDialog.value = true
  const res = await fetchUserPoints(row.id)
  wallet.value = res.data.wallet
  transactions.value = res.data.transactions || []
}

const submitAdjust = async () => {
  if (!selectedMember.value || !adjustForm.value.amount) {
    ElMessage.warning(t('members.amountRequired'))
    return
  }
  adjustSubmitting.value = true
  try {
    await adjustUserPoints(selectedMember.value.id, {
      amount: adjustForm.value.amount,
      description: adjustForm.value.description || t('members.defaultAdjustReason'),
    })
    ElMessage.success(t('common.success'))
    adjustDialog.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message || 'error')
  } finally {
    adjustSubmitting.value = false
  }
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('nav.members') }}</h2>
      <div class="search-row">
        <el-input
          v-model="search"
          :placeholder="t('members.searchPlaceholder')"
          clearable
          style="width: 280px"
          @keyup.enter="onSearch"
        />
        <el-button type="primary" @click="onSearch">{{ t('common.search') }}</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="items">
      <el-table-column prop="email" :label="t('common.email')" min-width="200" />
      <el-table-column prop="name" :label="t('common.name')" width="140" />
      <el-table-column prop="member_type" :label="t('common.memberType')" width="120" />
      <el-table-column prop="point_balance" :label="t('common.balance')" width="120" />
      <el-table-column :label="t('common.registeredAt')" width="160">
        <template #default="{ row }">{{ (row.created_at || '').slice(0, 16).replace('T', ' ') }}</template>
      </el-table-column>
      <el-table-column :label="t('common.actions')" width="140" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="openAdjust(row)">{{ t('common.adjustPoints') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="adjustDialog"
      :title="t('common.adjustPoints')"
      width="560px"
      destroy-on-close
    >
      <template v-if="selectedMember">
        <p class="member-meta">{{ selectedMember.email }} · {{ t('common.balance') }}: {{ wallet?.balance ?? '—' }}</p>
        <el-form label-width="100px">
          <el-form-item :label="t('common.pointAmount')">
            <el-input-number v-model="adjustForm.amount" :step="100" />
            <span class="hint">{{ t('members.amountHint') }}</span>
          </el-form-item>
          <el-form-item :label="t('common.reason')">
            <el-input v-model="adjustForm.description" type="textarea" rows="2" />
          </el-form-item>
        </el-form>
        <h4>{{ t('common.transactions') }}</h4>
        <el-table :data="transactions" size="small" max-height="240">
          <el-table-column prop="created_at" :label="t('common.status')" width="150">
            <template #default="{ row }">{{ (row.created_at || '').slice(0, 16).replace('T', ' ') }}</template>
          </el-table-column>
          <el-table-column prop="type" label="Type" width="90" />
          <el-table-column prop="amount" :label="t('common.pointAmount')" width="100" />
          <el-table-column prop="balance_after" :label="t('common.balance')" width="100" />
          <el-table-column prop="description" :label="t('common.reason')" min-width="160" />
        </el-table>
      </template>
      <template #footer>
        <el-button @click="adjustDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="adjustSubmitting" @click="submitAdjust">{{ t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.search-row { display: flex; gap: 0.5rem; align-items: center; }
.member-meta { margin: 0 0 1rem; opacity: 0.75; font-size: 0.9rem; }
.hint { margin-left: 0.75rem; font-size: 0.8rem; opacity: 0.6; }
h4 { margin: 1rem 0 0.5rem; font-size: 0.95rem; }
</style>
