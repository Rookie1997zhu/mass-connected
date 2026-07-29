/**
 * 聊天 WebSocket：每用户一条连接，指数退避重连，心跳保活。
 * 握手使用短时一次性 ticket（禁止长期 JWT 放 query）。
 */
export function createChatSocket({ fetchTicket, onEvent, onStatus } = {}) {
  let ws = null
  let closedByUser = false
  let attempt = 0
  let pingTimer = null
  let reconnectTimer = null
  let connecting = false

  const wsUrl = (ticket) => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${proto}//${window.location.host}/ws/chat/?ticket=${encodeURIComponent(ticket)}`
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

  const connect = async () => {
    if (!fetchTicket || connecting || closedByUser) return
    connecting = true
    clearTimers()
    onStatus?.('connecting')
    let ticket
    try {
      ticket = await fetchTicket()
    } catch {
      connecting = false
      onStatus?.('error')
      scheduleReconnect()
      return
    }
    if (!ticket || closedByUser) {
      connecting = false
      return
    }
    try {
      ws = new WebSocket(wsUrl(ticket))
    } catch {
      connecting = false
      onStatus?.('error')
      scheduleReconnect()
      return
    }
    ws.onopen = () => {
      connecting = false
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
      connecting = false
      clearTimers()
      onStatus?.('closed')
      if (closedByUser || ev.code === 4000) return
      scheduleReconnect()
    }
    ws.onerror = () => {
      onStatus?.('error')
    }
  }

  const scheduleReconnect = () => {
    if (closedByUser || reconnectTimer) return
    const delay = Math.min(30000, 1000 * 2 ** attempt)
    attempt += 1
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, delay)
  }

  connect()

  return {
    close() {
      closedByUser = true
      clearTimers()
      ws?.close()
    },
    reconnect() {
      closedByUser = false
      attempt = 0
      ws?.close()
      connect()
    },
  }
}
