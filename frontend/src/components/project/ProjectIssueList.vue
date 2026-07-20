<script setup>
import { useI18n } from 'vue-i18n'
import TextTranslateBlock from '../TextTranslateBlock.vue'

defineProps({
  issues: { type: Array, default: () => [] },
  projectId: { type: [Number, String], required: true },
  role: { type: String, required: true },
})

const { t, te } = useI18n()

const trOr = (key, fallback) => (te(key) ? t(key) : fallback)
const issueSeverityLabel = (v) => trOr(`workflow.issueSeverity.${v}`, v)
const issueStatusLabel = (v) => trOr(`workflow.issueStatus.${v}`, v)
</script>

<template>
  <ul class="issue-list">
    <li v-for="issue in issues" :key="issue.id">
      <div class="issue-head">
        <strong class="issue-title">{{ issue.title }}</strong>
        <div class="issue-badges">
          <span class="badge badge--severity" :class="`badge--severity-${issue.severity}`">
            {{ issueSeverityLabel(issue.severity) }}
          </span>
          <span class="badge badge--status" :class="`badge--status-${issue.status}`">
            {{ issueStatusLabel(issue.status) }}
          </span>
        </div>
      </div>
      <p v-if="issue.description" class="issue-desc">{{ issue.description }}</p>
      <TextTranslateBlock
        :project-id="projectId"
        :role="role"
        :text="[issue.title, issue.description].filter(Boolean).join('\n')"
      />
    </li>
  </ul>
</template>

<style scoped lang="scss">
.issue-list {
  list-style: none;
  padding: 0;
  margin: 0;

  li {
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--color-border);

    &:first-child {
      padding-top: 0;
    }

    &:last-child {
      border-bottom: none;
      padding-bottom: 0;
    }
  }
}

.issue-head {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.issue-title {
  font-size: 0.88rem;
  line-height: 1.4;
}

.issue-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.badge {
  font-size: 0.68rem;
  padding: 0.12rem 0.45rem;
  border-radius: 999px;
  font-weight: 600;
}

.badge--severity-low {
  background: #ecfdf5;
  color: #047857;
}

.badge--severity-medium {
  background: #fffbeb;
  color: #b45309;
}

.badge--severity-high {
  background: #fef2f2;
  color: #b91c1c;
}

.badge--status-open {
  background: #eff6ff;
  color: #1d4ed8;
}

.badge--status-resolved {
  background: #f0fdf4;
  color: #15803d;
}

.issue-desc {
  margin: 0.35rem 0 0;
  font-size: 0.85rem;
  opacity: 0.8;
  line-height: 1.45;
}
</style>
