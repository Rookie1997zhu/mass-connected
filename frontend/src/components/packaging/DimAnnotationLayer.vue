<script setup>
import { computed, nextTick, ref } from 'vue'
import DOMPurify from 'dompurify'

const props = defineProps({
  annotations: { type: Array, required: true },
  viewBox: { type: String, required: true },
  unit: { type: String, required: true },
})

const emit = defineEmits(['update:field'])

const DIM_COLOR = '#2563eb'

const editingField = ref(null)
const draftValue = ref('')

const arrowMarkup = computed(() => {
  const defs = `<defs>
    <marker id="dim-arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${DIM_COLOR}" />
    </marker>
  </defs>`
  const arrows = props.annotations.map((ann) => ann.arrowSvg).join('')
  return DOMPurify.sanitize(`${defs}${arrows}`)
})

const inputDecimals = computed(() => (props.unit === 'in' ? 4 : 1))

function foreignObjectBox(ann) {
  return {
    x: ann.labelX - ann.labelWidth / 2,
    y: ann.labelY - ann.labelHeight / 2,
    width: ann.labelWidth,
    height: ann.labelHeight,
  }
}

function formatValue(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return ''
  return n.toFixed(inputDecimals.value)
}

function parseDraft(raw) {
  const normalized = String(raw).trim().replace(',', '.')
  if (!normalized) return NaN
  return Number(normalized)
}

async function startEdit(ann) {
  editingField.value = ann.field
  draftValue.value = formatValue(ann.displayValue)
  await nextTick()
  const el = document.querySelector(`[data-dim-field="${ann.field}"]`)
  if (el instanceof HTMLInputElement) {
    el.focus()
    el.select()
  }
}

function commitEdit(field) {
  const ann = props.annotations.find((item) => item.field === field)
  const value = parseDraft(draftValue.value)
  if (!Number.isFinite(value) || value <= 0) {
    if (ann) draftValue.value = formatValue(ann.displayValue)
    editingField.value = null
    return
  }
  emit('update:field', { field, value })
  editingField.value = null
}

function cancelEdit(field) {
  const ann = props.annotations.find((item) => item.field === field)
  if (ann) draftValue.value = formatValue(ann.displayValue)
  editingField.value = null
}

function onKeydown(field, event) {
  if (event.key === 'Enter') {
    event.preventDefault()
    commitEdit(field)
  } else if (event.key === 'Escape') {
    event.preventDefault()
    cancelEdit(field)
  }
}
</script>

<template>
  <svg
    class="dim-annotation-layer"
    xmlns="http://www.w3.org/2000/svg"
    :viewBox="viewBox"
    width="100%"
    height="100%"
    preserveAspectRatio="xMidYMid meet"
  >
    <g class="dim-arrows" v-html="arrowMarkup" />
    <foreignObject
      v-for="ann in annotations"
      :key="ann.field"
      :x="foreignObjectBox(ann).x"
      :y="foreignObjectBox(ann).y"
      :width="foreignObjectBox(ann).width"
      :height="foreignObjectBox(ann).height"
    >
      <div
        xmlns="http://www.w3.org/1999/xhtml"
        class="dim-input-wrap"
        :style="{ fontSize: `${ann.fontSize}px` }"
      >
        <button
          v-if="editingField !== ann.field"
          type="button"
          class="dim-value-btn"
          :aria-label="ann.field"
          @click="startEdit(ann)"
        >
          {{ formatValue(ann.displayValue) }}
        </button>
        <input
          v-else
          type="text"
          inputmode="decimal"
          class="dim-input"
          :data-dim-field="ann.field"
          :value="draftValue"
          :aria-label="ann.field"
          @input="draftValue = $event.target.value"
          @blur="commitEdit(ann.field)"
          @keydown="onKeydown(ann.field, $event)"
        />
        <span class="dim-unit">{{ unit }}</span>
      </div>
    </foreignObject>
  </svg>
</template>

<style scoped lang="scss">
.dim-annotation-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 3;
}

.dim-arrows {
  pointer-events: none;
}

.dim-input-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.12em;
  width: 100%;
  height: 100%;
  pointer-events: auto;
}

.dim-value-btn {
  min-width: 0;
  padding: 0 0.2em;
  font-size: inherit;
  font-weight: 600;
  font-family: inherit;
  color: #2563eb;
  text-align: center;
  border: none;
  border-radius: 2px;
  background: #f8fafc;
  cursor: text;
  outline: none;
  line-height: 1.2;

  &:hover {
    box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.35);
  }
}

.dim-input {
  min-width: 0;
  padding: 0 0.2em;
  font-size: inherit;
  font-weight: 600;
  font-family: inherit;
  color: #2563eb;
  text-align: center;
  border: 1px solid #2563eb;
  border-radius: 2px;
  background: #fff;
  outline: none;
  line-height: 1.2;
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.2);
}

.dim-unit {
  font-size: 0.82em;
  font-weight: 600;
  color: #2563eb;
  white-space: nowrap;
}
</style>
