<script setup>
import { useI18n } from 'vue-i18n'

defineProps({
  todos: { type: Array, default: () => [] },
})

defineEmits(['toggle-todo'])

const { t } = useI18n()
const displayProjectTitle = (raw) => {
  const m = (raw || '').match(/^项目\s*(.+)$/)
  return m ? `${t('workflow.projectWord')} ${m[1]}` : raw
}
</script>

<template>
  <div>
    <p v-if="!todos.length" class="page-empty">{{ t('mypage.empty') }}</p>
    <ul v-else class="todo-list">
      <li v-for="td in todos" :key="td.id">
        <label>
          <input type="checkbox" :checked="td.is_done" @change="$emit('toggle-todo', td)" />
          <span :class="{ done: td.is_done }">{{ td.title }}</span>
        </label>
        <span class="todo-meta">{{ td.project_no }} · {{ displayProjectTitle(td.project_title) }}</span>
      </li>
    </ul>
  </div>
</template>

<style scoped lang="scss">
.todo-list { list-style: none; padding: 0; margin: 0; li { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0; border-bottom: 1px solid var(--color-border); label { display: flex; align-items: center; gap: 0.5rem; } .done { text-decoration: line-through; opacity: 0.5; } } }
.todo-meta { font-size: 0.75rem; opacity: 0.55; }
</style>
