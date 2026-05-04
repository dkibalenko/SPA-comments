<template>
  <div class="form-wrap">
    <h2>Leave a Comment</h2>

    <!-- Preview toggle -->
    <div v-if="previewMode" class="preview-box">
      <div class="preview-label">Preview:</div>
      <div class="preview-body" v-html="form.text" />
      <button @click="previewMode = false">✏️ Back to edit</button>
    </div>

    <form v-else @submit.prevent="submit">

      <!-- Identity fields -->
      <div class="row">
        <div class="field">
          <label>Username *</label>
          <input
            v-model="form.username"
            placeholder="Letters and digits only"
            :class="{ error: errors.username }"
          />
          <span class="err">{{ errors.username }}</span>
        </div>
        <div class="field">
          <label>Email *</label>
          <input
            v-model="form.email"
            type="email"
            placeholder="you@example.com"
            :class="{ error: errors.email }"
          />
          <span class="err">{{ errors.email }}</span>
        </div>
      </div>

      <div class="field">
        <label>Home page</label>
        <input
          v-model="form.home_page"
          placeholder="https://your-site.com (optional)"
        />
      </div>

      <!-- Reply context -->
      <div v-if="replyToId" class="reply-notice">
        Replying to comment <code>{{ replyToId.slice(0, 8) }}…</code>
        <button type="button" @click="$emit('cancel-reply')">✕ Cancel</button>
      </div>

      <!-- HTML toolbar -->
      <div class="toolbar">
        <button type="button" @click="wrap('i')"><i>i</i></button>
        <button type="button" @click="wrap('strong')"><strong>B</strong></button>
        <button type="button" @click="wrap('code')">code</button>
        <button type="button" @click="insertLink()">a</button>
      </div>

      <!-- Text area -->
      <div class="field">
        <label>Comment *</label>
        <textarea
          ref="textarea"
          v-model="form.text"
          rows="5"
          placeholder="Write your comment… allowed tags: <i> <strong> <code> <a>"
          :class="{ error: errors.text }"
        />
        <span class="err">{{ errors.text }}</span>
      </div>

      <!-- Toolbar actions -->
      <div class="toolbar-actions">
        <button type="button" @click="previewMode = true">👁 Preview</button>
      </div>

      <!-- File attachment -->
      <div class="field">
        <label>Attach file (image JPG/PNG/GIF max 320×240 or TXT max 100KB)</label>
        <input type="file" @change="onFileChange" accept=".jpg,.jpeg,.png,.gif,.txt" />
        <span class="err">{{ errors.file }}</span>
      </div>

      <!-- CAPTCHA -->
      <div class="field captcha-field">
        <label>CAPTCHA *</label>
        <div class="captcha-row">
          <img
            v-if="captcha.image"
            :src="`data:image/png;base64,${captcha.image}`"
            alt="captcha"
            class="captcha-img"
          />
          <button type="button" @click="loadCaptcha">🔄</button>
        </div>
        <input
          v-model="form.captcha_answer"
          placeholder="Type the characters above"
          :class="{ error: errors.captcha_answer }"
        />
        <span class="err">{{ errors.captcha_answer }}</span>
      </div>

      <!-- Submit -->
      <div class="form-actions">
        <button type="submit" :disabled="submitting">
          {{ submitting ? 'Posting…' : 'Post Comment' }}
        </button>
      </div>

      <div v-if="serverError" class="server-error">{{ serverError }}</div>

    </form>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import api from '../api/client.js'

const props = defineProps({
  replyToId: { type: String, default: null },
})

const emit = defineEmits(['submitted', 'cancel-reply'])

// ── State ─────────────────────────────────────────────
const form = ref({
  username: '',
  email: '',
  home_page: '',
  text: '',
  captcha_answer: '',
  file: null,
})

const errors      = ref({})
const serverError = ref('')
const submitting  = ref(false)
const previewMode = ref(false)
const textarea    = ref(null)

const captcha = ref({ token: '', image: '' })

// ── CAPTCHA ───────────────────────────────────────────
async function loadCaptcha() {
  const res = await api.getCaptcha()
  captcha.value = res.data
}

onMounted(loadCaptcha)

// ── HTML toolbar ──────────────────────────────────────
function wrap(tag) {
  const el = textarea.value
  if (!el) return
  const start = el.selectionStart
  const end   = el.selectionEnd
  const selected = form.value.text.slice(start, end) || 'text'
  const before = form.value.text.slice(0, start)
  const after  = form.value.text.slice(end)
  form.value.text = `${before}<${tag}>${selected}</${tag}>${after}`
}

