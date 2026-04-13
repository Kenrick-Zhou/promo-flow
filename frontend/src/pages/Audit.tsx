import { useCallback, useEffect, useRef, useState } from 'react'
import { ArrowLeft, RefreshCw } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import MediaPreview from '@/components/ui/MediaPreview'
import { useAudit } from '@/hooks/useAudit'
import type { Content, ContentListOut, ContentStatus, ContentType } from '@/types'
import { getThumbnailUrl } from '@/utils/oss'

const AUDIT_TABS: Array<{ key: ContentStatus; label: string }> = [
  { key: 'pending', label: '待审核' },
  { key: 'approved', label: '已通过' },
  { key: 'rejected', label: '已拒绝' },
]

const STATUS_BADGES: Record<ContentStatus, { text: string; className: string }> = {
  pending: { text: '待审核', className: 'bg-yellow-100 text-yellow-700' },
  approved: { text: '已通过', className: 'bg-green-100 text-green-700' },
  rejected: { text: '已拒绝', className: 'bg-red-100 text-red-700' },
}

export default function Audit() {
  const navigate = useNavigate()
  const { listAuditItems, submitAudit, editMetadata } = useAudit()
  const [activeStatus, setActiveStatus] = useState<ContentStatus>('pending')
  const [items, setItems] = useState<Content[]>([])
  const [total, setTotal] = useState(0)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [editSummary, setEditSummary] = useState('')
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false)
  const [isLoadingList, setIsLoadingList] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState<string | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewType, setPreviewType] = useState<ContentType>('image')
  const activeStatusRef = useRef<ContentStatus>('pending')
  const fingerprintRef = useRef('')
  const requestIdRef = useRef(0)

  const buildFingerprint = useCallback((data: ContentListOut) => {
    return JSON.stringify({
      total: data.total,
      items: data.items.map((item) => ({
        id: item.id,
        updated_at: item.updated_at,
        status: item.status,
        title: item.title,
        description: item.description,
        file_url: item.file_url,
        ai_summary: item.ai_summary,
        ai_keywords: item.ai_keywords,
        ai_status: item.ai_status,
        ai_error: item.ai_error,
        tags: item.tags,
      })),
    })
  }, [])

  const applyAuditData = useCallback(
    (data: ContentListOut) => {
      setItems(data.items)
      setTotal(data.total)
      fingerprintRef.current = buildFingerprint(data)
      setHasLoadedOnce(true)
    },
    [buildFingerprint],
  )

  const refreshAuditItems = useCallback(
    async ({
      force = false,
      showIndicator = false,
      showLoader = false,
      status,
    }: {
      force?: boolean
      showIndicator?: boolean
      showLoader?: boolean
      status?: ContentStatus
    } = {}) => {
      const targetStatus = status ?? activeStatusRef.current
      const requestId = requestIdRef.current + 1

      requestIdRef.current = requestId

      if (showIndicator) {
        setRefreshing(true)
      }

      if (showLoader) {
        setIsLoadingList(true)
      }

      try {
        const data = await listAuditItems(targetStatus, { silent: true })

        if (requestId !== requestIdRef.current) {
          return
        }

        const nextFingerprint = buildFingerprint(data)

        if (force || nextFingerprint !== fingerprintRef.current) {
          applyAuditData(data)
        }

        setRefreshError(null)
      } catch {
        if (requestId !== requestIdRef.current) {
          return
        }

        if (!hasLoadedOnce || showIndicator || showLoader) {
          const activeTab = AUDIT_TABS.find((tab) => tab.key === targetStatus)
          setRefreshError(`获取${activeTab?.label ?? '审核'}内容失败，请稍后重试。`)
        }
      } finally {
        if (requestId === requestIdRef.current) {
          if (showIndicator) {
            setRefreshing(false)
          }

          if (showLoader) {
            setIsLoadingList(false)
          }
        }
      }
    },
    [applyAuditData, buildFingerprint, hasLoadedOnce, listAuditItems],
  )

  useEffect(() => {
    activeStatusRef.current = activeStatus
    setEditingId(null)
    setRefreshError(null)
    void refreshAuditItems({ status: activeStatus, force: true, showLoader: true })
  }, [activeStatus, refreshAuditItems])

  useEffect(() => {
    if (editingId !== null || activeStatus !== 'pending') {
      return
    }

    const timer = window.setInterval(() => {
      void refreshAuditItems({ status: activeStatus })
    }, 10000)

    return () => window.clearInterval(timer)
  }, [activeStatus, editingId, refreshAuditItems])

  async function handleAudit(id: number, status: 'approved' | 'rejected', comments?: string) {
    await submitAudit(id, { status, comments })
    await refreshAuditItems({ force: true, status: activeStatusRef.current })
  }

  function startEdit(item: Content) {
    setEditingId(item.id)
    setEditTitle(item.title ?? '')
    setEditSummary(item.ai_summary ?? '')
  }

  async function saveEdit(id: number) {
    const updated = await editMetadata(id, { title: editTitle, ai_summary: editSummary })
    setItems((prev) => {
      const nextItems = prev.map((item) => (item.id === id ? updated : item))
      fingerprintRef.current = buildFingerprint({ items: nextItems, total })
      return nextItems
    })
    setEditingId(null)
  }

  function cancelEdit() {
    setEditingId(null)
  }

  function openPreview(item: Content) {
    if (item.file_url) {
      setPreviewUrl(item.file_url)
      setPreviewType(item.content_type)
    }
  }

  const aiStatusLabel: Record<string, { text: string; className: string }> = {
    pending: { text: 'AI 待处理', className: 'bg-gray-100 text-gray-600' },
    processing: { text: 'AI 分析中', className: 'bg-blue-100 text-blue-700' },
    completed: { text: 'AI 已完成', className: 'bg-green-100 text-green-700' },
    failed: { text: 'AI 失败', className: 'bg-red-100 text-red-700' },
  }

  const currentTab = AUDIT_TABS.find((tab) => tab.key === activeStatus) ?? AUDIT_TABS[0]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate('/me')}
            className="rounded-lg p-1.5 text-gray-600 transition-colors active:bg-gray-100 dark:text-gray-300 dark:active:bg-gray-700"
            aria-label="返回我的页面"
          >
            <ArrowLeft className="size-5" />
          </button>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">审核工作台</h1>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() =>
              void refreshAuditItems({
                force: true,
                showIndicator: true,
                status: activeStatus,
              })
            }
            disabled={refreshing}
            className="inline-flex items-center rounded-lg border border-gray-200 bg-white p-2 text-gray-600 transition hover:border-purple-200 hover:text-purple-700 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-purple-500/40 dark:hover:text-purple-300"
            aria-label="刷新审核内容"
          >
            <RefreshCw className={`size-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="mb-6 grid w-full grid-cols-3 rounded-xl border border-gray-200 bg-white p-1 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        {AUDIT_TABS.map((tab) => {
          const isActive = tab.key === activeStatus

          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveStatus(tab.key)}
              className={`rounded-lg px-4 py-2 text-center text-sm font-medium transition ${
                isActive
                  ? 'bg-purple-600 text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      <div className="mb-4">
        <span
          className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ${STATUS_BADGES[activeStatus].className} dark:bg-gray-700/60 dark:text-gray-200`}
        >
          {currentTab.label} {total} 个
        </span>
      </div>

      {refreshError && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-900/20 dark:text-red-300">
          {refreshError}
        </div>
      )}

      {isLoadingList && (
        <div className="flex min-h-64 items-center justify-center rounded-2xl border border-dashed border-gray-200 bg-white/70 py-20 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-800/70 dark:text-gray-400">
          正在加载{currentTab.label}内容...
        </div>
      )}

      {!isLoadingList && (
        <div className="space-y-4">
          {items.map((item) => {
            const isEditing = editingId === item.id
            const aiBadge = item.ai_status === 'completed' ? null : aiStatusLabel[item.ai_status]
            const showActionColumn = isEditing || item.status === 'pending'
            return (
              <article
                key={item.id}
                className="rounded-xl border border-gray-200 bg-white shadow-sm transition hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
              >
                <div className="flex">
                  {/* Thumbnail */}
                  {(() => {
                    const thumbUrl = getThumbnailUrl(item.file_url, item.content_type, 300, 300)
                    if (thumbUrl) {
                      return (
                        <button
                          type="button"
                          onClick={() => openPreview(item)}
                          className="relative shrink-0 w-36 overflow-hidden rounded-l-xl bg-gray-100 dark:bg-gray-700"
                          aria-label="预览媒体"
                        >
                          <img
                            src={thumbUrl}
                            alt={item.title ?? '缩略图'}
                            className="h-full w-full object-cover"
                          />
                          {item.content_type === 'video' && (
                            <div className="absolute inset-0 flex items-center justify-center">
                              <div className="flex size-10 items-center justify-center rounded-full bg-black/50 text-white">
                                <svg
                                  className="size-5 ml-0.5"
                                  viewBox="0 0 24 24"
                                  fill="currentColor"
                                >
                                  <path d="M8 5v14l11-7z" />
                                </svg>
                              </div>
                            </div>
                          )}
                        </button>
                      )
                    }
                    return (
                      <div className="flex w-36 shrink-0 items-center justify-center rounded-l-xl bg-gray-100 dark:bg-gray-700">
                        <span className="text-3xl">📄</span>
                      </div>
                    )
                  })()}

                  <div className="flex flex-1 items-start justify-between gap-4 p-5 min-w-0">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 min-w-0">
                        {aiBadge && (
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${aiBadge.className}`}
                          >
                            {aiBadge.text}
                          </span>
                        )}
                        {isEditing ? (
                          <input
                            type="text"
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            className="min-w-0 flex-1 rounded-md border border-gray-300 px-2 py-1 text-sm font-semibold text-gray-900 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                          />
                        ) : (
                          <h3 className="min-w-0 font-semibold text-gray-900 dark:text-white">
                            {item.title ?? '待AI生成'}
                          </h3>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                        {item.description}
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-1">
                        {item.tags.map((t) => (
                          <span
                            key={t}
                            className="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                      {item.ai_keywords.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          <span className="text-xs text-gray-400 dark:text-gray-500">
                            AI 关键词：
                          </span>
                          {item.ai_keywords.map((kw) => (
                            <span
                              key={kw}
                              className="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-600 dark:bg-blue-900/30 dark:text-blue-300"
                            >
                              {kw}
                            </span>
                          ))}
                        </div>
                      )}
                      {isEditing ? (
                        <textarea
                          value={editSummary}
                          onChange={(e) => setEditSummary(e.target.value)}
                          rows={2}
                          className="mt-2 w-full rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-600 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
                        />
                      ) : (
                        item.ai_summary && (
                          <p className="mt-2 text-xs italic text-gray-400 dark:text-gray-500">
                            AI 摘要：{item.ai_summary}
                          </p>
                        )
                      )}
                      {item.ai_error && (
                        <p className="mt-1 text-xs text-red-500">{item.ai_error}</p>
                      )}
                    </div>
                    {showActionColumn && (
                      <div className="flex shrink-0 flex-col gap-2">
                        {isEditing ? (
                          <>
                            <button
                              onClick={() => saveEdit(item.id)}
                              className="inline-flex items-center rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
                            >
                              保存
                            </button>
                            <button
                              onClick={cancelEdit}
                              className="inline-flex items-center rounded-lg bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 dark:bg-gray-600 dark:text-gray-200 dark:hover:bg-gray-500 dark:focus:ring-offset-gray-800"
                            >
                              取消
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              onClick={() => startEdit(item)}
                              className="inline-flex items-center rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-600 shadow-sm transition hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 dark:focus:ring-offset-gray-800"
                            >
                              编辑
                            </button>
                            <button
                              onClick={() => handleAudit(item.id, 'approved')}
                              className="inline-flex items-center rounded-lg bg-green-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-400 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
                            >
                              通过
                            </button>
                            <button
                              onClick={() => handleAudit(item.id, 'rejected')}
                              className="inline-flex items-center rounded-lg bg-red-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
                            >
                              驳回
                            </button>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </article>
            )
          })}

          {hasLoadedOnce && items.length === 0 && (
            <div className="flex flex-col items-center rounded-2xl border border-dashed border-gray-300 py-20 text-gray-400 dark:border-gray-600 dark:text-gray-500">
              <span className="text-5xl mb-4">🎉</span>
              <p className="text-sm">暂无{currentTab.label}内容</p>
            </div>
          )}
        </div>
      )}

      {previewUrl && (
        <MediaPreview
          fileUrl={previewUrl}
          contentType={previewType}
          onClose={() => setPreviewUrl(null)}
        />
      )}
    </div>
  )
}
