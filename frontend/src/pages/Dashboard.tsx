import { useState, useEffect, useCallback } from 'react'
import { Card, StatCard } from '@/components/Card'
import Button from '@/components/Button'
import { formatBytes, formatPct } from '@/lib/utils'
import {
  getTodayStats,
  getEngineStatus,
  startEngine,
  stopEngine,
  getStatsHistory,
  getCurrentBrowsing,
  type DailyStats,
  type CurrentBrowsing,
} from '@/lib/api'
import { useWebSocketBrowsePreview } from '@/hooks/useWebSocket'
import {
  Download,
  Globe,
  Target,
  Activity,
  Play,
  Square,
  TrendingUp,
  CheckCircle2,
  XCircle,
  Eye,
  ExternalLink,
  Layers,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'

export default function Dashboard() {
  const [stats, setStats] = useState<DailyStats | null>(null)
  const [history, setHistory] = useState<DailyStats[]>([])
  const [engineRunning, setEngineRunning] = useState(false)
  const [engineDay, setEngineDay] = useState(0)
  const [loading, setLoading] = useState(false)
  const [currentBrowsing, setCurrentBrowsing] = useState<CurrentBrowsing | null>(null)

  const { currentPage: wsPage, history: browseHistory, connected: browseWsConnected } = useWebSocketBrowsePreview(engineRunning)

  const refresh = useCallback(async () => {
    try {
      const [s, e, h, cb] = await Promise.all([
        getTodayStats(),
        getEngineStatus(),
        getStatsHistory(14),
        getCurrentBrowsing(),
      ])
      setStats(s)
      setEngineRunning(e.running)
      setEngineDay(e.current_day)
      setHistory(h.reverse())
      setCurrentBrowsing(cb)
    } catch {
      // Ignore
    }
  }, [])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 5000)
    return () => clearInterval(interval)
  }, [refresh])

  const handleToggleEngine = async () => {
    setLoading(true)
    try {
      if (engineRunning) {
        await stopEngine()
      } else {
        await startEngine(0)
      }
      await refresh()
    } catch {
      // Ignore
    } finally {
      setLoading(false)
    }
  }

  const totalBytes = stats ? stats.downloaded_bytes + stats.browse_bytes : 0
  const progress = stats && stats.target_bytes > 0 ? (totalBytes / stats.target_bytes) * 100 : 0

  const chartData = history.map((h) => ({
    date: h.date?.slice(5) || '',
    downloaded: Number(((h.downloaded_bytes + h.browse_bytes) / 1024 / 1024 / 1024).toFixed(2)),
    target: Number((h.target_bytes / 1024 / 1024 / 1024).toFixed(2)),
  }))

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>Dashboard</h2>
          <p className="text-sm mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
            Traffic simulation overview
          </p>
        </div>
        <Button
          variant={engineRunning ? 'danger' : 'primary'}
          onClick={handleToggleEngine}
          disabled={loading}
          data-testid="btn-engine-toggle"
        >
          {engineRunning ? <Square size={16} /> : <Play size={16} />}
          {engineRunning ? 'Stop Engine' : 'Start Engine'}
        </Button>
      </div>

      {/* Engine status */}
      <div
        className="flex items-center gap-3 px-4 py-3 rounded-xl"
        style={{
          background: engineRunning ? 'rgba(52,211,153,0.08)' : 'var(--color-surface-offset)',
          border: `1px solid ${engineRunning ? 'rgba(52,211,153,0.2)' : 'var(--color-border)'}`,
        }}
      >
        <div
          className="w-2.5 h-2.5 rounded-full"
          style={{
            background: engineRunning ? 'var(--color-success)' : 'var(--color-text-faint)',
            boxShadow: engineRunning ? '0 0 8px var(--color-success)' : 'none',
          }}
        />
        <span className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>
          {engineRunning ? `Engine running — Day ${engineDay}` : 'Engine stopped'}
        </span>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Traffic"
          value={formatBytes(totalBytes)}
          sub={stats?.target_bytes ? `of ${formatBytes(stats.target_bytes)} target` : undefined}
          icon={<TrendingUp size={20} />}
          color="var(--color-primary)"
        />
        <StatCard
          label="Downloads"
          value={formatBytes(stats?.downloaded_bytes || 0)}
          sub={`${stats?.file_downloads_ok || 0} successful`}
          icon={<Download size={20} />}
          color="var(--color-success)"
        />
        <StatCard
          label="Browse Traffic"
          value={formatBytes(stats?.browse_bytes || 0)}
          sub={`${stats?.browse_visits || 0} visits`}
          icon={<Globe size={20} />}
          color="var(--color-warning)"
        />
        <StatCard
          label="Progress"
          value={formatPct(progress)}
          sub={stats?.file_downloads_fail ? `${stats.file_downloads_fail} failed` : 'No failures'}
          icon={progress >= 100 ? <CheckCircle2 size={20} /> : <Target size={20} />}
          color={progress >= 100 ? 'var(--color-success)' : 'var(--color-primary)'}
        />
      </div>

      {/* Live Browsing Preview */}
      {engineRunning && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold flex items-center gap-2" style={{ color: 'var(--color-text)' }}>
              <Eye size={16} /> Live Browsing Preview
            </h3>
            <div className="flex items-center gap-2">
              <div
                className="w-2 h-2 rounded-full"
                style={{
                  background: browseWsConnected ? 'var(--color-success)' : 'var(--color-text-faint)',
                  boxShadow: browseWsConnected ? '0 0 6px var(--color-success)' : 'none',
                }}
              />
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                {browseWsConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>

          {/* Current page */}
          {(wsPage || currentBrowsing) ? (
            <div className="space-y-3">
              <div
                className="flex items-start gap-3 p-3 rounded-lg"
                style={{ background: 'var(--color-surface-offset)' }}
              >
                <Globe size={18} className="mt-0.5 shrink-0" style={{ color: 'var(--color-primary)' }} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate" style={{ color: 'var(--color-text)' }}>
                    {wsPage?.title || currentBrowsing?.title || 'Loading...'}
                  </p>
                  <p className="text-xs truncate mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                    {wsPage?.url || currentBrowsing?.url || ''}
                  </p>
                  <div className="flex items-center gap-3 mt-1.5">
                    <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full"
                      style={{ background: 'var(--color-primary)', color: 'var(--color-text-inverse)', opacity: 0.9 }}>
                      <Layers size={10} /> Depth {wsPage?.depth ?? currentBrowsing?.depth ?? 0}
                    </span>
                    {wsPage?.timestamp && (
                      <span className="text-xs tabular-nums" style={{ color: 'var(--color-text-faint)' }}>
                        {new Date(wsPage.timestamp).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                </div>
                {(wsPage?.url || currentBrowsing?.url) && (
                  <a
                    href={wsPage?.url || currentBrowsing?.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0 p-1.5 rounded-md transition-colors hover:opacity-70"
                    style={{ color: 'var(--color-text-muted)' }}
                  >
                    <ExternalLink size={14} />
                  </a>
                )}
              </div>

              {/* Recent browsing history */}
              {browseHistory.length > 1 && (
                <div className="space-y-1">
                  <p className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
                    Recent Pages ({browseHistory.length})
                  </p>
                  <div className="max-h-32 overflow-y-auto space-y-1 pr-1">
                    {browseHistory.slice(-8).reverse().slice(1).map((entry, i) => (
                      <div
                        key={`${entry.url}-${i}`}
                        className="flex items-center gap-2 text-xs py-1 px-2 rounded"
                        style={{ background: i === 0 ? 'transparent' : 'transparent', color: 'var(--color-text-faint)' }}
                      >
                        <span className="w-1 h-1 rounded-full shrink-0" style={{ background: 'var(--color-text-faint)' }} />
                        <span className="truncate">{entry.title || entry.url}</span>
                        <span className="text-xs tabular-nums shrink-0 ml-auto" style={{ opacity: 0.6 }}>
                          L{entry.depth}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center py-8">
              <p className="text-sm" style={{ color: 'var(--color-text-faint)' }}>
                Waiting for browsing activity...
              </p>
            </div>
          )}
        </Card>
      )}

      {/* Progress bar */}
      <Card>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>Daily Progress</span>
          <span className="text-sm font-mono tabular-nums" style={{ color: 'var(--color-primary)' }}>
            {formatPct(progress)}
          </span>
        </div>
        <div className="h-3 rounded-full overflow-hidden" style={{ background: 'var(--color-surface-offset)' }}>
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${Math.min(progress, 100)}%`,
              background: progress >= 100
                ? 'var(--color-success)'
                : 'linear-gradient(90deg, var(--color-primary), var(--color-primary-hover))',
            }}
          />
        </div>
      </Card>

      {/* Chart */}
      {chartData.length > 1 && (
        <Card>
          <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--color-text)' }}>
            Traffic History (GB)
          </h3>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorTraffic" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="date" stroke="var(--color-text-faint)" fontSize={12} />
                <YAxis stroke="var(--color-text-faint)" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    background: 'var(--color-surface)',
                    border: '1px solid var(--color-border)',
                    borderRadius: '8px',
                    fontSize: '13px',
                  }}
                  labelStyle={{ color: 'var(--color-text)' }}
                />
                <Area
                  type="monotone"
                  dataKey="downloaded"
                  stroke="var(--color-primary)"
                  fill="url(#colorTraffic)"
                  strokeWidth={2}
                  name="Actual (GB)"
                />
                <Area
                  type="monotone"
                  dataKey="target"
                  stroke="var(--color-text-faint)"
                  fill="none"
                  strokeDasharray="4 4"
                  strokeWidth={1}
                  name="Target (GB)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}
    </div>
  )
}