function insertLink() {
  const href  = prompt('URL:')
  const title = prompt('Title (optional):')
  if (!href) return
  const el = textarea.value
  const start = el.selectionStart
  const end   = el.selectionEnd
  const label = form.value.text.slice(start, end) || 'link text'
  const tag = title
    ? `<a href="${href}" title="${title}">${label}</a>`
    : `<a href="${href}">${label}</a>`
  form.value.text =
    form.value.text.slice(0, start) + tag + form.value.text.slice(end)
}

// ── File ──────────────────────────────────────────────
function onFileChange(e) {
  form.value.file = e.target.files[0] || null
  errors.value.file = ''
}

// ── Validation ────────────────────────────────────────
function validate() {
  const e = {}
  if (!form.value.username.trim())
    e.username = 'Username is required.'
  else if (!/^[a-zA-Z0-9]+$/.test(form.value.username))
    e.username = 'Letters and digits only.'
  if (!form.value.email.trim())
    e.email = 'Email is required.'
  if (!form.value.text.trim())
    e.text = 'Comment text is required.'
  if (!form.value.captcha_answer.trim())
    e.captcha_answer = 'Please solve the CAPTCHA.'
  errors.value = e
  return Object.keys(e).length === 0
}

// ── Submit ────────────────────────────────────────────
async function submit() {
  serverError.value = ''
  if (!validate()) return

  submitting.value = true
  try {
    await api.createComment({
      username:       form.value.username,
      email:          form.value.email,
      home_page:      form.value.home_page || null,
      text:           form.value.text,
      captcha_token:  captcha.value.token,
      captcha_answer: form.value.captcha_answer,
      parent_id:      props.replyToId || null,
      file:           form.value.file,
    })

    // Reset form
    form.value = {
      username: form.value.username,   // keep identity
      email:    form.value.email,
      home_page: form.value.home_page,
      text: '',
      captcha_answer: '',
      file: null,
    }
    await loadCaptcha()
    emit('submitted')

  } catch (err) {
    const detail = err.response?.data?.detail
    if (detail) {
      serverError.value = detail
    } else if (err.response?.data) {
      // Field-level errors from DRF serializer
      errors.value = err.response.data
    } else {
      serverError.value = 'Something went wrong. Please try again.'
    }
    await loadCaptcha()   // always refresh CAPTCHA on failure
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.form-wrap {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 32px;
}
h2 { margin-bottom: 16px; font-size: 1.2rem; }

.row { display: flex; gap: 16px; }
.row .field { flex: 1; }

.field { margin-bottom: 14px; }
label { display: block; font-size: 0.85rem; margin-bottom: 4px; color: #555; }
input, textarea {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.95rem;
  font-family: inherit;
}
input.error, textarea.error { border-color: #e53e3e; }
.err { color: #e53e3e; font-size: 0.8rem; }

.toolbar {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
}
.toolbar button {
  padding: 4px 10px;
  border: 1px solid #ccc;
  background: #f9f9f9;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}
.toolbar-actions { margin-bottom: 12px; }
.toolbar-actions button {
  padding: 4px 12px;
  border: 1px solid #ccc;
  background: #f9f9f9;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}

.captcha-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.captcha-img { border: 1px solid #ccc; border-radius: 4px; }
.captcha-row button {
  padding: 4px 8px;
  border: 1px solid #ccc;
  background: #f9f9f9;
  border-radius: 4px;
  cursor: pointer;
}

.reply-notice {
  background: #f0f4ff;
  border: 1px solid #c3d0f5;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 0.85rem;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.reply-notice button {
  background: none;
  border: none;
  cursor: pointer;
  color: #888;
}

.preview-box {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 16px;
}
.preview-label { font-size: 0.8rem; color: #888; margin-bottom: 8px; }
.preview-body { line-height: 1.6; margin-bottom: 12px; }
.preview-box button {
  padding: 4px 12px;
  border: 1px solid #ccc;
  background: #f9f9f9;
  border-radius: 4px;
  cursor: pointer;
}

.form-actions button {
  padding: 10px 24px;
  background: #333;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95rem;
}
.form-actions button:disabled { opacity: 0.5; cursor: default; }

.server-error {
  margin-top: 12px;
  color: #e53e3e;
  font-size: 0.9rem;
}
</style>
