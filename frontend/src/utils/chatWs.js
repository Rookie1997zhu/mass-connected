/**
 * 聊天 WebSocket：每用户一条连接，指数退避重连，心跳保活。
 */
export function createChatSocket({ token, onEvent, onStatus } = {}) {
  let ws = null
  let closedByUser = false
  let attempt = 0
  let pingTimer = null
  let reconnectTimer = null

  const wsUrl = () => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${proto}//${window.location.host}/ws/chat/?token=${encodeURIComponent(token)}`
  }

  const clearTimers = () => {
    if (pingTimer) {
      clearInterval(pingTimer)
      pingTimer = null
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  const connect = () => {
    if (!token) return
    clearTimers()
    ws = new WebSocket(wsUrl())
    onStatus?.('connecting')
    ws.onopen = () => {
      attempt = 0
      onStatus?.('open')
      pingTimer = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ event: 'ping' }))
        }
      }, 25000)
    }
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data)
        onEvent?.(data)
      } catch {
        /* ignore */
      }
    }
    ws.onclose = (ev) => {
      clearTimers()
      onStatus?.('closed')
      if (closedByUser || ev.code === 4000) return
      const delay = Math.min(30000, 1000 * 2 ** attempt)
      attempt += 1
      reconnectTimer = setTimeout(connect, delay)
    }
    ws.onerror = () => {
      onStatus?.('error')
    }
  }

  connect()

  return {
    close() {
      closedByUser = true
      clearTimers()
      ws?.close()
    },
    reconnectWithToken(nextToken) {
      token = nextToken
      closedByUser = false
      attempt = 0
      ws?.close()
      connect()
    },
  }
}
