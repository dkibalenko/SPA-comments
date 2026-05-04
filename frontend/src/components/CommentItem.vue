<template>
  <div class="comment" :style="{ marginLeft: depth * 24 + 'px' }">

    <!-- Comment header -->
    <div class="comment-header">
      <strong>{{ comment.username || comment.user?.username }}</strong>
      <span class="meta">
        {{ comment.email || comment.user?.email }}
        · {{ formatDate(comment.created_at) }}
      </span>
    </div>

    <!-- Comment body -->
    <div class="comment-body" v-html="comment.text" />

    <!-- Attachment -->
    <div v-if="comment.attachment" class="attachment">
      <a :href="comment.attachment.storage_path" target="_blank">
        📎 {{ comment.attachment.original_filename }}
      </a>
    </div>

    <!-- Reply button -->
    <button class="reply-btn" @click="toggleReplies">
      {{ showReplies ? 'Hide replies' : `Replies (${replyCount})` }}
    </button>
    <button class="reply-btn" @click="$emit('reply', comment.id)">
      ↩ Reply
    </button>

    <!-- Nested replies -->
    <div v-if="showReplies && hasReplies" class="replies">
      <CommentItem
        v-for="reply in replies"
        :key="reply.id"
        :comment="reply"
        :depth="depth + 1"
        @reply="$emit('reply', $event)"
      />
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '../api/client.js'

const props = defineProps({
  comment: { type: Object, required: true },
  depth:   { type: Number, default: 0 },
})

defineEmits(['reply'])

const showReplies = ref(false)
const replies = ref([])
const loaded = ref(false)

const replyCount = computed(() => props.comment.reply_count ?? 0)
const hasReplies  = computed(() => replies.value.length > 0)

async function toggleReplies() {
  if (!loaded.value && replyCount.value > 0) {
    // Fetch the full tree for this root comment
    const res = await api.getCommentTree(props.comment.id)
    // The tree response is [root + replies nested]
    replies.value = res.data[0]?.replies ?? []
    loaded.value = true
  }
  showReplies.value = !showReplies.value
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString()
}
</script>

<style scoped>
.comment {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 12px 16px;
  margin-bottom: 10px;
}
.comment-header {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 8px;
}
.meta { font-size: 0.8rem; color: #888; }
.comment-body { line-height: 1.6; }
.attachment { margin-top: 8px; font-size: 0.85rem; }
.reply-btn {
  margin-top: 8px;
  margin-right: 8px;
  background: none;
  border: none;
  color: #555;
  cursor: pointer;
  font-size: 0.85rem;
  padding: 2px 0;
}
.reply-btn:hover { color: #000; }
.replies { margin-top: 8px; }
</style>
