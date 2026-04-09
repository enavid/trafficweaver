import { useState, useEffect, useRef, useCallback } from 'react'
import { Card } from '@/components/Card'
import Button from '@/components/Button'
import { getLogs, clearLogs, type LogEntry } from '@/lib/api'
import { useWebSocketLogs, type WsLogEntry } from '@/hooks/useWebSocket'
import { Trash2, Wifi, WifiOff, ArrowDownToLine, Filter } from 'lucide-react'

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: 'var(--color-text-faint)',
  INFO: 'var(--color-primary)',
  WARNING: 'var(--color-warning)',
  ERROR: 'var(--color-error)',
  CRITICAL: 'var(--color-error)',
}

const LEVEL_BG: Record<string, string> = {
  DEBUG: 'transparent',
  INFO: 'rgba(34,211,238,0.06)',
  WARNING: 'rgba(251,191,36,0.06)',
  ERROR: 'rgba(248,113,113,0.06)',
  CRITICAL: 'rgba(248,113,113,0.1)',
}

export default function Logs() {
  const [dbLogs, setDbLogs] = useState<LogEntry[]>([])
  const [filterLevel, setFilterLevel] = useState<string | null>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const scrollRef = useRef<HTMLDivElement>(null)
  const { logs: wsLogs, connected, clearLogs: clearWsLogs } = useWebSocketLogs(true)

  const refresh = useCallback(async () => {
    try {
      const data = await getLogs(300, filterLevel || undefined)
      setDbLogs(data.reverse())
    } catch {
      // Ignore
    }
  }, [filterLevel])

  useEffect(() => { refresh() }, [refresh])

  // Auto-scroll to bottom on new WebSocket logs
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [wsLogs, autoScroll])

  const handleClear = async () => {
    try {
      await clearLogs()
      clearWsLogs()
      setDbLogs([])
    } catch {
      // Ignore
    }
  }

  const handleScroll = () => {
    if (!scrollRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current
    setAutoScroll(scrollHeight - scrollTop - clientHeight < 40)
  }

  // Combine DB logs with real-time WS logs
  const allLogs: Array<{ level: string; message: string; timestamp?: string }> = [
    ...dbLogs.map((l) => ({ level: l.level, message: l.message, timestamp: l.timestamp })),
    ...wsLogs.map((l) => ({ level: l.level, message: l.message })),
  ]

  const filteredLogs = filterLevel
    ? allLogs.filter((l) => l.level === filterLevel)
    : allLogs

  const levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>System Logs</h2>
          <p className="text-sm mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
            Real-time log stream with history
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Connection indicator */}
          <div className="flex items-center gap-1.5 text-xs" style={{ color: connected ? 'var(--color-success)' : 'var(--color-error)' }}>
            {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
            {connected ? 'Live' : 'Disconnected'}
          </div>
          <Button variant="ghost" size="sm" onClick={() => setAutoScroll(!autoScroll)}>
            <ArrowDownToLine size={14} />
            {autoScroll ? 'Auto-scroll ON' : 'Auto-scroll OFF'}
          </Button>
          <Button variant="danger" size="sm" onClick={handleClear}>
            <Trash2 size={14} /> Clear
          </Button>
        </div>
      </div>

      {/* Level filter */}
      <div className="flex items-center gap-2">
        <Filter size={14} style={{ color: 'var(--color-text-muted)' }} />
        <button
          onClick={() => setFilterLevel(null)}
          className="px-3 py-1 rounded-md text-xs font-medium transition-colors"
          style={{
            background: !filterLevel ? 'var(--color-primary-highlight)' : 'transparent',
            color: !filterLevel ? 'var(--color-primary)' : 'var(--color-text-muted)',
            border: `1px solid ${!filterLevel ? 'var(--color-primary)' : 'var(--color-border)'}`,
          }}
        >
          All
        </button>
        {levels.map((lvl) => (
          <button
            key={lvl}
            onClick={() => setFilterLevel(filterLevel === lvl ? null : lvl)}
            className="px-3 py-1 rounded-md text-xs font-medium transition-colors"
            style={{
              background: filterLevel === lvl ? 'var(--color-primary-highlight)' : 'transparent',
              color: filterLevel === lvl ? LEVEL_COLORS[lvl] : 'var(--color-text-muted)',
              border: `1px solid ${filterLevel === lvl ? LEVEL_COLORS[lvl] : 'var(--color-border)'}`,
            }}
          >
            {lvl}
          </button>
        ))}
      </div>

      {/* Log viewer */}
      <Card padding={false}>
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="h-[calc(100vh-300px)] overflow-y-auto font-mono text-xs"
          style={{ minHeight: '400px' }}
        >
          {filteredLogs.length === 0 ? (
            <div className="p-8 text-center" style={{ color: 'var(--color-text-muted)' }}>
              No log entries yet.
            </div>
          ) : (
            filteredLogs.map((entry, i) => (
              <div
                key={i}
                className="flex px-4 py-1.5 border-b"
                style={{
                  background: LEVEL_BG[entry.level] || 'transparent',
                  borderColor: 'var(--color-divider)',
                }}
              >
                <span
                  className="inline-block w-16 flex-shrink-0 font-semibold uppercase"
                  style={{ color: LEVEL_COLORS[entry.level] || 'var(--color-text)' }}
                >
                  {entry.level}
                </span>
                {entry.timestamp && (
                  <span
                    className="inline-block w-44 flex-shrink-0"
                    style={{ color: 'var(--color-text-faint)' }}
                  >
                    {entry.timestamp}
                  </span>
                )}
                <span style={{ color: 'var(--color-text)', wordBreak: 'break-all' }}>
                  {entry.message}
                </span>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  )
}
