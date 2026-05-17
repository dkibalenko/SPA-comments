import { onUnmounted } from 'vue'

export function useWebSocket(onMessage) {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${protocol}://${location.host}/ws/comments/`)

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
