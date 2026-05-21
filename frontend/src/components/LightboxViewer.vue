<template>
  <!-- Overlay -->
  <Teleport to="body">
    <div v-if="visible" class="lightbox-overlay" @click.self="close">
      <div class="lightbox-box">

        <!-- Close button -->
        <button class="lb-close" @click="close">✕</button>

        <!-- Image viewer -->
        <template v-if="isImage">
          <img :src="file.url" :alt="file.original_filename" class="lb-image" />
        </template>

        <!-- Text file viewer -->
        <template v-else>
          <div class="lb-text-header">
            📄 {{ file.original_filename }}
          </div>
          <div v-if="textLoading" class="lb-loading">Loading…</div>
          <pre v-else class="lb-text-content">{{ textContent }}</pre>
        </template>

        <div class="lb-filename">{{ file.original_filename }}</div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  file:    { type: Object, default: null },  // { url, file_type, original_filename }
  visible: { type: Boolean, default: false },
})

const emit = defineEmits(['close'])

const textContent = ref('')
const textLoading = ref(false)

const isImage = computed(() =>
  props.file?.file_type === 'image'
)

// When a text file opens, fetch its content
watch(() => props.visible, async (open) => {
  if (open && !isImage.value && props.file?.url) {
    textLoading.value = true
    try {
      const res = await fetch(props.file.url)
      textContent.value = await res.text()
    } catch {
      textContent.value = 'Could not load file.'
    } finally {
      textLoading.value = false
    }
  }
})

// Close on Escape key
function onKey(e) {
  if (e.key === 'Escape') close()
}

watch(() => props.visible, (open) => {
  if (open) {
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'  // prevent background scroll
  } else {
    document.removeEventListener('keydown', onKey)
    document.body.style.overflow = ''
  }
})

function close() {
  emit('close')
}
</script>

<style scoped>
.lightbox-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.82);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.18s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

.lightbox-box {
  position: relative;
  background: #1a1a1a;
  border-radius: 8px;
  padding: 16px;
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  animation: scaleIn 0.18s ease;
}

@keyframes scaleIn {
  from { transform: scale(0.9); opacity: 0; }
  to   { transform: scale(1);   opacity: 1; }
}

.lb-close {
  position: absolute;
  top: 8px;
  right: 12px;
  background: none;
  border: none;
  color: #fff;
  font-size: 1.4rem;
  cursor: pointer;
  line-height: 1;
  opacity: 0.7;
}
.lb-close:hover { opacity: 1; }

.lb-image {
  max-width: 80vw;
  max-height: 75vh;
  object-fit: contain;
  border-radius: 4px;
  display: block;
}

.lb-text-header {
  color: #ccc;
  font-size: 0.9rem;
  margin-bottom: 12px;
  align-self: flex-start;
}

.lb-text-content {
  background: #111;
  color: #e0e0e0;
  padding: 16px;
  border-radius: 4px;
  font-size: 0.85rem;
  line-height: 1.6;
  max-width: 70vw;
  max-height: 65vh;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.lb-loading {
  color: #888;
  padding: 40px;
}

.lb-filename {
  color: #888;
  font-size: 0.8rem;
  margin-top: 10px;
}
</style>
