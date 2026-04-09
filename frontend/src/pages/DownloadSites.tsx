import { useState, useEffect, useCallback, useRef } from 'react'
import { Card } from '@/components/Card'
import Button from '@/components/Button'
import Input from '@/components/Input'
import { formatBytes } from '@/lib/utils'
import {
  getDownloadSites,
  addDownloadSite,
  updateDownloadSite,
  deleteDownloadSite,
  importDownloadSites,
  exportDownloadSites,
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
} from 'lucide-react'

// ── Component ────────────────────────────────────────────────────────────────

export default function DownloadSites() {
  const [sites, setSites] = useState<Site[]>([])
  const [url, setUrl] = useState('')
  const [sizeBytes, setSizeBytes] = useState('')
  const [adding, setAdding] = useState(false)

  // Import / Export
  const [importing, setImporting] = useState(false)
  const [importMsg, setImportMsg] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // ── Data loading ───────────────────────────────────────────────────────────

  const refresh = useCallback(async () => {
    try {
      const data = await getDownloadSites()
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
      await addDownloadSite(url.trim(), parseInt(sizeBytes) || 0)
      setUrl('')
      setSizeBytes('')
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
      await updateDownloadSite(site.id, { enabled: !site.enabled })
      await refresh()
    } catch {
      // Ignore
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteDownloadSite(id)
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

      const result = await importDownloadSites(urls)
      setImportMsg(`Imported ${result.added} new sites (${result.total_input} total in file)`)
      await refresh()
    } catch (err: any) {
      setImportMsg(err.message || 'Failed to import')
    } finally {
      setImporting(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  // ── Export ─────────────────────────────────────────────────────────────────

  const handleExport = async (format: 'json' | 'csv') => {
    try {
      const result = await exportDownloadSites()
      let content: string
      let mimeType: string
      let filename: string

      if (format === 'json') {
        content = JSON.stringify(
          result.sites.map(s => ({
            url: s.url,
            size_bytes: s.size_bytes || 0,
            enabled: !!s.enabled,
          })),
          null,
          2,
        )
        mimeType = 'application/json'
        filename = 'download-sites.json'
      } else {
        const lines = [
          'url,size_bytes,enabled',
          ...result.sites.map(s => `${s.url},${s.size_bytes || 0},${s.enabled ? 'true' : 'false'}`),
        ]
        content = lines.join('\n')
        mimeType = 'text/csv'
        filename = 'download-sites.csv'
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

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>Download Sites</h2>
        <p className="text-sm mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
          Manage files to download for traffic generation
        </p>
      </div>

      {/* ── Add form ──────────────────────────────────────────────────────── */}
      <Card>
        <form onSubmit={handleAdd} className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <Input
              placeholder="https://example.com/file.bin"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              data-testid="input-download-url"
            />
          </div>
          <div className="w-full sm:w-40">
            <Input
              placeholder="Size (bytes)"
              type="number"
              value={sizeBytes}
              onChange={(e) => setSizeBytes(e.target.value)}
              data-testid="input-download-size"
            />
          </div>
          <Button type="submit" disabled={adding || !url.trim()} data-testid="btn-add-download">
            <Plus size={16} /> Add
          </Button>
        </form>
      </Card>

      {/* ── Import / Export toolbar ────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2">
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
          data-testid="btn-import-download"
        >
          <Upload size={14} />
          {importing ? 'Importing...' : 'Import'}
        </Button>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => handleExport('csv')}
          data-testid="btn-export-csv-download"
        >
          <Download size={14} /> Export CSV
        </Button>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => handleExport('json')}
          data-testid="btn-export-json-download"
        >
          <Download size={14} /> Export JSON
        </Button>

        {importMsg && (
          <span className="text-xs self-center" style={{ color: 'var(--color-text-muted)' }}>
            {importMsg}
          </span>
        )}
      </div>

      {/* ── Sites list ────────────────────────────────────────────────────── */}
      <Card padding={false}>
        {sites.length === 0 ? (
          <div className="p-8 text-center" style={{ color: 'var(--color-text-muted)' }}>
            <p className="text-sm">No download sites configured yet.</p>
            <p className="text-xs mt-1" style={{ color: 'var(--color-text-faint)' }}>
              Add a file URL above or import from a file.
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
                  data-testid={`toggle-download-${site.id}`}
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
                  <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-faint)' }}>
                    {site.size_bytes ? formatBytes(site.size_bytes) : 'Size unknown'}
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
                  data-testid={`delete-download-${site.id}`}
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
