import { onUnmounted } from 'vue'

export function useWebSocket(onMessage) {
  const ws = new WebSocket(`ws://${location.host}/ws/comments/`)

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    onMessage(data)
  }

  ws.onclose = () => console.log('WS disconnected')
  ws.onerror = (e) => console.error('WS error', e)

  // Auto-cleanup when component unmounts
  onUnmounted(() => ws.close())

  return ws
}
