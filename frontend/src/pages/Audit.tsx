import { useCallback, useEffect, useRef, useState } from 'react'
import { RefreshCw, Upload as UploadIcon, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '@/components/layout/PageHeader'
import CategorySelector from '@/components/content/CategorySelector'
import TagSelector from '@/components/content/TagSelector'
import MediaPreview from '@/components/ui/MediaPreview'
import Pagination from '@/components/ui/Pagination'
import { useAudit } from '@/hooks/useAudit'
import { useContent } from '@/hooks/useContent'
import { useSystem } from '@/hooks/useSystem'
import type {
  CategoryTree,
  Content,
  ContentListOut,
  ContentStatus,
  ContentType,
  Tag,
} from '@/types'
import { navigateBack } from '@/utils/navigation'
import { getThumbnailUrl } from '@/utils/oss'

const AUDIT_TABS: Array<{ key: ContentStatus; label: string }> = [
  { key: 'pending', label: '待审核' },
  { key: 'approved', label: '已通过' },
  { key: 'rejected', label: '已拒绝' },
]

const PAGE_SIZE = 20

const STATUS_BADGES: Record<ContentStatus, { text: string; className: string }> = {
  pending: { text: '待审核', className: 'bg-yellow-100 text-yellow-700' },
  approved: { text: '已通过', className: 'bg-green-100 text-green-700' },
  rejected: { text: '已拒绝', className: 'bg-red-100 text-red-700' },
}

interface EditState {
  title: string
  description: string
  summary: string
  tags: string[]
  primaryId: number | null
  secondaryId: number | null
  keywords: string[]
  thumbnailKey: string | null
  thumbnailUrl: string | null
}

function findPrimaryId(categories: CategoryTree[], secondaryId: number | null): number | null {
  if (!secondaryId) return null
  for (const primary of categories) {
    if (primary.children?.some((c) => c.id === secondaryId)) {
      return primary.id
    }
  }
  return null
}

function buildCategoryPath(item: Content): string {
  const parts = [item.primary_category_name, item.category_name].filter((p): p is string =>
    Boolean(p && p.trim()),
  )
  return parts.length > 0 ? parts.join(' / ') : '暂未分类'
}

interface KeywordEditorProps {
  keywords: string[]
  onChange: (keywords: string[]) => void
}

function KeywordEditor({ keywords, onChange }: KeywordEditorProps) {
  const [input, setInput] = useState('')

  function add() {
    const value = input.trim()
    if (!value || keywords.includes(value)) {
      setInput('')
      return
    }
    onChange([...keywords, value])
    setInput('')
  }

  function remove(value: string) {
    onChange(keywords.filter((k) => k !== value))
  }

  return (
    <div className="space-y-2">
      <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
        AI 关键词
      </label>
      <div className="flex flex-wrap gap-1.5">
        {keywords.length === 0 && (
          <span className="text-xs text-gray-400 dark:text-gray-500">暂无关键词</span>
        )}
        {keywords.map((kw) => (
          <span
            key={kw}
            className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
          >
            {kw}
            <button
              type="button"
              onClick={() => remove(kw)}
              className="rounded-full p-0.5 hover:bg-blue-100 dark:hover:bg-blue-800/40"
              aria-label={`移除关键词 ${kw}`}
            >
              <X className="size-3" />
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              add()
            }
          }}
          placeholder="输入新关键词，回车添加"
          className="flex-1 rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-700 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
        />
        <button
          type="button"
          onClick={add}
          className="rounded-md bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 transition hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-900/50"
        >
          添加
        </button>
      </div>
    </div>
  )
}

export default function Audit() {
  const navigate = useNavigate()
  const { listAuditItems, submitAudit, editMetadata } = useAudit()
  const { listCategories, listTags } = useSystem()
  const { getPresignedUrl, uploadToPresignedUrl } = useContent()
  const [activeStatus, setActiveStatus] = useState<ContentStatus>('pending')
  const [items, setItems] = useState<Content[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [edit, setEdit] = useState<EditState | null>(null)
  const [savingEdit, setSavingEdit] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)
  const [thumbUploading, setThumbUploading] = useState(false)
  const [categories, setCategories] = useState<CategoryTree[]>([])
  const [availableTags, setAvailableTags] = useState<Tag[]>([])
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false)
  const [isLoadingList, setIsLoadingList] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState<string | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewType, setPreviewType] = useState<ContentType>('image')
  const activeStatusRef = useRef<ContentStatus>('pending')
  const pageRef = useRef(1)
  const fingerprintRef = useRef('')
  const requestIdRef = useRef(0)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

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
      page: pageOverride,
    }: {
      force?: boolean
      showIndicator?: boolean
      showLoader?: boolean
      status?: ContentStatus
      page?: number
    } = {}) => {
      const targetStatus = status ?? activeStatusRef.current
      const targetPage = pageOverride ?? pageRef.current
      const requestId = requestIdRef.current + 1

      requestIdRef.current = requestId

      if (showIndicator) {
        setRefreshing(true)
      }

      if (showLoader) {
        setIsLoadingList(true)
      }

      try {
        const data = await listAuditItems(targetStatus, {
          silent: true,
          offset: (targetPage - 1) * PAGE_SIZE,
          limit: PAGE_SIZE,
        })

        if (requestId !== requestIdRef.current) {
          return
        }

        const nextFingerprint = buildFingerprint(data)

        if (force || nextFingerprint !== fingerprintRef.current) {
          applyAuditData(data)
        }

        // If current page is empty but there are still items, fall back to last page
        if (data.items.length === 0 && data.total > 0 && targetPage > 1) {
          const lastPage = Math.max(1, Math.ceil(data.total / PAGE_SIZE))
          if (lastPage !== targetPage) {
            pageRef.current = lastPage
            setPage(lastPage)
          }
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
    pageRef.current = 1
    setPage(1)
    setEditingId(null)
    setRefreshError(null)
    void refreshAuditItems({ status: activeStatus, page: 1, force: true, showLoader: true })
  }, [activeStatus, refreshAuditItems])

  // Load categories + tags once for the editor.
  useEffect(() => {
    let cancelled = false
    Promise.all([listCategories(), listTags()])
      .then(([cats, tags]) => {
        if (cancelled) return
        setCategories(cats)
        setAvailableTags(tags)
      })
      .catch(() => {
        // Editor will degrade gracefully when these are empty.
      })
    return () => {
      cancelled = true
    }
  }, [listCategories, listTags])

  useEffect(() => {
    if (editingId !== null || activeStatus !== 'pending') {
      return
    }

    const timer = window.setInterval(() => {
      void refreshAuditItems({ status: activeStatus, page: pageRef.current })
    }, 10000)

    return () => window.clearInterval(timer)
  }, [activeStatus, editingId, refreshAuditItems])

  function handlePageChange(nextPage: number) {
    if (nextPage < 1 || nextPage > totalPages || nextPage === page) {
      return
    }
    pageRef.current = nextPage
    setPage(nextPage)
    setEditingId(null)
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
    void refreshAuditItems({
      status: activeStatusRef.current,
      page: nextPage,
      force: true,
      showLoader: true,
    })
  }

  async function handleAudit(id: number, status: 'approved' | 'rejected', comments?: string) {
    await submitAudit(id, { status, comments })
    await refreshAuditItems({ force: true, status: activeStatusRef.current, page: pageRef.current })
  }

  function startEdit(item: Content) {
    setEditingId(item.id)
    setEditError(null)
    setEdit({
      title: item.title ?? '',
      description: item.description ?? '',
      summary: item.ai_summary ?? '',
      tags: [...item.tags],
      primaryId: findPrimaryId(categories, item.category_id),
      secondaryId: item.category_id,
      keywords: [...item.ai_keywords],
      thumbnailKey: item.thumbnail_key,
      thumbnailUrl: item.thumbnail_url,
    })
  }

  function updateEdit(patch: Partial<EditState>) {
    setEdit((prev) => (prev ? { ...prev, ...patch } : prev))
  }

  async function handleThumbnailUpload(file: File) {
    if (!edit) return
    if (!file.type.startsWith('image/')) {
      setEditError('请上传图片格式的缩略图。')
      return
    }
    setEditError(null)
    setThumbUploading(true)
    try {
      const presigned = await getPresignedUrl(file.name, file.type)
      await uploadToPresignedUrl(presigned.upload_url, file, presigned.upload_headers)
      // Build a public URL by stripping the presigned query string.
      const publicUrl = presigned.upload_url.split('?')[0] ?? null
      updateEdit({ thumbnailKey: presigned.file_key, thumbnailUrl: publicUrl })
    } catch {
      setEditError('缩略图上传失败，请重试。')
    } finally {
      setThumbUploading(false)
    }
  }

  async function saveEdit(id: number) {
    if (!edit) return
    if (!edit.secondaryId) {
      setEditError('请选择二级类目。')
      return
    }
    setEditError(null)
    setSavingEdit(true)
    try {
      const updated = await editMetadata(id, {
        title: edit.title,
        description: edit.description,
        ai_summary: edit.summary,
        tag_names: edit.tags,
        category_id: edit.secondaryId,
        ai_keywords: edit.keywords,
        thumbnail_key: edit.thumbnailKey,
      })
      setItems((prev) => {
        const nextItems = prev.map((item) => (item.id === id ? updated : item))
        fingerprintRef.current = buildFingerprint({ items: nextItems, total })
        return nextItems
      })
      setEditingId(null)
      setEdit(null)
    } catch {
      setEditError('保存失败，请稍后重试。')
    } finally {
      setSavingEdit(false)
    }
  }

  function cancelEdit() {
    setEditingId(null)
    setEdit(null)
    setEditError(null)
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

  function handleBack() {
    navigateBack(navigate, '/me')
  }

  return (
    <div>
      <PageHeader title="审核工作台" onBack={handleBack} />

      {/* 状态 tabs（吸顶） */}
      <div className="sticky top-0 z-20 -mx-4 mb-4 border-b border-gray-200/70 bg-gray-50/95 px-4 py-2 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-gray-50/80 dark:border-gray-800/80 dark:bg-gray-900/95 dark:supports-[backdrop-filter]:bg-gray-900/80">
        <div className="grid w-full grid-cols-3 rounded-2xl border border-gray-200 bg-white p-1 shadow-sm dark:border-gray-700 dark:bg-gray-800">
          {AUDIT_TABS.map((tab) => {
            const isActive = tab.key === activeStatus

            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveStatus(tab.key)}
                className={`rounded-lg px-4 py-2 text-center text-sm font-medium transition-all duration-300 ${
                  isActive
                    ? 'bg-purple-600 text-white shadow-sm'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white'
                }`}
                aria-pressed={isActive}
              >
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() =>
            void refreshAuditItems({
              force: true,
              showIndicator: true,
              status: activeStatus,
              page: pageRef.current,
            })
          }
          disabled={refreshing}
          className="inline-flex items-center rounded-lg border border-gray-200 bg-white p-1.5 text-gray-600 transition hover:border-purple-200 hover:text-purple-700 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-purple-500/40 dark:hover:text-purple-300"
          aria-label="刷新审核内容"
        >
          <RefreshCw className={`size-4 ${refreshing ? 'animate-spin' : ''}`} />
        </button>
        <span
          className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ${STATUS_BADGES[activeStatus].className} dark:bg-gray-700/60 dark:text-gray-200`}
        >
          {currentTab.label} {total} 个
        </span>
        {total > 0 && (
          <span className="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-600 dark:bg-gray-700 dark:text-gray-300">
            第 {page} / {totalPages} 页
          </span>
        )}
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
            return (
              <article
                key={item.id}
                className="rounded-xl border border-gray-200 bg-white shadow-sm transition hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
              >
                <div className="flex">
                  {/* Thumbnail */}
                  {(() => {
                    const previewThumbUrl =
                      isEditing && edit?.thumbnailUrl
                        ? `${edit.thumbnailUrl}?x-oss-process=image/resize,m_lfit,w_300,h_300`
                        : getThumbnailUrl(
                            item.file_url,
                            item.content_type,
                            300,
                            300,
                            item.thumbnail_url,
                          )
                    if (previewThumbUrl) {
                      return (
                        <button
                          type="button"
                          onClick={() => openPreview(item)}
                          className="relative shrink-0 w-36 overflow-hidden rounded-l-xl bg-gray-100 dark:bg-gray-700"
                          aria-label="预览媒体"
                        >
                          <img
                            src={previewThumbUrl}
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
                        {isEditing && edit ? (
                          <input
                            type="text"
                            value={edit.title}
                            onChange={(e) => updateEdit({ title: e.target.value })}
                            className="min-w-0 flex-1 rounded-md border border-gray-300 px-2 py-1 text-sm font-semibold text-gray-900 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                            placeholder="标题"
                          />
                        ) : (
                          <h3 className="min-w-0 font-semibold text-gray-900 dark:text-white">
                            {item.title ?? '待AI生成'}
                          </h3>
                        )}
                      </div>
                      {!isEditing && (
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                          分类：{buildCategoryPath(item)}
                        </p>
                      )}
                      {!isEditing && item.description && (
                        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                          <span className="text-gray-400 dark:text-gray-500">描述：</span>
                          {item.description}
                        </p>
                      )}

                      {isEditing && edit ? (
                        <div className="mt-3 space-y-3">
                          <CategorySelector
                            categories={categories}
                            primaryId={edit.primaryId}
                            secondaryId={edit.secondaryId}
                            onPrimaryChange={(id) =>
                              updateEdit({ primaryId: id, secondaryId: null })
                            }
                            onSecondaryChange={(id) => updateEdit({ secondaryId: id })}
                          />
                          <TagSelector
                            availableTags={availableTags}
                            selectedTags={edit.tags}
                            onChange={(tags) => updateEdit({ tags })}
                          />
                          <KeywordEditor
                            keywords={edit.keywords}
                            onChange={(keywords) => updateEdit({ keywords })}
                          />
                          <div className="space-y-1">
                            <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
                              描述
                            </label>
                            <textarea
                              value={edit.description}
                              onChange={(e) => updateEdit({ description: e.target.value })}
                              rows={2}
                              placeholder="请输入素材描述（可选）"
                              className="w-full rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-700 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
                              AI 摘要
                            </label>
                            <textarea
                              value={edit.summary}
                              onChange={(e) => updateEdit({ summary: e.target.value })}
                              rows={3}
                              className="w-full rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-700 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                            />
                          </div>
                          {item.content_type === 'video' && (
                            <div className="space-y-1">
                              <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
                                视频缩略图
                              </label>
                              <div className="flex items-center gap-3">
                                <label
                                  className={`inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-dashed border-gray-300 bg-gray-50 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:border-blue-300 hover:text-blue-600 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:border-blue-500 dark:hover:text-blue-300 ${
                                    thumbUploading ? 'pointer-events-none opacity-60' : ''
                                  }`}
                                >
                                  <UploadIcon className="size-3.5" />
                                  {thumbUploading ? '上传中…' : '上传缩略图'}
                                  <input
                                    type="file"
                                    accept="image/*"
                                    className="hidden"
                                    disabled={thumbUploading}
                                    onChange={(e) => {
                                      const file = e.target.files?.[0]
                                      if (file) void handleThumbnailUpload(file)
                                      e.target.value = ''
                                    }}
                                  />
                                </label>
                                {edit.thumbnailKey && (
                                  <button
                                    type="button"
                                    onClick={() =>
                                      updateEdit({ thumbnailKey: null, thumbnailUrl: null })
                                    }
                                    className="text-xs text-gray-500 underline hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400"
                                  >
                                    恢复默认（视频首帧）
                                  </button>
                                )}
                                <span className="text-xs text-gray-400 dark:text-gray-500">
                                  {edit.thumbnailKey ? '已设置自定义缩略图' : '默认使用视频首帧'}
                                </span>
                              </div>
                            </div>
                          )}
                          {editError && <p className="text-xs text-red-500">{editError}</p>}
                        </div>
                      ) : (
                        <>
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
                          {item.ai_summary && (
                            <p className="mt-2 text-xs italic text-gray-400 dark:text-gray-500">
                              AI 摘要：{item.ai_summary}
                            </p>
                          )}
                        </>
                      )}
                      {item.ai_error && (
                        <p className="mt-1 text-xs text-red-500">{item.ai_error}</p>
                      )}
                    </div>
                    <div className="flex shrink-0 flex-col gap-2">
                      {isEditing ? (
                        <>
                          <button
                            onClick={() => saveEdit(item.id)}
                            disabled={savingEdit || thumbUploading}
                            className="inline-flex items-center justify-center rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 dark:focus:ring-offset-gray-800"
                          >
                            {savingEdit ? '保存中…' : '保存'}
                          </button>
                          <button
                            onClick={cancelEdit}
                            disabled={savingEdit}
                            className="inline-flex items-center justify-center rounded-lg bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-gray-600 dark:text-gray-200 dark:hover:bg-gray-500 dark:focus:ring-offset-gray-800"
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
                          {item.status === 'pending' && (
                            <>
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
                          {item.status === 'approved' && (
                            <button
                              onClick={() => handleAudit(item.id, 'rejected')}
                              className="inline-flex items-center rounded-lg bg-red-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
                            >
                              下架
                            </button>
                          )}
                          {item.status === 'rejected' && (
                            <button
                              onClick={() => handleAudit(item.id, 'approved')}
                              className="inline-flex items-center rounded-lg bg-green-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-400 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
                            >
                              通过
                            </button>
                          )}
                        </>
                      )}
                    </div>
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

      {!isLoadingList && totalPages > 1 && (
        <div className="mt-8 mb-4 flex flex-col items-center gap-2">
          <Pagination page={page} totalPages={totalPages} onPageChange={handlePageChange} />
          <p className="text-xs text-gray-500 dark:text-gray-400">
            第 {page} / {totalPages} 页 · 共 {total} 条
          </p>
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
