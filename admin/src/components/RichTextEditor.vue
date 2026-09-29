<script setup>
import '@wangeditor/editor/dist/css/style.css'
import { onBeforeUnmount, shallowRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { Editor, Toolbar } from '@wangeditor/editor-for-vue'
import { ElMessage } from 'element-plus'
import { uploadAdminMedia } from '../api'

const props = defineProps({
  modelValue: { type: String, default: '' },
  height: { type: String, default: '360px' },
})

const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()
const editorRef = shallowRef(null)

const toolbarConfig = {}
const editorConfig = {
  placeholder: t('common.editorPlaceholder'),
  MENU_CONF: {
    uploadImage: {
      async customUpload(file, insertFn) {
        const form = new FormData()
        form.append('file', file)
        try {
          const res = await uploadAdminMedia(form)
          const url = res.data?.url
          if (!url) throw new Error(t('blog.uploadFailed'))
          insertFn(url, file.name, url)
        } catch (error) {
          ElMessage.error(error?.message || t('blog.uploadFailed'))
        }
      },
    },
  },
}

const handleCreated = (editor) => {
  editorRef.value = editor
}

onBeforeUnmount(() => {
  editorRef.value?.destroy()
})
</script>

<template>
  <div class="editor-wrap">
    <Toolbar class="editor-toolbar" :editor="editorRef" :default-config="toolbarConfig" mode="default" />
    <Editor
      class="editor-body"
      :style="{ height }"
      :model-value="props.modelValue"
      :default-config="editorConfig"
      mode="default"
      @on-created="handleCreated"
      @update:model-value="emit('update:modelValue', $event)"
    />
  </div>
</template>

<style scoped>
.editor-wrap {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
  width: 100%;
}
.editor-toolbar { border-bottom: 1px solid #dcdfe6; }
.editor-body { overflow-y: hidden; }
</style>
