<template>
  <div class="app">
    <header>
      <h1>💬 Comments</h1>
    </header>

    <main>
      <CommentForm
        :reply-to-id="replyToId"
        @submitted="onCommentSubmitted"
        @cancel-reply="replyToId = null"
      />

      <CommentList
        :comments="comments"
        :total="total"
        :page="page"
        :ordering="ordering"
        @page-change="loadPage"
        @sort-change="changeSort"
        @reply="openReplyForm"
      />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import CommentForm from './components/CommentForm.vue'
import CommentList from './components/CommentList.vue'
import api from './api/client.js'
import { useWebSocket } from './composables/useWebSocket.js'

const comments = ref([])
const total = ref(0)
const page = ref(1)
const ordering = ref('-date')

async function loadComments() {
  const res = await api.getComments({
    page: page.value,
    ordering: ordering.value,
  })
  comments.value = res.data.results
  total.value = res.data.count
}

function onCommentSubmitted() {
  page.value = 1
  loadComments()
}

const replyToId = ref(null)

function openReplyForm(commentId) {
  replyToId.value = commentId
  // Scroll to form
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function loadPage(p) {
  page.value = p
  loadComments()
}

function changeSort(field) {
  // toggle asc/desc on same field
  ordering.value = ordering.value === field ? `-${field}` : field
  page.value = 1
  loadComments()
}

// WebSocket — adds new top-level comments in real time
useWebSocket((data) => {
  if (!data.parent_id) {
    // New top-level comment — reload the list
    loadComments()
  }
})

onMounted(loadComments)
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, sans-serif; background: #f5f5f5; color: #333; }
.app { max-width: 900px; margin: 0 auto; padding: 20px; }
header { margin-bottom: 24px; }
h1 { font-size: 1.8rem; }
</style>
