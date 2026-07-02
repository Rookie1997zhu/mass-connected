<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { emptyI18n } from '../utils/i18nField'

const props = defineProps({
  modelValue: { type: Object, default: () => emptyI18n() },
  label: { type: String, default: '' },
  type: { type: String, default: 'input' },
  rows: { type: Number, default: 3 },
})

const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()

const value = computed({
  get: () => ({ ...emptyI18n(), ...props.modelValue }),
  set: (next) => emit('update:modelValue', next),
})

const updateField = (locale, fieldValue) => {
  value.value = { ...value.value, [locale]: fieldValue }
}

const locales = [
  { key: 'ko', label: t('lang.ko') },
  { key: 'zh', label: t('lang.zh') },
  { key: 'en', label: t('lang.en') },
]
</script>

<template>
  <div class="multi-lang-input">
    <div v-if="label" class="field-label">{{ label }}</div>
    <el-tabs type="border-card">
      <el-tab-pane v-for="item in locales" :key="item.key" :label="item.label">
        <el-input
          v-if="type === 'input'"
          :model-value="value[item.key]"
          @update:model-value="updateField(item.key, $event)"
        />
        <el-input
          v-else
          type="textarea"
          :rows="rows"
          :model-value="value[item.key]"
          @update:model-value="updateField(item.key, $event)"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.multi-lang-input { width: 100%; }
.field-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
}
</style>
