import { useState, useEffect, useCallback } from 'react'
import { Card } from '@/components/Card'
import Button from '@/components/Button'
import Input from '@/components/Input'
import {
  getConfig,
  updateConfig,
  changePassword,
  getTimezones,
  computeSchedule,
  getNetworkInterfaces,
  type NetworkInterface,
} from '@/lib/api'
import { formatBytes } from '@/lib/utils'
import { Save, Lock, Check, Clock, Globe, Sun, Moon, Wifi } from 'lucide-react'

// ── Types ────────────────────────────────────────────────────────────────────

interface SchedulePreview {
  weights: number[]
  labels: string[]
}

// ── Component ────────────────────────────────────────────────────────────────

export default function Settings() {
  const [config, setConfig] = useState<Record<string, any> | null>(null)
  const [mode, setMode] = useState<'simple' | 'advanced'>('simple')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  // ── Simple mode state ──────────────────────────────────────────────────────
  const [dailyTargetGb, setDailyTargetGb] = useState('10')
  const [speedCapMbps, setSpeedCapMbps] = useState('2')
  const [maxConcurrent, setMaxConcurrent] = useState('2')
  const [usePlaywright, setUsePlaywright] = useState(false)

  // Human-behavior active hours (Simple mode)
  const [wakeHour, setWakeHour] = useState(8)
  const [sleepHour, setSleepHour] = useState(24)
  const [schedulePreview, setSchedulePreview] = useState<SchedulePreview | null>(null)
  const [computingSchedule, setComputingSchedule] = useState(false)

  // ── Advanced mode state ────────────────────────────────────────────────────
  const [dailyVariance, setDailyVariance] = useState('0.20')
  const [schedWeights, setSchedWeights] = useState('0.05,0.30,0.35,0.30')
  const [pauseProb, setPauseProb] = useState('0.3')
  const [pauseMin, setPauseMin] = useState('15')
  const [pauseMax, setPauseMax] = useState('120')
  const [browseDelayMin, setBrowseDelayMin] = useState('8')
  const [browseDelayMax, setBrowseDelayMax] = useState('75')
  const [browseMaxLinks, setBrowseMaxLinks] = useState('3')
  const [bindIp, setBindIp] = useState('')
  const [logLevel, setLogLevel] = useState('INFO')

  // ── Network interface state ────────────────────────────────────────────────
  const [networkInterfaces, setNetworkInterfaces] = useState<NetworkInterface[]>([])
  const [selectedInterface, setSelectedInterface] = useState('')
  const [browseDepth, setBrowseDepth] = useState('2')

  // ── Timezone state ─────────────────────────────────────────────────────────
  const [timezones, setTimezones] = useState<Record<string, number>>({})
  const [selectedTimezone, setSelectedTimezone] = useState('Asia/Tehran')
  const [timezoneOffset, setTimezoneOffset] = useState(3.5)

  // ── Password state ─────────────────────────────────────────────────────────
  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [pwMsg, setPwMsg] = useState('')

  // ── Load config + timezones ────────────────────────────────────────────────

  const refresh = useCallback(async () => {
    try {
      const [c, tzList, nics] = await Promise.all([getConfig(), getTimezones(), getNetworkInterfaces()])
      setConfig(c)
      setTimezones(tzList)
      setNetworkInterfaces(nics)

      // Populate form fields
      const traffic = c.traffic || {}
      const dl = traffic.download || {}
      const br = traffic.browsing || {}
      const sched = traffic.schedule || {}
      const tz = c.timezone || {}

      setDailyTargetGb((traffic.daily_target_bytes / (1024 ** 3)).toFixed(1))
      setSpeedCapMbps(((dl.speed_cap_bps || 0) / (1024 * 1024)).toFixed(1))
      setMaxConcurrent(String(dl.max_concurrent || 2))
      setUsePlaywright(br.use_playwright || false)

      setDailyVariance(String(traffic.daily_variance || 0.20))
      setSchedWeights((sched.weights || [0.05, 0.30, 0.35, 0.30]).join(','))
      setPauseProb(String(dl.pause_probability || 0.3))
      const pr = dl.pause_range || [15, 120]
      setPauseMin(String(pr[0]))
      setPauseMax(String(pr[1]))
      const dr = br.delay_range || [8, 75]
      setBrowseDelayMin(String(dr[0]))
      setBrowseDelayMax(String(dr[1]))
      setBrowseMaxLinks(String(br.max_internal_links || 3))
      setBrowseDepth(String(br.browse_depth || 2))
      setBindIp(c.network?.bind_ip || '')
      setLogLevel(c.logging?.level || 'INFO')
      setSelectedInterface(c.network?.interface || '')

      // Timezone
      setSelectedTimezone(tz.name || 'Asia/Tehran')
      setTimezoneOffset(tz.offset ?? 3.5)
    } catch {
      // Ignore load errors
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  // ── Auto-compute schedule when active hours or timezone change ──────────

  const handleComputeSchedule = useCallback(async () => {
    setComputingSchedule(true)
    try {
      const result = await computeSchedule(wakeHour, sleepHour, timezoneOffset)
      setSchedulePreview({
        weights: result.weights,
        labels: ['00–06', '06–12', '12–18', '18–24'],
      })
    } catch {
      // Ignore
    } finally {
      setComputingSchedule(false)
    }
  }, [wakeHour, sleepHour, timezoneOffset])

  useEffect(() => {
    if (mode === 'simple') {
      handleComputeSchedule()
    }
  }, [mode, wakeHour, sleepHour, timezoneOffset, handleComputeSchedule])

  // ── Save config ────────────────────────────────────────────────────────────

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    try {
      const updates: Record<string, any> = {
        'traffic.daily_target_bytes': Math.round(parseFloat(dailyTargetGb) * 1024 ** 3),
        'traffic.download.speed_cap_bps': Math.round(parseFloat(speedCapMbps) * 1024 * 1024),
        'traffic.download.max_concurrent': parseInt(maxConcurrent),
        'traffic.browsing.use_playwright': usePlaywright,
        'traffic.browsing.browse_depth': parseInt(browseDepth),
        'network.interface': selectedInterface,
        'timezone.name': selectedTimezone,
        'timezone.offset': timezoneOffset,
      }

      if (mode === 'simple' && schedulePreview) {
        // Apply auto-computed schedule weights from human-behavior model
        updates['traffic.schedule.weights'] = schedulePreview.weights
      }

      if (mode === 'advanced') {
        updates['traffic.daily_variance'] = parseFloat(dailyVariance)
        updates['traffic.schedule.weights'] = schedWeights.split(',').map(Number)
        updates['traffic.download.pause_probability'] = parseFloat(pauseProb)
        updates['traffic.download.pause_range'] = [parseInt(pauseMin), parseInt(pauseMax)]
        updates['traffic.browsing.delay_range'] = [parseInt(browseDelayMin), parseInt(browseDelayMax)]
        updates['traffic.browsing.max_internal_links'] = parseInt(browseMaxLinks)
        updates['network.bind_ip'] = bindIp
        updates['logging.level'] = logLevel
      }

      await updateConfig(updates)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
      await refresh()
    } catch {
      // Ignore
    } finally {
      setSaving(false)
    }
  }

  // ── Change password ────────────────────────────────────────────────────────

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPwMsg('')
    try {
      await changePassword(currentPw, newPw)
      setPwMsg('Password changed successfully')
      setCurrentPw('')
      setNewPw('')
    } catch (err: any) {
      setPwMsg(err.message || 'Failed to change password')
    }
  }

  // ── Timezone change handler ────────────────────────────────────────────────

  const handleTimezoneChange = (tz: string) => {
    setSelectedTimezone(tz)
    const offset = timezones[tz]
    if (offset !== undefined) {
      setTimezoneOffset(offset)
    }
  }

  // ── Render helpers ─────────────────────────────────────────────────────────

  const formatHour = (h: number): string => {
    if (h === 0 || h === 24) return '12:00 AM'
    if (h === 12) return '12:00 PM'
    if (h < 12) return `${h}:00 AM`
    return `${h - 12}:00 PM`
  }

  const renderWeightBar = (weight: number, label: string) => {
    const pct = Math.round(weight * 100)
    return (
      <div key={label} className="flex items-center gap-2">
        <span className="text-xs w-12 text-right tabular-nums" style={{ color: 'var(--color-text-muted)' }}>
          {label}
        </span>
        <div className="flex-1 h-5 rounded-md overflow-hidden" style={{ background: 'var(--color-surface-offset)' }}>
          <div
            className="h-full rounded-md transition-all duration-500"
            style={{
              width: `${Math.max(pct, 2)}%`,
              background: pct > 20 ? 'var(--color-primary)' : 'var(--color-text-faint)',
            }}
          />
        </div>
        <span className="text-xs w-10 tabular-nums" style={{ color: 'var(--color-text-muted)' }}>
          {pct}%
        </span>
      </div>
    )
  }

  // ── Loading state ──────────────────────────────────────────────────────────

  if (!config) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Loading configuration...</div>
      </div>
    )
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header with mode toggle */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>Settings</h2>
          <p className="text-sm mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
            Configure traffic simulation parameters
          </p>
        </div>
        <div className="flex rounded-lg overflow-hidden" style={{ border: '1px solid var(--color-border)' }}>
          <button
            onClick={() => setMode('simple')}
            className="px-4 py-2 text-sm font-medium transition-colors"
            style={{
              background: mode === 'simple' ? 'var(--color-primary)' : 'var(--color-surface)',
              color: mode === 'simple' ? 'var(--color-text-inverse)' : 'var(--color-text-muted)',
            }}
            data-testid="btn-mode-simple"
          >
            Simple
          </button>
          <button
            onClick={() => setMode('advanced')}
            className="px-4 py-2 text-sm font-medium transition-colors"
            style={{
              background: mode === 'advanced' ? 'var(--color-primary)' : 'var(--color-surface)',
              color: mode === 'advanced' ? 'var(--color-text-inverse)' : 'var(--color-text-muted)',
            }}
            data-testid="btn-mode-advanced"
          >
            Advanced
          </button>
        </div>
      </div>

      {/* ── Timezone selector ─────────────────────────────────────────────── */}
      <Card>
        <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--color-text)' }}>
          <Globe size={16} /> Timezone
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="block text-sm font-medium" style={{ color: 'var(--color-text)' }}>
              Timezone
            </label>
            <select
              value={selectedTimezone}
              onChange={(e) => handleTimezoneChange(e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm"
              style={{
                background: 'var(--color-surface-2)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text)',
              }}
              data-testid="select-timezone"
            >
              {Object.entries(timezones).map(([name, offset]) => (
                <option key={name} value={name}>
                  {name} (UTC{offset >= 0 ? '+' : ''}{offset})
                </option>
              ))}
            </select>
          </div>
          <Input
            label="UTC Offset"
            type="number"
            step="0.5"
            value={String(timezoneOffset)}
            onChange={(e) => setTimezoneOffset(parseFloat(e.target.value) || 0)}
            hint="Auto-filled from timezone selection"
            data-testid="input-tz-offset"
          />
        </div>
      </Card>

      {/* ── Network Interface ─────────────────────────────────────────── */}
      <Card>
        <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--color-text)' }}>
          <Wifi size={16} /> Network Interface
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="block text-sm font-medium" style={{ color: 'var(--color-text)' }}>
              Interface
            </label>
            <select
              value={selectedInterface}
              onChange={(e) => setSelectedInterface(e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm"
              style={{
                background: 'var(--color-surface-2)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text)',
              }}
              data-testid="select-network-interface"
            >
              <option value="">Auto (Default)</option>
              {networkInterfaces.filter(nic => nic.is_up).map(nic => (
                <option key={nic.name} value={nic.name}>
                  {nic.name} — {nic.ip} ({nic.description})
                </option>
              ))}
            </select>
            <p className="text-xs" style={{ color: 'var(--color-text-faint)' }}>
              Select which network interface to use for outbound traffic
            </p>
          </div>
          <div className="space-y-1.5">
            <label className="block text-sm font-medium" style={{ color: 'var(--color-text)' }}>
              Browse Depth
            </label>
            <select
              value={browseDepth}
              onChange={(e) => setBrowseDepth(e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm"
              style={{
                background: 'var(--color-surface-2)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text)',
              }}
              data-testid="select-browse-depth"
            >
              <option value="1">1 Layer — Visit page only</option>
              <option value="2">2 Layers — Follow 1 link deep</option>
              <option value="3">3 Layers — Follow 2 links deep</option>
            </select>
            <p className="text-xs" style={{ color: 'var(--color-text-faint)' }}>
              How deep the browser engine navigates within each site
            </p>
          </div>
        </div>
      </Card>

      {/* ── Traffic Configuration ──────────────────────────────────────────── */}
      <Card>
        <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--color-text)' }}>
          Traffic Configuration
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Daily Target (GB)"
            type="number"
            step="0.1"
            value={dailyTargetGb}
            onChange={(e) => setDailyTargetGb(e.target.value)}
            hint={`= ${formatBytes(parseFloat(dailyTargetGb || '0') * 1024 ** 3)}`}
            data-testid="input-daily-target"
          />
          <Input
            label="Speed Cap (MB/s)"
            type="number"
            step="0.1"
            value={speedCapMbps}
            onChange={(e) => setSpeedCapMbps(e.target.value)}
            hint="0 = unlimited"
            data-testid="input-speed-cap"
          />
          <Input
            label="Max Concurrent Downloads"
            type="number"
            min="1"
            max="10"
            value={maxConcurrent}
            onChange={(e) => setMaxConcurrent(e.target.value)}
            data-testid="input-max-concurrent"
          />
          <div className="space-y-1.5">
            <label className="block text-sm font-medium" style={{ color: 'var(--color-text)' }}>
              Browser Engine
            </label>
            <button
              onClick={() => setUsePlaywright(!usePlaywright)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg w-full text-sm transition-colors"
              style={{
                background: 'var(--color-surface-2)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text)',
              }}
              data-testid="btn-toggle-playwright"
            >
              <div
                className="w-8 h-5 rounded-full transition-colors relative"
                style={{ background: usePlaywright ? 'var(--color-primary)' : 'var(--color-surface-offset)' }}
              >
                <div
                  className="w-3.5 h-3.5 rounded-full absolute top-0.5 transition-all"
                  style={{
                    background: 'white',
                    left: usePlaywright ? '16px' : '3px',
                  }}
                />
              </div>
              {usePlaywright ? 'Playwright (Chromium)' : 'aiohttp (Lightweight)'}
            </button>
            <p className="text-xs" style={{ color: 'var(--color-text-faint)' }}>
              Playwright is harder to detect but requires extra setup
            </p>
          </div>
        </div>
      </Card>

      {/* ── Simple Mode: Human-Behavior Active Hours ──────────────────────── */}
      {mode === 'simple' && (
        <Card>
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--color-text)' }}>
            <Clock size={16} /> Human-Behavior Schedule
          </h3>
          <p className="text-xs mb-4" style={{ color: 'var(--color-text-muted)' }}>
            Set your active hours and the schedule weights will be computed automatically
            to mimic realistic human browsing patterns.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
            {/* Wake hour */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium flex items-center gap-1.5" style={{ color: 'var(--color-text)' }}>
                <Sun size={14} /> Wake Up
              </label>
              <select
                value={wakeHour}
                onChange={(e) => setWakeHour(parseInt(e.target.value))}
                className="w-full rounded-lg px-3 py-2 text-sm"
                style={{
                  background: 'var(--color-surface-2)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text)',
                }}
                data-testid="select-wake-hour"
              >
                {Array.from({ length: 24 }, (_, i) => (
                  <option key={i} value={i}>{formatHour(i)}</option>
                ))}
              </select>
              <p className="text-xs" style={{ color: 'var(--color-text-faint)' }}>
                Start of daily activity
              </p>
            </div>

            {/* Sleep hour */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium flex items-center gap-1.5" style={{ color: 'var(--color-text)' }}>
                <Moon size={14} /> Sleep
              </label>
              <select
                value={sleepHour}
                onChange={(e) => setSleepHour(parseInt(e.target.value))}
                className="w-full rounded-lg px-3 py-2 text-sm"
                style={{
                  background: 'var(--color-surface-2)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text)',
                }}
                data-testid="select-sleep-hour"
              >
                {Array.from({ length: 25 }, (_, i) => (
                  <option key={i} value={i}>{i === 24 ? '12:00 AM (midnight)' : formatHour(i)}</option>
                ))}
              </select>
              <p className="text-xs" style={{ color: 'var(--color-text-faint)' }}>
                End of daily activity
              </p>
            </div>
          </div>

          {/* Schedule weight preview */}
          {schedulePreview && (
            <div className="space-y-2">
              <p className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
                Computed Schedule Weights (UTC)
                {computingSchedule && ' — computing...'}
              </p>
              <div className="space-y-1.5">
                {schedulePreview.weights.map((w, i) =>
                  renderWeightBar(w, schedulePreview.labels[i])
                )}
              </div>
              <p className="text-xs mt-2" style={{ color: 'var(--color-text-faint)' }}>
                Active: {formatHour(wakeHour)} – {sleepHour === 24 ? '12:00 AM' : formatHour(sleepHour)} ({selectedTimezone})
              </p>
            </div>
          )}
        </Card>
      )}

      {/* ── Advanced settings ──────────────────────────────────────────────── */}
      {mode === 'advanced' && (
        <>
          <Card>
            <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--color-text)' }}>
              Schedule & Variance
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Daily Variance"
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={dailyVariance}
                onChange={(e) => setDailyVariance(e.target.value)}
                hint={`+/- ${(parseFloat(dailyVariance || '0') * 100).toFixed(0)}% randomness`}
              />
              <Input
                label="Schedule Weights (4 values)"
                value={schedWeights}
                onChange={(e) => setSchedWeights(e.target.value)}
                hint="[00-06, 06-12, 12-18, 18-24] — must sum to ~1.0"
              />
            </div>
          </Card>

          <Card>
            <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--color-text)' }}>
              Download Behaviour
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Input
                label="Pause Probability"
                type="number"
                step="0.05"
                min="0"
                max="1"
                value={pauseProb}
                onChange={(e) => setPauseProb(e.target.value)}
                hint={`${(parseFloat(pauseProb || '0') * 100).toFixed(0)}% chance`}
              />
              <Input
                label="Pause Min (sec)"
                type="number"
                value={pauseMin}
                onChange={(e) => setPauseMin(e.target.value)}
              />
              <Input
                label="Pause Max (sec)"
                type="number"
                value={pauseMax}
                onChange={(e) => setPauseMax(e.target.value)}
              />
            </div>
          </Card>

          <Card>
            <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--color-text)' }}>
              Browsing Behaviour
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Input
                label="Delay Min (sec)"
                type="number"
                value={browseDelayMin}
                onChange={(e) => setBrowseDelayMin(e.target.value)}
              />
              <Input
                label="Delay Max (sec)"
                type="number"
                value={browseDelayMax}
                onChange={(e) => setBrowseDelayMax(e.target.value)}
              />
              <Input
                label="Max Internal Links"
                type="number"
                min="0"
                max="10"
                value={browseMaxLinks}
                onChange={(e) => setBrowseMaxLinks(e.target.value)}
              />
            </div>
          </Card>

          <Card>
            <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--color-text)' }}>
              Network & Logging
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Bind IP"
                placeholder="Leave empty for default"
                value={bindIp}
                onChange={(e) => setBindIp(e.target.value)}
                hint="Bind outbound traffic to a specific interface"
              />
              <div className="space-y-1.5">
                <label className="block text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                  Log Level
                </label>
                <select
                  value={logLevel}
                  onChange={(e) => setLogLevel(e.target.value)}
                  className="w-full rounded-lg px-3 py-2 text-sm"
                  style={{
                    background: 'var(--color-surface-2)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-text)',
                  }}
                >
                  <option value="DEBUG">DEBUG</option>
                  <option value="INFO">INFO</option>
                  <option value="WARNING">WARNING</option>
                  <option value="ERROR">ERROR</option>
                </select>
              </div>
            </div>
          </Card>
        </>
      )}

      {/* ── Save button ───────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <Button onClick={handleSave} disabled={saving} data-testid="btn-save-settings">
          {saved ? <Check size={16} /> : <Save size={16} />}
          {saving ? 'Saving...' : saved ? 'Saved' : 'Save Changes'}
        </Button>
        <span className="text-xs" style={{ color: 'var(--color-text-faint)' }}>
          Changes apply immediately — no restart required
        </span>
      </div>

      {/* ── Password change ───────────────────────────────────────────────── */}
      <Card>
        <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--color-text)' }}>
          <Lock size={16} /> Change Password
        </h3>
        <form onSubmit={handleChangePassword} className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Current Password"
              type="password"
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
            />
            <Input
              label="New Password"
              type="password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-3">
            <Button type="submit" variant="secondary" size="sm" disabled={!currentPw || !newPw}>
              Update Password
            </Button>
            {pwMsg && (
              <span className="text-xs" style={{
                color: pwMsg.includes('success') ? 'var(--color-success)' : 'var(--color-error)'
              }}>
                {pwMsg}
              </span>
            )}
          </div>
        </form>
      </Card>
    </div>
  )
}
