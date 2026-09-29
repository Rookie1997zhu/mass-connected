<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../components/PageShell.vue'
import { useAuthStore } from '../stores/auth'
import {
  blogCommentCreate,
  blogCommentDelete,
  blogLikeCreate,
  blogLikeDelete,
  fetchBlogComments,
  fetchBlogPost,
} from '../api'
import { sanitizeHtml } from '../utils/sanitize'

const { locale, t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const post = ref(null)
const comments = ref([])
const commentPage = ref({ page: 1, total_pages: 1 })
const draft = ref('')
const replyTo = ref(null)
const errorText = ref('')
const missing = ref(false)

const renderedContent = computed(() => sanitizeHtml(post.value?.content || ''))

const formatDate = (value) => {
  if (!value) return ''
  const map = { zh: 'zh-CN', ko: 'ko-KR', ja: 'ja-JP', en: 'en-US' }
  return new Date(value).toLocaleDateString(map[locale.value] || 'ko-KR')
}

const requireLogin = () => {
  router.push({ name: 'login', query: { redirect: route.fullPath } })
}

const loadComments = async (page = 1) => {
  const res = await fetchBlogComments(route.params.id, { page })
  comments.value = res.data.items || []
  commentPage.value = res.data.pagination || { page: 1, total_pages: 1 }
}

const load = async () => {
  missing.value = false
  errorText.value = ''
  post.value = null
  try {
    const res = await fetchBlogPost(route.params.id)
    post.value = res.data
    await loadComments(1)
  } catch {
    missing.value = true
  }
}

watch(() => route.params.id, load, { immediate: true })

const toggleLike = async () => {
  if (!auth.isLoggedIn) {
    requireLogin()
    return
  }
  try {
    const res = post.value.liked_by_me
      ? await blogLikeDelete(post.value.id)
      : await blogLikeCreate(post.value.id)
    post.value.liked_by_me = res.data.liked
    post.value.like_count = res.data.like_count
  } catch (error) {
    errorText.value = error?.message || t('blog.actionFailed')
  }
}

const submitComment = async () => {
  if (!auth.isLoggedIn) {
    requireLogin()
    return
  }
  const content = draft.value.trim()
  if (!content) return
  try {
    await blogCommentCreate(post.value.id, {
      content,
      parent: replyTo.value?.id || null,
    })
    draft.value = ''
    replyTo.value = null
    post.value.comment_count += 1
    await loadComments(commentPage.value.page || 1)
  } catch (error) {
    errorText.value = error?.message || t('blog.actionFailed')
  }
}

const removeComment = async (id) => {
  try {
    await blogCommentDelete(id)
    post.value.comment_count = Math.max(0, post.value.comment_count - 1)
    await loadComments(commentPage.value.page || 1)
  } catch (error) {
    errorText.value = error?.message || t('blog.actionFailed')
  }
}
</script>

<template>
  <PageShell>
    <p v-if="missing" class="muted">{{ t('blog.missing') }}</p>
    <article v-else-if="post" class="article">
      <RouterLink to="/blog" class="back">{{ t('blog.back') }}</RouterLink>
      <p class="meta">
        <RouterLink v-if="post.category" :to="{ name: 'blog', query: { category: post.category.slug } }">
          {{ post.category.name }}
        </RouterLink>
        <span>{{ post.author_name }}</span>
        <span>{{ formatDate(post.published_at) }}</span>
      </p>
      <h1>{{ post.title }}</h1>
      <p v-if="post.summary" class="lead">{{ post.summary }}</p>
      <img v-if="post.cover_image" class="cover" :src="post.cover_image" :alt="post.title" />
      <div class="rich-content" v-html="renderedContent" />

      <div v-if="post.tags?.length" class="tags">
        <RouterLink v-for="tag in post.tags" :key="tag" :to="{ name: 'blog', query: { tag } }">#{{ tag }}</RouterLink>
      </div>

      <button type="button" class="like" :class="{ on: post.liked_by_me }" @click="toggleLike">
        {{ post.liked_by_me ? t('blog.liked') : t('blog.like') }} · {{ post.like_count }}
      </button>

      <nav class="neighbors">
        <RouterLink v-if="post.previous" :to="`/blog/${post.previous.id}`">{{ t('blog.previousPost') }} {{ post.previous.title }}</RouterLink>
        <RouterLink v-if="post.next" :to="`/blog/${post.next.id}`">{{ t('blog.nextPost') }} {{ post.next.title }}</RouterLink>
      </nav>

      <section v-if="post.related?.length" class="related">
        <h2>{{ t('blog.related') }}</h2>
        <RouterLink v-for="item in post.related" :key="item.id" :to="`/blog/${item.id}`">{{ item.title }}</RouterLink>
      </section>

      <section class="comments">
        <h2>{{ t('blog.comments') }} {{ post.comment_count }}</h2>
        <p v-if="errorText" class="error">{{ errorText }}</p>
        <p v-if="replyTo" class="replying">
          {{ t('blog.replying', { name: replyTo.author_name }) }}
          <button type="button" @click="replyTo = null">{{ t('common.cancel') }}</button>
        </p>
        <form class="composer" @submit.prevent="submitComment">
          <textarea v-model="draft" rows="4" maxlength="1000" :placeholder="t('blog.commentPlaceholder')" />
          <button type="submit">{{ t('blog.submitComment') }}</button>
        </form>
        <p v-if="!comments.length" class="muted">{{ t('blog.commentEmpty') }}</p>
        <ul v-else>
          <li v-for="item in comments" :key="item.id" class="comment">
            <p class="who">
              <span>{{ item.author_name }}</span>
              <button type="button" @click="replyTo = item">{{ t('blog.reply') }}</button>
              <button v-if="item.is_mine" type="button" @click="removeComment(item.id)">{{ t('blog.deleteComment') }}</button>
            </p>
            <p class="body">{{ item.content }}</p>
            <ul v-if="item.replies?.length">
              <li v-for="reply in item.replies" :key="reply.id" class="comment nested">
                <p class="who">
                  <span>{{ reply.author_name }}</span>
                  <button v-if="reply.is_mine" type="button" @click="removeComment(reply.id)">{{ t('blog.deleteComment') }}</button>
                </p>
                <p class="body">{{ reply.content }}</p>
              </li>
            </ul>
          </li>
        </ul>
        <div v-if="commentPage.total_pages > 1" class="pager">
          <button type="button" :disabled="commentPage.page <= 1" @click="loadComments(commentPage.page - 1)">{{ t('blog.prev') }}</button>
          <span>{{ commentPage.page }} / {{ commentPage.total_pages }}</span>
          <button type="button" :disabled="commentPage.page >= commentPage.total_pages" @click="loadComments(commentPage.page + 1)">{{ t('blog.next') }}</button>
        </div>
      </section>
    </article>
  </PageShell>
</template>

<style scoped lang="scss">
.back { color: var(--color-steel); text-decoration: none; font-size: 0.875rem; }
.meta { color: var(--color-text-muted); display: flex; gap: 0.75rem; margin: 0.75rem 0; }
.meta a { color: var(--color-steel); text-decoration: none; }
h1 { font-size: clamp(1.75rem, 3vw, 2.4rem); margin-bottom: 0.75rem; }
.lead { color: var(--color-text); margin-bottom: var(--space-lg); }
.cover { width: 100%; border-radius: var(--radius-md); margin-bottom: var(--space-lg); }
.rich-content {
  line-height: 1.8;
  :deep(p) { margin: 0 0 1rem; }
  :deep(img) { max-width: 100%; border-radius: var(--radius-md); }
  :deep(a) { color: var(--color-steel); }
}
.tags { display: flex; gap: 0.5rem; flex-wrap: wrap; margin: var(--space-lg) 0; }
.tags a {
  text-decoration: none;
  color: var(--color-steel);
  background: var(--color-steel-muted);
  border-radius: 999px;
  padding: 0.15rem 0.6rem;
  font-size: 0.875rem;
}
.like {
  border: 1px solid var(--color-border-strong);
  background: var(--color-surface);
  border-radius: 999px;
  padding: 0.45rem 1rem;
  cursor: pointer;
}
.like.on { background: var(--color-steel); color: #fff; border-color: var(--color-steel); }
.neighbors, .related { display: flex; flex-direction: column; gap: 0.5rem; margin-top: var(--space-xl); }
.neighbors a, .related a { color: var(--color-steel); text-decoration: none; }
.comments { margin-top: var(--space-2xl); }
.composer { display: flex; flex-direction: column; gap: 0.5rem; margin: var(--space-md) 0; }
textarea {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 0.75rem;
  font: inherit;
}
.composer button, .pager button {
  align-self: flex-start;
  border: 0;
  background: var(--color-steel);
  color: #fff;
  border-radius: var(--radius-sm);
  padding: 0.45rem 0.9rem;
  cursor: pointer;
}
.pager { display: flex; gap: 0.75rem; align-items: center; }
.pager button { background: var(--color-surface); color: var(--color-text); border: 1px solid var(--color-border); }
.muted, .error { color: var(--color-text-muted); }
.error { color: #b42318; }
ul { list-style: none; padding: 0; margin: 0; }
.comment { padding: 0.75rem 0; border-top: 1px solid var(--color-border); }
.comment.nested { margin-left: 1.25rem; }
.who { display: flex; gap: 0.75rem; align-items: center; font-weight: 600; color: var(--color-text-heading); }
.who button { border: 0; background: transparent; color: var(--color-steel); cursor: pointer; font-weight: 500; }
.body { margin: 0.35rem 0 0; white-space: pre-wrap; }
</style>
