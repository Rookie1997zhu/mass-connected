<script setup>
defineProps({
  title: { type: String, required: true },
  note: { type: String, default: '' },
})
</script>

<template>
  <div class="page-head">
    <div>
      <h2>{{ title }}</h2>
      <p v-if="note" class="note">{{ note }}</p>
    </div>
    <div class="actions">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
}
.note {
  margin: 0.35rem 0 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.5;
  max-width: 42rem;
}
.actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
}
</style>
