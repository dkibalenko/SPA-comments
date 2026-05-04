<template>
  <section class="comment-list">

    <!-- Sorting controls -->
    <div class="sort-bar">
      <span>Sort by:</span>
      <button
        v-for="field in sortFields"
        :key="field.value"
        :class="{ active: isActive(field.value) }"
        @click="$emit('sort-change', field.value)"
      >
        {{ field.label }}
        <span v-if="isActive(field.value)">
          {{ ordering.startsWith('-') ? '↓' : '↑' }}
        </span>
      </button>
    </div>

    <!-- Comment table -->
    <div v-if="comments.length === 0" class="empty">
      No comments yet. Be the first!
    </div>

    <div v-else class="comments">
      <CommentItem
        v-for="comment in comments"
        :key="comment.id"
        :comment="comment"
        @reply="$emit('reply', $event)"
      />
    </div>

    <!-- Pagination -->
    <div class="pagination" v-if="totalPages > 1">
      <button
        :disabled="currentPage === 1"
        @click="$emit('page-change', currentPage - 1)"
      >← Prev</button>

      <span>Page {{ currentPage }} of {{ totalPages }}</span>

      <button
        :disabled="currentPage === totalPages"
        @click="$emit('page-change', currentPage + 1)"
      >Next →</button>
    </div>

  </section>
</template>

<script setup>
import { computed } from 'vue'
import CommentItem from './CommentItem.vue'

const props = defineProps({
  comments: { type: Array, default: () => [] },
  total:    { type: Number, default: 0 },
  page:     { type: Number, default: 1 },
  ordering: { type: String, default: '-created_at' },
})

defineEmits(['sort-change', 'page-change', 'reply'])

const PAGE_SIZE = 25
const currentPage = computed(() => props.page)
const totalPages  = computed(() => Math.ceil(props.total / PAGE_SIZE))

const sortFields = [
  { label: 'Username', value: 'username' },
  { label: 'Email',    value: 'email' },
  { label: 'Date',     value: 'date' },
]

function isActive(field) {
  return props.ordering === field || props.ordering === `-${field}`
}
</script>

<style scoped>
.comment-list { margin-top: 32px; }

.sort-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 0.9rem;
}
.sort-bar button {
  padding: 4px 10px;
  border: 1px solid #ccc;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
}
.sort-bar button.active {
  background: #333;
  color: #fff;
  border-color: #333;
}

.empty {
  text-align: center;
  padding: 40px;
  color: #888;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
}
.pagination button {
  padding: 6px 14px;
  border: 1px solid #ccc;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
}
.pagination button:disabled {
  opacity: 0.4;
  cursor: default;
}
</style>
