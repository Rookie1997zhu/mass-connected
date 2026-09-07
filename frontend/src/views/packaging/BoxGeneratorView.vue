<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import BoxParamForm from './BoxParamForm.vue'
import BoxPreviewPanel from './BoxPreviewPanel.vue'
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
  submitting,
  downloadBusy,
  pointsBalance,
  pointsCost,
  isUnlocked,
  isFixedAsset,

  templateLabel,
  selectedTemplate,
  canPurchase,
  hasBoxDims,

  previewError,
  preview,
  dimAnnotations,
  dimViewBox,
  previewLinesSvg,
  onDimFieldUpdate,

  goToLibrary,
  onUnlock,
  onDownload,
} = useBoxGenerator()

const boxName = computed(() => templateLabel(selectedTemplate.value, 'name'))

const unlockDisabled = computed(
  () => submitting.value || !canPurchase.value || isUnlocked.value || (!isFixedAsset.value && !hasBoxDims.value),
)
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
        :submit-disabled="unlockDisabled"
        :is-fixed-asset="isFixedAsset"
        :is-unlocked="isUnlocked"
        :points-cost="pointsCost"
        :points-balance="pointsBalance"
        :submitting="submitting"
        @change-box="goToLibrary"
        @submit="onUnlock"
      />

      <BoxPreviewPanel
        :box-code="boxCode"
        :unit="unit"
        :preview-error="previewError"
        :preview="preview"
        :dim-annotations="dimAnnotations"
        :dim-view-box="dimViewBox"
        :preview-lines-svg="previewLinesSvg"
        :is-unlocked="isUnlocked"
        :download-busy="downloadBusy"
        @dim-field-update="onDimFieldUpdate"
        @download="onDownload"
      />
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
  color: var(--color-text-muted);
}
</style>
