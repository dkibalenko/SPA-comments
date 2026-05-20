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
    <div v-if="attachment" class="attachment">
      <button class="attach-btn" @click="lightboxOpen = true">
        <span v-if="attachment.file_type === 'image'">🖼</span>
        <span v-else>📄</span>
        {{ attachment.original_filename }}
      </button>
    </div>

    <!-- Lightbox -->
    <LightboxViewer
      :file="attachment"
      :visible="lightboxOpen"
      @close="lightboxOpen = false"
    />

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
import { ref, computed, onMounted, inject, watch } from 'vue'
import LightboxViewer from './LightboxViewer.vue'
import api from '../api/client.js'

const props = defineProps({
  comment: { type: Object, required: true },
  depth:   { type: Number, default: 0 },
})

defineEmits(['reply'])

const showReplies = ref(false)
const replies = ref([])
const loaded = ref(false)
const lightboxOpen = ref(false)

// reply_count exists on list items; for tree items check embedded replies
const replyCount = computed(() =>
  props.comment.reply_count ?? props.comment.replies?.length ?? 0
)
const hasReplies = computed(() => replies.value.length > 0)

// If the comment already has replies embedded (from tree CTE), use them directly
onMounted(() => {
  if (props.comment.replies?.length) {
    replies.value = props.comment.replies
    loaded.value = true
  }
})

async function toggleReplies() {
  if (!showReplies.value) {
    if (props.depth === 0 && replyCount.value > 0) {
      // Root items own the tree fetch — CTE returns all descendants
      const res = await api.getCommentTree(props.comment.id)
      replies.value = res.data[0]?.replies ?? []
      loaded.value = true
    }
    // Nested items: replies come from props.comment.replies kept in sync below
  }
  showReplies.value = !showReplies.value
}

// Nested items' replies come from the root's tree fetch embedded in props.
// This watch fires whenever the parent re-fetches and passes new prop data down.
watch(() => props.comment.replies, (newReplies) => {
  if (props.depth > 0) {
    replies.value = newReplies ?? []
  }
})

// Root items re-fetch their tree when any reply is posted anywhere.
const treeRefreshKey = inject('treeRefreshKey', ref(0))
watch(treeRefreshKey, async () => {
  if (loaded.value && props.depth === 0) {
    const res = await api.getCommentTree(props.comment.id)
    replies.value = res.data[0]?.replies ?? []
  }
})

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString()
}

const attachment = computed(() => {
  if (props.comment.attachment) {
    return props.comment.attachment
  }
  if (props.comment.attachment_path) {
    const path = props.comment.attachment_path
    const url = path.startsWith('http') ? path : `/media/${path}`
    return {
      file_type: props.comment.attachment_type,
      original_filename: props.comment.attachment_filename,
      url,
    }
  }
  return null
})
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
.attach-btn {
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 4px 10px;
  cursor: pointer;
  font-size: 0.85rem;
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: background 0.15s;
}
.attach-btn:hover { background: #e8e8e8; }
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
