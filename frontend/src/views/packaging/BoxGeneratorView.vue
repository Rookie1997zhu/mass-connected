<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import BoxParamForm from './BoxParamForm.vue'
import BoxPreviewPanel from './BoxPreviewPanel.vue'
import BoxQuoteResult from './BoxQuoteResult.vue'
import { useBoxGenerator } from './useBoxGenerator'

const { t } = useI18n()

const {
  catalogLoading,
  catalogError,

  productName,
  unit,
  dimensionType,
  boardType,
  boxCode,
  length,
  width,
  height,
  thickness,
  quantity,
  printColors,

  error,
  result,
  submitting,

  templateLabel,
  selectedTemplate,
  canQuote,
  hasBoxDims,

  previewError,
  preview,
  dimAnnotations,
  dimViewBox,
  previewLinesSvg,
  onDimFieldUpdate,

  goToLibrary,
  onGenerate,
  onConvert,
} = useBoxGenerator()

const boxName = computed(() => templateLabel(selectedTemplate.value, 'name'))

const submitDisabled = computed(() => submitting.value || !preview.value || !canQuote.value || !hasBoxDims.value)

const productionAssetUrl = computed(() => selectedTemplate.value?.productionAssetUrl || '')
</script>

<template>
  <PageShell container-wide :title="t('packaging.title')" :subtitle="t('packaging.editorPageDesc')">
    <p v-if="catalogLoading" class="pkg-lib-status">{{ t('packaging.catalogLoading') }}</p>
    <p v-else-if="catalogError" class="page-message page-message--error">{{ catalogError }}</p>

    <div v-else-if="!boxCode" class="pkg-no-box card">
      <p>{{ t('packaging.noBoxSelected') }}</p>
      <button type="button" class="btn btn-primary" @click="goToLibrary">{{ t('packaging.backToLibrary') }}</button>
    </div>

    <div v-else class="pkg-layout">
      <BoxParamForm
        v-model:product-name="productName"
        v-model:unit="unit"
        v-model:dimension-type="dimensionType"
        v-model:board-type="boardType"
        v-model:length="length"
        v-model:width="width"
        v-model:height="height"
        v-model:thickness="thickness"
        v-model:quantity="quantity"
        v-model:print-colors="printColors"
        :box-code="boxCode"
        :box-name="boxName"
        :error="error"
        :submit-disabled="submitDisabled"
        @change-box="goToLibrary"
        @submit="onGenerate"
      />

      <BoxPreviewPanel
        :box-code="boxCode"
        :unit="unit"
        :preview-error="previewError"
        :preview="preview"
        :dim-annotations="dimAnnotations"
        :dim-view-box="dimViewBox"
        :preview-lines-svg="previewLinesSvg"
        :production-asset-url="productionAssetUrl"
        @dim-field-update="onDimFieldUpdate"
      />

      <BoxQuoteResult v-if="result" :result="result" @convert="onConvert" />
    </div>
  </PageShell>
</template>

<style scoped lang="scss">
.pkg-layout {
  display: grid;
  grid-template-columns: clamp(260px, 24vw, 320px) minmax(0, 1fr);
  gap: var(--space-lg);
  align-items: stretch;
}

.card {
  padding: var(--space-xl);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.pkg-no-box {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-md);
}

.pkg-lib-status {
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

@media (max-width: 960px) {
  .pkg-layout {
    grid-template-columns: 1fr;
  }
}
</style>
