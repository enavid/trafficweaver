import { useEffect, useRef, useCallback, useState } from 'react'
import { getToken } from '@/lib/api'

export interface WsLogEntry {
  level: string
  logger: string
  message: string
}

export function useWebSocketLogs(enabled: boolean = true) {
  const [logs, setLogs] = useState<WsLogEntry[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>()

  const connect = useCallback(() => {
    const token = getToken()
    if (!token || !enabled) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/ws/logs?token=${token}`)

    ws.onopen = () => {
      setConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const entry: WsLogEntry = JSON.parse(event.data)
        setLogs(prev => {
          const next = [...prev, entry]
          // Keep last 500 entries in memory
          return next.length > 500 ? next.slice(-500) : next
        })
      } catch {
        // Ignore malformed messages
      }
    }

    ws.onclose = () => {
      setConnected(false)
      // Auto-reconnect after 3 seconds
      reconnectRef.current = setTimeout(connect, 3000)
    }

    ws.onerror = () => {
      ws.close()
    }

    wsRef.current = ws
  }, [enabled])

  useEffect(() => {
    connect()
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectRef.current) {
        clearTimeout(reconnectRef.current)
      }
    }
  }, [connect])

  const clearLogs = useCallback(() => {
    setLogs([])
  }, [])

  return { logs, connected, clearLogs }
}

export interface BrowsePreviewEntry {
  type: string
  url: string
  title: string
  depth: number
  timestamp: string
}

export function useWebSocketBrowsePreview(enabled: boolean = true) {
  const [currentPage, setCurrentPage] = useState<BrowsePreviewEntry | null>(null)
  const [history, setHistory] = useState<BrowsePreviewEntry[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>()

  const connect = useCallback(() => {
    const token = getToken()
    if (!token || !enabled) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/ws/browse-preview?token=${token}`)

    ws.onopen = () => {
      setConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const entry: BrowsePreviewEntry = JSON.parse(event.data)
        setCurrentPage(entry)
        setHistory(prev => {
          const next = [...prev, entry]
          return next.length > 50 ? next.slice(-50) : next
        })
      } catch {
        // Ignore malformed messages
      }
    }

    ws.onclose = () => {
      setConnected(false)
      reconnectRef.current = setTimeout(connect, 3000)
    }

    ws.onerror = () => {
      ws.close()
    }

    wsRef.current = ws
  }, [enabled])

  useEffect(() => {
    connect()
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectRef.current) {
        clearTimeout(reconnectRef.current)
      }
    }
  }, [connect])

  const clearHistory = useCallback(() => {
    setHistory([])
    setCurrentPage(null)
  }, [])

  return { currentPage, history, connected, clearHistory }
}
