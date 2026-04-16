import { useEffect, useState } from 'react'
import ContentGrid from '@/components/content/ContentGrid'
import ContentDetail from '@/components/content/ContentDetail'
import LoadingDots from '@/components/ui/LoadingDots'
import Toast from '@/components/ui/Toast'
import { useContent } from '@/hooks/useContent'
import { useSearch } from '@/hooks/useSearch'
import type { Content, ContentType } from '@/types'

const typeOptions: { value: ContentType | ''; label: string }[] = [
  { value: '', label: '全部' },
  { value: 'image', label: '图片' },
  { value: 'video', label: '视频' },
]

export default function Dashboard() {
  const { listContents, loading, recordView, recordDownload } = useContent()
  const { semanticSearch, loading: searchLoading } = useSearch()
  const [items, setItems] = useState<Content[]>([])
  const [total, setTotal] = useState(0)
  const [contentType, setContentType] = useState<ContentType | ''>('')
  const [query, setQuery] = useState('')
  const [isSearchMode, setIsSearchMode] = useState(false)
  const [selectedContent, setSelectedContent] = useState<Content | null>(null)
  const [showDownloadToast, setShowDownloadToast] = useState(false)

  useEffect(() => {
    if (isSearchMode) return
    listContents({ status: 'approved', content_type: contentType || undefined }).then((r) => {
      setItems(r.items)
      setTotal(r.total)
    })
  }, [contentType, listContents, isSearchMode])

  useEffect(() => {
    if (!showDownloadToast) {
      return
    }

    const timeoutId = window.setTimeout(() => {
      setShowDownloadToast(false)
    }, 3000)

    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [showDownloadToast])

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) {
      setIsSearchMode(false)
      return
    }
    setIsSearchMode(true)
    const results = await semanticSearch(query)
    setItems(results.map((r) => r.content))
    setTotal(results.length)
  }

  function handleClearSearch() {
    setQuery('')
    setIsSearchMode(false)
  }

  function handleSelectContent(content: Content) {
    setSelectedContent(content)
    recordView(content.id).then(() => {
      // Update local view count optimistically
      setItems((prev) =>
        prev.map((c) => (c.id === content.id ? { ...c, view_count: c.view_count + 1 } : c)),
      )
    })
  }

  async function handleDownload(content: Content) {
    try {
      await recordDownload(content.id)
      setItems((prev) =>
        prev.map((c) => (c.id === content.id ? { ...c, download_count: c.download_count + 1 } : c)),
      )
      setShowDownloadToast(true)
    } catch {
      setShowDownloadToast(false)
    }
  }

  const isLoading = loading || searchLoading

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">素材广场</h1>
        <span className="rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-300">
          共 {total} 个素材
        </span>
      </div>

      {/* 搜索栏 */}
      <form onSubmit={handleSearch} className="flex gap-3 mb-4">
        <div className="relative flex-1">
          <input
            className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-700 shadow-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
            placeholder="搜索素材，例如：夏季促销图片"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {isSearchMode && (
            <button
              type="button"
              onClick={handleClearSearch}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md px-2 py-1 text-xs text-gray-400 transition hover:text-gray-600 dark:hover:text-gray-300"
            >
              清除
            </button>
          )}
        </div>
        <button
          type="submit"
          disabled={isLoading}
          className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed dark:focus:ring-offset-gray-900"
        >
          {searchLoading ? '搜索中...' : '搜索'}
        </button>
      </form>

      {/* 类型筛选 */}
      {!isSearchMode && (
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-gray-700">
            {typeOptions.map((o) => (
              <button
                key={o.value}
                type="button"
                onClick={() => setContentType(o.value as ContentType | '')}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  contentType === o.value
                    ? 'bg-white text-purple-700 shadow-sm dark:bg-gray-800 dark:text-purple-300'
                    : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'
                }`}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {isLoading ? (
        <LoadingDots label="素材广场加载中…" />
      ) : (
        <ContentGrid items={items} onSelect={handleSelectContent} onDownload={handleDownload} />
      )}

      {selectedContent && (
        <ContentDetail content={selectedContent} onClose={() => setSelectedContent(null)} />
      )}

      <Toast
        open={showDownloadToast}
        title="已通过方小集Bot发送"
        description="请查看您的飞书消息"
      />
    </div>
  )
}
