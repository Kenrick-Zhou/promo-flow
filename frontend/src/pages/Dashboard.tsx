import { useEffect, useRef, useState, type TouchEvent } from 'react'
import { clsx } from 'clsx'
import ContentGrid from '@/components/content/ContentGrid'
import ContentDetail from '@/components/content/ContentDetail'
import LoadingDots from '@/components/ui/LoadingDots'
import Toast from '@/components/ui/Toast'
import { useContent } from '@/hooks/useContent'
import { useSearch } from '@/hooks/useSearch'
import type { Content } from '@/types'

const DISCOVERY_TABS = [
  { key: 'latest', label: '最新' },
  { key: 'popular', label: '热门' },
  { key: 'all', label: '全部' },
] as const

type DiscoveryTabKey = (typeof DISCOVERY_TABS)[number]['key']

const TAB_COUNT = DISCOVERY_TABS.length
const TRACK_STEP_PERCENT = 100 / TAB_COUNT
const SWIPE_ACTIVATION_DISTANCE = 10

export default function Dashboard() {
  const { listContents, loading, recordView, recordDownload } = useContent()
  const { semanticSearch, loading: searchLoading } = useSearch()
  const [items, setItems] = useState<Content[]>([])
  const [activeTab, setActiveTab] = useState<DiscoveryTabKey>('latest')
  const [query, setQuery] = useState('')
  const [isSearchMode, setIsSearchMode] = useState(false)
  const [selectedContent, setSelectedContent] = useState<Content | null>(null)
  const [showDownloadToast, setShowDownloadToast] = useState(false)
  const [dragOffset, setDragOffset] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const contentViewportRef = useRef<HTMLDivElement | null>(null)
  const touchSessionRef = useRef<{
    startX: number
    startY: number
    deltaX: number
    isHorizontal: boolean
  } | null>(null)

  useEffect(() => {
    if (isSearchMode) return
    listContents({ status: 'approved' }).then((r) => {
      setItems(r.items)
    })
  }, [listContents, isSearchMode])

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

  function handleTabChange(nextTab: DiscoveryTabKey) {
    setActiveTab(nextTab)
    setDragOffset(0)
    setIsDragging(false)
  }

  function handleTouchStart(event: TouchEvent<HTMLDivElement>) {
    const touch = event.touches[0]

    touchSessionRef.current = {
      startX: touch.clientX,
      startY: touch.clientY,
      deltaX: 0,
      isHorizontal: false,
    }
  }

  function handleTouchMove(event: TouchEvent<HTMLDivElement>) {
    const session = touchSessionRef.current

    if (!session) {
      return
    }

    const touch = event.touches[0]
    const deltaX = touch.clientX - session.startX
    const deltaY = touch.clientY - session.startY

    if (!session.isHorizontal) {
      if (Math.abs(deltaY) > Math.abs(deltaX) || Math.abs(deltaX) < SWIPE_ACTIVATION_DISTANCE) {
        return
      }

      session.isHorizontal = true
    }

    session.deltaX = deltaX
    setIsDragging(true)

    const activeTabIndex = DISCOVERY_TABS.findIndex((tab) => tab.key === activeTab)
    const isEdgeSwipe =
      (activeTabIndex === 0 && deltaX > 0) || (activeTabIndex === TAB_COUNT - 1 && deltaX < 0)

    setDragOffset(isEdgeSwipe ? deltaX * 0.35 : deltaX)
  }

  function handleTouchEnd() {
    const session = touchSessionRef.current
    const viewportWidth = contentViewportRef.current?.clientWidth ?? 1

    if (!session) {
      return
    }

    if (!session.isHorizontal) {
      touchSessionRef.current = null
      setDragOffset(0)
      setIsDragging(false)
      return
    }

    const threshold = viewportWidth * 0.18
    const activeTabIndex = DISCOVERY_TABS.findIndex((tab) => tab.key === activeTab)

    if (session.deltaX <= -threshold && activeTabIndex < TAB_COUNT - 1) {
      setActiveTab(DISCOVERY_TABS[activeTabIndex + 1].key)
    } else if (session.deltaX >= threshold && activeTabIndex > 0) {
      setActiveTab(DISCOVERY_TABS[activeTabIndex - 1].key)
    }

    touchSessionRef.current = null
    setDragOffset(0)
    setIsDragging(false)
  }

  const isLoading = loading || searchLoading
  const activeTabIndex = DISCOVERY_TABS.findIndex((tab) => tab.key === activeTab)
  const contentSection = isLoading ? (
    <LoadingDots label="素材广场加载中…" />
  ) : (
    <ContentGrid items={items} onSelect={handleSelectContent} onDownload={handleDownload} />
  )
  const trackTransform = `translate3d(calc(-${activeTabIndex * TRACK_STEP_PERCENT}% + ${dragOffset}px), 0, 0)`

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">素材广场</h1>
      </div>

      <div className="sticky top-0 z-20 -mx-4 mb-6 space-y-3 border-b border-gray-200/70 bg-gray-50/95 px-4 py-2 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-gray-50/80 dark:border-gray-800/80 dark:bg-gray-900/95 dark:supports-[backdrop-filter]:bg-gray-900/80">
        {/* 搜索栏 */}
        <form onSubmit={handleSearch} className="flex gap-3">
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
            className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:focus:ring-offset-gray-900"
          >
            {searchLoading ? '搜索中...' : '搜索'}
          </button>
        </form>

        <div className="grid w-full grid-cols-3 rounded-2xl border border-gray-200 bg-white p-1 shadow-sm dark:border-gray-700 dark:bg-gray-800">
          {DISCOVERY_TABS.map((tab) => {
            const isActive = tab.key === activeTab

            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => handleTabChange(tab.key)}
                className={clsx(
                  'rounded-lg px-4 py-2 text-center text-sm font-medium transition-all duration-300',
                  isActive
                    ? 'bg-purple-600 text-white shadow-sm'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white',
                )}
                aria-pressed={isActive}
              >
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>

      <div
        ref={contentViewportRef}
        className="overflow-hidden touch-pan-y"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onTouchCancel={handleTouchEnd}
      >
        <div
          className={clsx(
            'flex will-change-transform',
            isDragging ? 'transition-none' : 'transition-transform duration-300 ease-out',
          )}
          style={{ width: `${TAB_COUNT * 100}%`, transform: trackTransform }}
        >
          {DISCOVERY_TABS.map((tab) => (
            <div
              key={tab.key}
              className={clsx('shrink-0 px-0', isDragging && 'pointer-events-none')}
              style={{ width: `${100 / TAB_COUNT}%` }}
              aria-hidden={tab.key !== activeTab}
            >
              {contentSection}
            </div>
          ))}
        </div>
      </div>

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
