<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { confirmRecharge, fetchPointRules, fetchRecharges, savePointRule, updatePointRule } from '../api'

const { t } = useI18n()
const tab = ref('rules')
const rules = ref([])
const recharges = ref([])
const createDialog = ref(false)
const newRule = ref({
  rule_code: '',
  rule_name: '',
  rule_type: 'spend',
  point_amount: 0,
  enabled: true,
  description: '',
})

const loadRules = async () => {
  const res = await fetchPointRules()
  rules.value = res.data.items || []
}
const loadRecharges = async () => {
  const res = await fetchRecharges()
  recharges.value = res.data.items || []
}
onMounted(async () => {
  await loadRules()
  await loadRecharges()
})

const saveRule = async (row) => {
  await updatePointRule(row.id, { point_amount: row.point_amount, enabled: row.enabled })
  ElMessage.success(t('common.success'))
}

const openCreate = () => {
  newRule.value = {
    rule_code: '',
    rule_name: '',
    rule_type: 'spend',
    point_amount: 0,
    enabled: true,
    description: '',
  }
  createDialog.value = true
}

const submitCreate = async () => {
  if (!newRule.value.rule_code || !newRule.value.rule_name) {
    ElMessage.warning(t('points.ruleRequired'))
    return
  }
  await savePointRule(newRule.value)
  ElMessage.success(t('common.success'))
  createDialog.value = false
  await loadRules()
}

const onConfirm = async (row) => {
  await confirmRecharge(row.id)
  ElMessage.success(t('common.success'))
  await loadRecharges()
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('nav.points') }}</h2>
      <el-button v-if="tab === 'rules'" type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
    </div>
    <el-tabs v-model="tab">
      <el-tab-pane :label="t('common.ruleCode')" name="rules">
        <el-table :data="rules">
          <el-table-column prop="rule_code" :label="t('common.ruleCode')" />
          <el-table-column prop="rule_name" :label="t('common.ruleName')" />
          <el-table-column prop="rule_type" :label="t('points.ruleType')" width="100" />
          <el-table-column :label="t('common.pointAmount')" width="160">
            <template #default="{ row }"><el-input-number v-model="row.point_amount" :min="0" size="small" /></template>
          </el-table-column>
          <el-table-column :label="t('common.enabled')" width="90">
            <template #default="{ row }"><el-switch v-model="row.enabled" /></template>
          </el-table-column>
          <el-table-column :label="t('common.actions')" width="100">
            <template #default="{ row }"><el-button size="small" type="primary" @click="saveRule(row)">{{ t('common.save') }}</el-button></template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane :label="t('common.amount')" name="recharges">
        <el-table :data="recharges">
          <el-table-column prop="recharge_no" label="No" />
          <el-table-column prop="user_email" :label="t('common.email')" />
          <el-table-column prop="amount_krw" :label="t('common.amount')" />
          <el-table-column prop="point_amount" :label="t('common.pointAmount')" width="100" />
          <el-table-column prop="status" :label="t('common.status')" width="130" />
          <el-table-column :label="t('common.actions')" width="120">
            <template #default="{ row }">
              <el-button v-if="row.status !== 'confirmed'" size="small" type="primary" @click="onConfirm(row)">{{ t('common.confirm') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="createDialog" :title="t('points.createRule')" width="480px">
      <el-form label-width="120px">
        <el-form-item :label="t('common.ruleCode')"><el-input v-model="newRule.rule_code" /></el-form-item>
        <el-form-item :label="t('common.ruleName')"><el-input v-model="newRule.rule_name" /></el-form-item>
        <el-form-item :label="t('points.ruleType')">
          <el-select v-model="newRule.rule_type" style="width: 100%">
            <el-option value="earn" label="earn" />
            <el-option value="spend" label="spend" />
            <el-option value="recharge" label="recharge" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('common.pointAmount')"><el-input-number v-model="newRule.point_amount" :min="0" /></el-form-item>
        <el-form-item :label="t('common.enabled')"><el-switch v-model="newRule.enabled" /></el-form-item>
        <el-form-item :label="t('common.reason')"><el-input v-model="newRule.description" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitCreate">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
</style>
