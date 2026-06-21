import { ref, onUnmounted } from 'vue'
import { useMessage, useNotification } from 'naive-ui'

export interface WsMessage {
  type: 'connected' | 'notification' | 'alert' | 'data_update' | 'ping'
  event?: string
  org_id?: number
  title?: string
  message?: string
  level?: 'info' | 'warning' | 'critical'
  data?: Record<string, unknown>
  timestamp?: string
}

let ws: WebSocket | null = null
let reconnectTimer: number | null = null
const isConnected = ref(false)
const listeners = new Set<(msg: WsMessage) => void>()

function connect(token: string) {
  if (ws && ws.readyState === WebSocket.OPEN) return
  if (!token) return

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  // 开发环境通过 vite proxy 转发 /ws 到后端
  const wsUrl = `${protocol}//${host}/api/v1/ws?token=${encodeURIComponent(token)}`

  try {
    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      isConnected.value = true
      console.log('[WS] connected')
    }

    ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data)
        if (msg.type === 'ping') return
        listeners.forEach((fn) => fn(msg))
      } catch (e) {
        console.warn('[WS] parse error:', e)
      }
    }

    ws.onclose = () => {
      isConnected.value = false
      console.log('[WS] disconnected, reconnecting in 5s...')
      // 5 秒后自动重连
      if (reconnectTimer) clearTimeout(reconnectTimer)
      reconnectTimer = window.setTimeout(() => {
        const newToken = localStorage.getItem('token')
        if (newToken) connect(newToken)
      }, 5000)
    }

    ws.onerror = (error) => {
      console.error('[WS] error:', error)
    }

    // 心跳保活
    const heartbeat = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send('ping')
      }
    }, 30000)

    onUnmounted(() => clearInterval(heartbeat))
  } catch (e) {
    console.error('[WS] connect failed:', e)
  }
}

function disconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (ws) {
    ws.close()
    ws = null
  }
  isConnected.value = false
}

function onMessage(fn: (msg: WsMessage) => void) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export function useWebSocket() {
  return { connect, disconnect, isConnected, onMessage }
}

/**
 * 全局实时通知 composable
 * 在 Layout 中调用，自动将 WebSocket 消息转为 Naive UI 通知
 */
export function useRealtimeNotifications() {
  const notification = useNotification()

  function start(token: string) {
    connect(token)
    onMessage((msg) => {
      if (msg.type === 'notification' || msg.type === 'alert') {
        const type = msg.level === 'critical' ? 'error' : msg.level === 'warning' ? 'warning' : 'info'
        notification[type]({
          title: msg.title || '通知',
          content: msg.message || '',
          duration: msg.level === 'critical' ? 0 : 5000,
          meta: msg.event || '',
        })
      }
    })
  }

  return { start, isConnected }
}
