<script setup>
import { useI18n } from 'vue-i18n'

defineProps({
  boxCode: { type: String, default: '' },
  boxName: { type: String, default: '' },
  error: { type: String, default: '' },
  submitDisabled: { type: Boolean, default: false },
  isFixedAsset: { type: Boolean, default: false },
  isUnlocked: { type: Boolean, default: false },
  pointsCost: { type: Number, default: 0 },
  pointsBalance: { type: [Number, null], default: null },
  submitting: { type: Boolean, default: false },
})

const emit = defineEmits(['change-box', 'submit'])

const { t } = useI18n()

const productName = defineModel('productName', { type: String, default: '' })
const unit = defineModel('unit', { type: String, default: 'mm' })
const dimensionType = defineModel('dimensionType', { type: String, default: 'internal' })
const boardType = defineModel('boardType', { type: String, default: 'E' })
const length = defineModel('length', { default: '' })
const width = defineModel('width', { default: '' })
const height = defineModel('height', { default: '' })
const thickness = defineModel('thickness', { default: '' })
const quantity = defineModel('quantity', { default: '' })
const printColors = defineModel('printColors', { default: '' })

const onSubmit = () => emit('submit')
</script>

<template>
  <section class="pkg-form card">
    <div class="pkg-form-head">
      <div>
        <h2>{{ t('packaging.editParams') }}</h2>
        <p class="pkg-selected-box">
          <span class="pkg-box-code">FEFCO {{ boxCode }}</span>
          <span class="pkg-box-name">{{ boxName }}</span>
        </p>
      </div>
      <button type="button" class="btn btn-secondary btn-sm" @click="emit('change-box')">{{ t('packaging.changeBox') }}</button>
    </div>

    <div class="pkg-form-fields">
      <label>{{ t('packaging.productName') }}
        <input v-model="productName" type="text" />
      </label>

      <div class="pkg-row">
        <label>{{ t('packaging.unit') }}
          <select v-model="unit">
            <option value="mm">{{ t('packaging.unitMm') }}</option>
            <option value="in">{{ t('packaging.unitIn') }}</option>
          </select>
        </label>
        <label>{{ t('packaging.thickness') }}
          <input v-model.number="thickness" type="number" min="0.1" step="0.1" :placeholder="t('packaging.dimPlaceholder')" />
        </label>
      </div>

      <div v-if="!isFixedAsset" class="pkg-dim-type">
        <span class="pkg-dim-label">{{ t('packaging.dimensionType') }}</span>
        <div class="pkg-dim-chips">
          <button
            type="button"
            class="pkg-dim-chip"
            :class="{ active: dimensionType === 'internal' }"
            @click="dimensionType = 'internal'"
          >
            {{ t('packaging.dimInternal') }}
          </button>
          <button
            type="button"
            class="pkg-dim-chip"
            :class="{ active: dimensionType === 'external' }"
            @click="dimensionType = 'external'"
          >
            {{ t('packaging.dimExternal') }}
          </button>
          <button
            type="button"
            class="pkg-dim-chip"
            :class="{ active: dimensionType === 'manufacturing' }"
            @click="dimensionType = 'manufacturing'"
          >
            {{ t('packaging.dimManufacturing') }}
          </button>
        </div>
      </div>

      <template v-if="!isFixedAsset">
        <div class="pkg-row">
          <label>{{ t('packaging.length') }}<input v-model.number="length" type="number" min="1" step="0.1" :placeholder="t('packaging.dimPlaceholder')" /></label>
          <label>{{ t('packaging.width') }}<input v-model.number="width" type="number" min="1" step="0.1" :placeholder="t('packaging.dimPlaceholder')" /></label>
        </div>
        <label>{{ t('packaging.height') }}<input v-model.number="height" type="number" min="1" step="0.1" :placeholder="t('packaging.dimPlaceholder')" /></label>
      </template>
      <p v-else class="pkg-fixed-hint">{{ t('packaging.fixedAssetDimsHint') }}</p>

      <label>{{ t('packaging.boardType') }}
        <select v-model="boardType">
          <option value="E">{{ t('packaging.boardE') }}</option>
          <option value="B">{{ t('packaging.boardB') }}</option>
          <option value="C">{{ t('packaging.boardC') }}</option>
          <option value="白卡">{{ t('packaging.boardWhite') }}</option>
        </select>
      </label>

      <p class="pkg-points-row">
        <span>{{ t('packaging.pointsCost', { n: pointsCost }) }}</span>
        <span v-if="pointsBalance != null">{{ t('packaging.pointsBalance', { n: pointsBalance }) }}</span>
      </p>
      <p v-if="isUnlocked" class="pkg-unlocked">{{ t('packaging.alreadyUnlocked') }}</p>

      <p v-if="error" class="page-message page-message--error">{{ error }}</p>
      <button type="button" class="btn btn-primary" :disabled="submitDisabled" @click="onSubmit">
        {{ submitting ? t('packaging.unlocking') : (isUnlocked ? t('packaging.alreadyUnlocked') : t('packaging.unlock')) }}
      </button>
    </div>
  </section>
</template>

<style scoped lang="scss">
.card {
  padding: var(--space-xl);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.pkg-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  position: sticky;
  top: calc(var(--header-height) + 1rem);
  align-self: start;
  max-height: calc(100vh - var(--header-height) - 2rem);
  overflow: hidden;
  min-width: 0;

  h2 {
    margin: 0;
    font-size: 1rem;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-size: 0.8125rem;
  }

  select,
  input {
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
    padding: 0.45rem 0.5rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
  }

  .btn {
    width: 100%;
  }
}

.pkg-form-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-sm);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--color-border);
}

.pkg-selected-box {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin: 0.35rem 0 0;
  font-size: 0.85rem;
}

.pkg-box-code {
  flex-shrink: 0;
  font-size: 0.68rem;
  font-weight: 700;
  color: var(--color-primary, #2563eb);
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  background: rgba(37, 99, 235, 0.08);
}

.pkg-box-name {
  font-weight: 600;
}

.pkg-fixed-hint,
.pkg-points-row,
.pkg-unlocked {
  margin: 0;
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.pkg-points-row {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.pkg-unlocked {
  color: #15803d;
}

.pkg-form-fields {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  overflow-y: auto;
  padding-right: 0.15rem;
}

.pkg-dim-type {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.pkg-dim-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-heading);
}

.pkg-dim-chips {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.pkg-dim-chip {
  width: 100%;
  padding: 0.35rem 0.45rem;
  font-size: 0.72rem;
  line-height: 1.2;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg, #fff);
  color: var(--color-text);
  cursor: pointer;
  text-align: center;

  &.active {
    border-color: var(--color-primary, #2563eb);
    color: var(--color-primary, #2563eb);
    font-weight: 600;
    background: rgba(37, 99, 235, 0.08);
    box-shadow: 0 0 0 1px var(--color-primary, #2563eb);
  }
}

.pkg-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-sm);
}

@media (max-width: 960px) {
  .pkg-form {
    position: static;
    max-height: none;
  }

  .pkg-dim-chips {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .pkg-dim-chip {
    flex: 1 1 calc(33% - 0.3rem);
    width: auto;
  }
}
</style>
