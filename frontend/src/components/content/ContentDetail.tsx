import { useCallback, useEffect } from 'react'
import { X } from 'lucide-react'
import type { Content } from '@/types'

interface Props {
  content: Content
  onClose: () => void
}

export default function ContentDetail({ content, onClose }: Props) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    },
    [onClose],
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [handleKeyDown])

  function handleBackdropClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col bg-black/85"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-label="素材详情"
    >
      {/* 关闭按钮 */}
      <button
        type="button"
        onClick={onClose}
        className="absolute right-4 top-4 z-10 flex size-10 items-center justify-center rounded-full bg-black/50 text-white transition hover:bg-black/70"
        aria-label="关闭"
      >
        <X className="size-6" />
      </button>

      {/* 媒体区域 */}
      <div
        className="flex flex-1 items-center justify-center p-6 overflow-hidden"
        onClick={handleBackdropClick}
      >
        {content.file_url && content.content_type === 'video' ? (
          <video
            src={content.file_url}
            controls
            autoPlay
            className="max-h-full max-w-full rounded-lg object-contain"
          >
            <track kind="captions" />
          </video>
        ) : content.file_url && content.content_type === 'image' ? (
          <img
            src={content.file_url}
            alt={content.title ?? '图片预览'}
            className="max-h-full max-w-full rounded-lg object-contain"
          />
        ) : (
          <div className="flex flex-col items-center gap-4 text-gray-400">
            <span className="text-8xl">📄</span>
            <p className="text-sm">文档暂不支持预览</p>
          </div>
        )}
      </div>

      {/* 底部详情栏 */}
      <div className="shrink-0 bg-white dark:bg-gray-900" onClick={(e) => e.stopPropagation()}>
        <div className="mx-auto max-w-4xl px-6 py-4 flex flex-wrap items-start gap-x-8 gap-y-3">
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white truncate">
              {content.title ?? '待AI生成'}
            </h3>
            {content.description && (
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                {content.description}
              </p>
            )}
          </div>

          {content.tags.length > 0 && (
            <div className="shrink-0">
              <p className="mb-1 text-xs font-medium text-gray-400 dark:text-gray-500">标签</p>
              <div className="flex flex-wrap gap-1">
                {content.tags.map((t) => (
                  <span
                    key={t}
                    className="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {content.ai_keywords.length > 0 && (
            <div className="shrink-0">
              <p className="mb-1 text-xs font-medium text-gray-400 dark:text-gray-500">AI 关键词</p>
              <div className="flex flex-wrap gap-1">
                {content.ai_keywords.map((kw) => (
                  <span
                    key={kw}
                    className="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-600 dark:bg-blue-900/30 dark:text-blue-300"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}

          {content.ai_summary && (
            <div className="w-full">
              <p className="mb-1 text-xs font-medium text-gray-400 dark:text-gray-500">AI 摘要</p>
              <p className="text-xs italic text-gray-500 dark:text-gray-400 line-clamp-2">
                {content.ai_summary}
              </p>
            </div>
          )}

          <p className="w-full text-xs text-gray-400 dark:text-gray-500">
            — by {content.uploaded_by_name}
          </p>
        </div>
      </div>
    </div>
  )
}
