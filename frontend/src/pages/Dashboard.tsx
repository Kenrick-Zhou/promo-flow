import { useCallback, useEffect, useRef, useState, type TouchEvent } from 'react'
import { clsx } from 'clsx'
import ContentGrid from '@/components/content/ContentGrid'
import ContentDetail from '@/components/content/ContentDetail'
import PageHeader from '@/components/layout/PageHeader'
import LoadingDots from '@/components/ui/LoadingDots'
import Toast from '@/components/ui/Toast'
import { useContent } from '@/hooks/useContent'
import { useSearch } from '@/hooks/useSearch'
import { useSystem } from '@/hooks/useSystem'
import type { CategoryTree, Content } from '@/types'
import { getCurrentUserName, track } from '@/utils/track'

const DISCOVERY_TABS = [
  { key: 'latest', label: '最新' },
  { key: 'popular', label: '热门' },
  { key: 'all', label: '全部' },
] as const

type DiscoveryTabKey = (typeof DISCOVERY_TABS)[number]['key']

const TAB_COUNT = DISCOVERY_TABS.length
const TRACK_STEP_PERCENT = 100 / TAB_COUNT
const SWIPE_ACTIVATION_DISTANCE = 10
const PAGE_SIZE = 24

export default function Dashboard() {
  const { listContents, recordView, recordDownload } = useContent()
  const { semanticSearch, loading: searchLoading } = useSearch()
  const { listCategories } = useSystem()
  const [items, setItems] = useState<Content[]>([])
  const [total, setTotal] = useState(0)
  const [isInitialLoading, setIsInitialLoading] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [activeTab, setActiveTab] = useState<DiscoveryTabKey>('latest')
  const [query, setQuery] = useState('')
  const [isSearchMode, setIsSearchMode] = useState(false)
  const [selectedContent, setSelectedContent] = useState<Content | null>(null)
  const [showDownloadToast, setShowDownloadToast] = useState(false)
  const [dragOffset, setDragOffset] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const [categoryTree, setCategoryTree] = useState<CategoryTree[]>([])
  const [primaryCategoryId, setPrimaryCategoryId] = useState<number | null>(null)
  const [secondaryCategoryId, setSecondaryCategoryId] = useState<number | null>(null)
  const [contentTypeFilter, setContentTypeFilter] = useState<'image' | 'video' | null>(null)
  const contentViewportRef = useRef<HTMLDivElement | null>(null)
  const sentinelRef = useRef<HTMLDivElement | null>(null)
  const loadedCountRef = useRef(0)
  const totalRef = useRef(0)
  const requestIdRef = useRef(0)
  const touchSessionRef = useRef<{
    startX: number
    startY: number
    deltaX: number
    isHorizontal: boolean
  } | null>(null)

  useEffect(() => {
    listCategories()
      .then(setCategoryTree)
      .catch(() => {})
  }, [listCategories])

  // 进入素材广场埋点。
  useEffect(() => {
    track('home_visit', { user_name: getCurrentUserName() })
  }, [])

  const primaryCategories = categoryTree
  const secondaryCategories =
    primaryCategoryId !== null
      ? (categoryTree.find((c) => c.id === primaryCategoryId)?.children ?? [])
      : []

  const buildListParams = useCallback(
    (offset: number): Record<string, unknown> => {
      const params: Record<string, unknown> = {
        status: 'approved',
        offset,
        limit: PAGE_SIZE,
      }
      if (activeTab === 'popular') {
        params.sort_by = 'hot'
      }
      if (activeTab === 'all') {
        if (secondaryCategoryId !== null) {
          params.category_id = secondaryCategoryId
        } else if (primaryCategoryId !== null) {
          params.primary_category_id = primaryCategoryId
        }
        if (contentTypeFilter !== null) {
          params.content_type = contentTypeFilter
        }
      }
      return params
    },
    [activeTab, primaryCategoryId, secondaryCategoryId, contentTypeFilter],
  )

  // Reset & load first page whenever filters/tab change (skip in search mode)
  useEffect(() => {
    if (isSearchMode) return
    const reqId = ++requestIdRef.current
    setIsInitialLoading(true)
    setItems([])
    loadedCountRef.current = 0
    totalRef.current = 0
    setTotal(0)
    listContents(buildListParams(0))
      .then((r) => {
        if (reqId !== requestIdRef.current) return
        setItems(r.items)
        setTotal(r.total)
        loadedCountRef.current = r.items.length
        totalRef.current = r.total
      })
      .catch(() => {
        // listContents already surfaces error state internally
      })
      .finally(() => {
        if (reqId === requestIdRef.current) {
          setIsInitialLoading(false)
        }
      })
  }, [isSearchMode, buildListParams, listContents])

  const loadMore = useCallback(async () => {
    if (isSearchMode) return
    if (isLoadingMore || isInitialLoading) return
    if (loadedCountRef.current >= totalRef.current) return

    const reqId = ++requestIdRef.current
    setIsLoadingMore(true)
    try {
      const r = await listContents(buildListParams(loadedCountRef.current))
      if (reqId !== requestIdRef.current) return
      setItems((prev) => {
        const seen = new Set(prev.map((it) => it.id))
        const merged = [...prev, ...r.items.filter((it) => !seen.has(it.id))]
        loadedCountRef.current = merged.length
        return merged
      })
      totalRef.current = r.total
      setTotal(r.total)
    } catch {
      // ignore; next intersection will retry
    } finally {
      if (reqId === requestIdRef.current) {
        setIsLoadingMore(false)
      }
    }
  }, [isSearchMode, isLoadingMore, isInitialLoading, listContents, buildListParams])

  // Infinite scroll observer
  useEffect(() => {
    if (isSearchMode) return
    const el = sentinelRef.current
    if (!el) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          void loadMore()
        }
      },
      { rootMargin: '400px 0px' },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [isSearchMode, loadMore])

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
    track('search', {
      user_name: getCurrentUserName(),
      query,
      result_count: results.length,
    })
  }

  function handleClearSearch() {
    setQuery('')
    setIsSearchMode(false)
  }

  function handleSelectContent(content: Content) {
    setSelectedContent(content)
    track('content_view', {
      user_name: getCurrentUserName(),
      tab: activeTab,
      content_id: content.id,
      content_title: content.title ?? '',
      content_type: content.content_type,
    })
    recordView(content.id).then(() => {
      // Update local view count optimistically
      setItems((prev) =>
        prev.map((c) => (c.id === content.id ? { ...c, view_count: c.view_count + 1 } : c)),
      )
    })
  }

  async function handleDownload(content: Content) {
    track('content_download', {
      user_name: getCurrentUserName(),
      tab: activeTab,
      content_id: content.id,
      content_title: content.title ?? '',
      content_type: content.content_type,
    })
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
    if (nextTab !== 'all') {
      setPrimaryCategoryId(null)
      setSecondaryCategoryId(null)
      setContentTypeFilter(null)
    }
  }

  function handlePrimaryCategoryChange(value: string) {
    const id = value === '' ? null : Number(value)
    setPrimaryCategoryId(id)
    setSecondaryCategoryId(null)
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

  const isLoading = isInitialLoading || searchLoading
  const activeTabIndex = DISCOVERY_TABS.findIndex((tab) => tab.key === activeTab)
  const contentSection = isLoading ? (
    <LoadingDots label="素材广场加载中…" />
  ) : (
    <ContentGrid items={items} onSelect={handleSelectContent} onDownload={handleDownload} />
  )
  const trackTransform = `translate3d(calc(-${activeTabIndex * TRACK_STEP_PERCENT}% + ${dragOffset}px), 0, 0)`

  return (
    <div>
      <PageHeader title="素材广场" />

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

        {activeTab === 'all' && (
          <div className="flex gap-2">
            <select
              value={primaryCategoryId ?? ''}
              onChange={(e) => handlePrimaryCategoryChange(e.target.value)}
              className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
            >
              <option value="">全部类目</option>
              {primaryCategories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>

            <select
              value={secondaryCategoryId ?? ''}
              disabled={primaryCategoryId === null}
              onChange={(e) =>
                setSecondaryCategoryId(e.target.value === '' ? null : Number(e.target.value))
              }
              className={clsx(
                'flex-1 rounded-lg border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-purple-500',
                primaryCategoryId === null
                  ? 'cursor-not-allowed border-gray-200 bg-gray-100 text-gray-400 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-600'
                  : 'border-gray-300 bg-white text-gray-700 focus:border-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200',
              )}
            >
              <option value="">全部子类目</option>
              {secondaryCategories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>

            <select
              value={contentTypeFilter ?? ''}
              onChange={(e) => {
                const v = e.target.value
                setContentTypeFilter(v === '' ? null : (v as 'image' | 'video'))
              }}
              className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
            >
              <option value="">图片&amp;视频</option>
              <option value="image">图片</option>
              <option value="video">视频</option>
            </select>
          </div>
        )}
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

      {!isSearchMode && !isInitialLoading && items.length > 0 && (
        <>
          <div ref={sentinelRef} aria-hidden="true" className="h-1" />
          <div className="mt-6 mb-4 flex justify-center text-sm text-gray-500 dark:text-gray-400">
            {isLoadingMore ? (
              <LoadingDots label="加载更多中…" />
            ) : loadedCountRef.current < total ? (
              <button
                type="button"
                onClick={() => void loadMore()}
                className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm text-gray-600 transition hover:border-purple-300 hover:text-purple-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-purple-500/40 dark:hover:text-purple-300"
              >
                加载更多
              </button>
            ) : (
              <span>· 已加载全部 {total} 条 ·</span>
            )}
          </div>
        </>
      )}

      {selectedContent && (
        <ContentDetail
          content={selectedContent}
          onClose={() => setSelectedContent(null)}
          onDownload={handleDownload}
        />
      )}

      <Toast
        open={showDownloadToast}
        title="已通过方小集Bot发送"
        description="请查看您的飞书消息"
      />
    </div>
  )
}
