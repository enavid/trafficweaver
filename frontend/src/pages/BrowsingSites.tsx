import { useState, useEffect, useCallback, useRef } from 'react'
import { Card } from '@/components/Card'
import Button from '@/components/Button'
import Input from '@/components/Input'
import {
  getBrowsingSites,
  addBrowsingSite,
  updateBrowsingSite,
  deleteBrowsingSite,
  importBrowsingSites,
  exportBrowsingSites,
  getIranianPresets,
  loadIranianPreset,
  type Site,
} from '@/lib/api'
import {
  Plus,
  Trash2,
  ExternalLink,
  ToggleLeft,
  ToggleRight,
  Upload,
  Download,
  Flag,
  CheckSquare,
  Square,
  Loader2,
} from 'lucide-react'

// ── Types ────────────────────────────────────────────────────────────────────

interface PresetInfo {
  total: number
  categories: Record<string, number>
  sites: Record<string, string[]>
}

// ── Component ────────────────────────────────────────────────────────────────

export default function BrowsingSites() {
  const [sites, setSites] = useState<Site[]>([])
  const [url, setUrl] = useState('')
  const [adding, setAdding] = useState(false)

  // Import / Export
  const [importing, setImporting] = useState(false)
  const [importMsg, setImportMsg] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Iranian preset
  const [presetInfo, setPresetInfo] = useState<PresetInfo | null>(null)
  const [presetOpen, setPresetOpen] = useState(false)
  const [selectedCategories, setSelectedCategories] = useState<Set<string>>(new Set())
  const [loadingPreset, setLoadingPreset] = useState(false)
  const [presetMsg, setPresetMsg] = useState('')

  // ── Data loading ───────────────────────────────────────────────────────────

  const refresh = useCallback(async () => {
    try {
      const data = await getBrowsingSites()
      setSites(data)
    } catch {
      // Ignore
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  // ── Add single site ────────────────────────────────────────────────────────

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return
    setAdding(true)
    try {
      await addBrowsingSite(url.trim())
      setUrl('')
      await refresh()
    } catch {
      // Ignore
    } finally {
      setAdding(false)
    }
  }

  // ── Toggle / Delete ────────────────────────────────────────────────────────

  const handleToggle = async (site: Site) => {
    try {
      await updateBrowsingSite(site.id, { enabled: !site.enabled })
      await refresh()
    } catch {
      // Ignore
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteBrowsingSite(id)
      await refresh()
    } catch {
      // Ignore
    }
  }

  // ── Import (file upload) ───────────────────────────────────────────────────

  const handleImportClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setImporting(true)
    setImportMsg('')

    try {
      const text = await file.text()
      let urls: string[] = []

      if (file.name.endsWith('.json')) {
        const parsed = JSON.parse(text)
        // Support both array of strings and array of objects with url field
        if (Array.isArray(parsed)) {
          urls = parsed.map((item: any) => (typeof item === 'string' ? item : item.url || '')).filter(Boolean)
        }
      } else {
        // CSV or plain text — one URL per line
        urls = text
          .split(/[\r\n]+/)
          .map((line: string) => line.trim())
          .filter((line: string) => line && !line.startsWith('#'))
      }

      if (urls.length === 0) {
        setImportMsg('No valid URLs found in the file')
        return
      }

      const result = await importBrowsingSites(urls)
      setImportMsg(`Imported ${result.added} new sites (${result.total_input} total in file)`)
      await refresh()
    } catch (err: any) {
      setImportMsg(err.message || 'Failed to import')
    } finally {
      setImporting(false)
      // Reset input so same file can be selected again
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  // ── Export ─────────────────────────────────────────────────────────────────

  const handleExport = async (format: 'json' | 'csv') => {
    try {
      const result = await exportBrowsingSites()
      let content: string
      let mimeType: string
      let filename: string

      if (format === 'json') {
        content = JSON.stringify(result.sites.map(s => ({ url: s.url, enabled: !!s.enabled })), null, 2)
        mimeType = 'application/json'
        filename = 'browsing-sites.json'
      } else {
        const lines = ['url,enabled', ...result.sites.map(s => `${s.url},${s.enabled ? 'true' : 'false'}`)]
        content = lines.join('\n')
        mimeType = 'text/csv'
        filename = 'browsing-sites.csv'
      }

      const blob = new Blob([content], { type: mimeType })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = filename
      a.click()
      URL.revokeObjectURL(a.href)
    } catch {
      // Ignore
    }
  }

  // ── Iranian Preset ─────────────────────────────────────────────────────────

  const handleOpenPreset = async () => {
    if (!presetInfo) {
      try {
        const info = await getIranianPresets()
        setPresetInfo(info)
        setSelectedCategories(new Set(Object.keys(info.categories)))
      } catch {
        // Ignore
      }
    }
    setPresetOpen(!presetOpen)
    setPresetMsg('')
  }

  const toggleCategory = (cat: string) => {
    setSelectedCategories(prev => {
      const next = new Set(prev)
      if (next.has(cat)) {
        next.delete(cat)
      } else {
        next.add(cat)
      }
      return next
    })
  }

  const selectAllCategories = () => {
    if (presetInfo) {
      setSelectedCategories(new Set(Object.keys(presetInfo.categories)))
    }
  }

  const deselectAllCategories = () => {
    setSelectedCategories(new Set())
  }

  const handleLoadPreset = async () => {
    setLoadingPreset(true)
    setPresetMsg('')
    try {
      const cats = selectedCategories.size === Object.keys(presetInfo?.categories || {}).length
        ? undefined
        : Array.from(selectedCategories)
      const result = await loadIranianPreset(cats)
      setPresetMsg(`Added ${result.added} sites (${result.skipped} already existed)`)
      await refresh()
    } catch (err: any) {
      setPresetMsg(err.message || 'Failed to load preset')
    } finally {
      setLoadingPreset(false)
    }
  }

  const formatCategory = (cat: string): string => {
    return cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>Browsing Sites</h2>
        <p className="text-sm mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
          Manage websites to visit for simulated browsing traffic
        </p>
      </div>

      {/* ── Add form ──────────────────────────────────────────────────────── */}
      <Card>
        <form onSubmit={handleAdd} className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <Input
              placeholder="https://www.example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              data-testid="input-browsing-url"
            />
          </div>
          <Button type="submit" disabled={adding || !url.trim()} data-testid="btn-add-browsing">
            <Plus size={16} /> Add
          </Button>
        </form>
      </Card>

      {/* ── Import / Export / Preset toolbar ───────────────────────────────── */}
      <div className="flex flex-wrap gap-2">
        {/* Hidden file input for import */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.json,.txt"
          className="hidden"
          onChange={handleFileSelected}
        />

        <Button
          variant="secondary"
          size="sm"
          onClick={handleImportClick}
          disabled={importing}
          data-testid="btn-import-browsing"
        >
          <Upload size={14} />
          {importing ? 'Importing...' : 'Import'}
        </Button>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => handleExport('csv')}
          data-testid="btn-export-csv-browsing"
        >
          <Download size={14} /> Export CSV
        </Button>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => handleExport('json')}
          data-testid="btn-export-json-browsing"
        >
          <Download size={14} /> Export JSON
        </Button>

        <Button
          variant={presetOpen ? 'primary' : 'secondary'}
          size="sm"
          onClick={handleOpenPreset}
          data-testid="btn-iranian-preset"
        >
          <Flag size={14} /> Iranian Sites Preset
        </Button>

        {importMsg && (
          <span className="text-xs self-center" style={{ color: 'var(--color-text-muted)' }}>
            {importMsg}
          </span>
        )}
      </div>

      {/* ── Iranian Preset panel ──────────────────────────────────────────── */}
      {presetOpen && presetInfo && (
        <Card>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                Iranian Websites — {presetInfo.total} sites in {Object.keys(presetInfo.categories).length} categories
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={selectAllCategories}
                  className="text-xs px-2 py-1 rounded transition-colors"
                  style={{ color: 'var(--color-primary)' }}
                >
                  Select all
                </button>
                <button
                  onClick={deselectAllCategories}
                  className="text-xs px-2 py-1 rounded transition-colors"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  Deselect all
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {Object.entries(presetInfo.categories).map(([cat, count]) => (
                <button
                  key={cat}
                  onClick={() => toggleCategory(cat)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors text-left"
                  style={{
                    background: selectedCategories.has(cat) ? 'var(--color-primary-highlight)' : 'var(--color-surface-2)',
                    border: `1px solid ${selectedCategories.has(cat) ? 'var(--color-primary)' : 'var(--color-border)'}`,
                    color: 'var(--color-text)',
                  }}
                  data-testid={`preset-cat-${cat}`}
                >
                  {selectedCategories.has(cat)
                    ? <CheckSquare size={14} style={{ color: 'var(--color-primary)' }} />
                    : <Square size={14} style={{ color: 'var(--color-text-faint)' }} />
                  }
                  <span className="truncate">{formatCategory(cat)}</span>
                  <span className="text-xs ml-auto" style={{ color: 'var(--color-text-faint)' }}>
                    {count}
                  </span>
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3">
              <Button
                size="sm"
                onClick={handleLoadPreset}
                disabled={loadingPreset || selectedCategories.size === 0}
                data-testid="btn-load-preset"
              >
                {loadingPreset ? <Loader2 size={14} className="animate-spin" /> : <Flag size={14} />}
                {loadingPreset ? 'Loading...' : `Load ${selectedCategories.size} categories`}
              </Button>
              {presetMsg && (
                <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                  {presetMsg}
                </span>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* ── Sites list ────────────────────────────────────────────────────── */}
      <Card padding={false}>
        {sites.length === 0 ? (
          <div className="p-8 text-center" style={{ color: 'var(--color-text-muted)' }}>
            <p className="text-sm">No browsing sites configured yet.</p>
            <p className="text-xs mt-1" style={{ color: 'var(--color-text-faint)' }}>
              Add a website URL above, import from a file, or load the Iranian preset.
            </p>
          </div>
        ) : (
          <div className="divide-y" style={{ borderColor: 'var(--color-border)' }}>
            {sites.map((site) => (
              <div
                key={site.id}
                className="flex items-center gap-4 px-5 py-3.5 transition-colors"
                style={{ opacity: site.enabled ? 1 : 0.5 }}
              >
                <button
                  onClick={() => handleToggle(site)}
                  className="flex-shrink-0 transition-colors"
                  style={{ color: site.enabled ? 'var(--color-success)' : 'var(--color-text-faint)' }}
                  title={site.enabled ? 'Disable' : 'Enable'}
                  data-testid={`toggle-browsing-${site.id}`}
                >
                  {site.enabled ? <ToggleRight size={24} /> : <ToggleLeft size={24} />}
                </button>
                <div className="flex-1 min-w-0">
                  <p
                    className="text-sm font-medium truncate"
                    style={{ color: 'var(--color-text)' }}
                    title={site.url}
                  >
                    {site.url}
                  </p>
                </div>
                <a
                  href={site.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-shrink-0 p-1.5 rounded-md transition-colors"
                  style={{ color: 'var(--color-text-muted)' }}
                  onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--color-primary)' }}
                  onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--color-text-muted)' }}
                >
                  <ExternalLink size={16} />
                </a>
                <button
                  onClick={() => handleDelete(site.id)}
                  className="flex-shrink-0 p-1.5 rounded-md transition-colors"
                  style={{ color: 'var(--color-text-muted)' }}
                  onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--color-error)' }}
                  onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--color-text-muted)' }}
                  data-testid={`delete-browsing-${site.id}`}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>

      <p className="text-xs" style={{ color: 'var(--color-text-faint)' }}>
        {sites.length} site{sites.length !== 1 ? 's' : ''} configured
        {' · '}
        {sites.filter(s => s.enabled).length} enabled
      </p>
    </div>
  )
}
