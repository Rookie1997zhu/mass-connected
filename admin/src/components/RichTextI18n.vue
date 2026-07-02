<script setup>
import '@wangeditor/editor/dist/css/style.css'
import { computed, onBeforeUnmount, shallowRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Editor, Toolbar } from '@wangeditor/editor-for-vue'
import { emptyI18n } from '../utils/i18nField'

const props = defineProps({
  modelValue: { type: Object, default: () => emptyI18n() },
  label: { type: String, default: '' },
  height: { type: String, default: '320px' },
})

const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()

const locales = [
  { key: 'ko', label: t('lang.ko') },
  { key: 'zh', label: t('lang.zh') },
  { key: 'en', label: t('lang.en') },
]

const activeLocale = shallowRef('ko')
const editorRefs = shallowRef({ ko: null, zh: null, en: null })

const value = computed({
  get: () => ({ ...emptyI18n(), ...props.modelValue }),
  set: (next) => emit('update:modelValue', next),
})

const toolbarConfig = {}
const editorConfig = { placeholder: t('common.editorPlaceholder') }

const handleCreated = (locale, editor) => {
  editorRefs.value = { ...editorRefs.value, [locale]: editor }
}

const updateField = (locale, html) => {
  value.value = { ...value.value, [locale]: html }
}

watch(
  () => props.modelValue,
  (next) => {
    locales.forEach(({ key }) => {
      const editor = editorRefs.value[key]
      if (!editor) return
      const html = next?.[key] || ''
      if (editor.getHtml() !== html) editor.setHtml(html)
    })
  },
  { deep: true }
)

onBeforeUnmount(() => {
  Object.values(editorRefs.value).forEach((editor) => {
    if (editor) editor.destroy()
  })
})
</script>

<template>
  <div class="rich-text-i18n">
    <div v-if="label" class="field-label">{{ label }}</div>
    <el-tabs v-model="activeLocale" type="border-card">
      <el-tab-pane v-for="item in locales" :key="item.key" :label="item.label" :name="item.key">
        <div class="editor-wrap">
          <Toolbar
            class="editor-toolbar"
            :editor="editorRefs[item.key]"
            :default-config="toolbarConfig"
            mode="default"
          />
          <Editor
            class="editor-body"
            :style="{ height }"
            :model-value="value[item.key]"
            :default-config="editorConfig"
            mode="default"
            @on-created="(editor) => handleCreated(item.key, editor)"
            @update:model-value="updateField(item.key, $event)"
          />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.rich-text-i18n { width: 100%; }
.field-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
}
.editor-wrap {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}
.editor-toolbar {
  border-bottom: 1px solid #dcdfe6;
}
.editor-body {
  overflow-y: hidden;
}
</style>
