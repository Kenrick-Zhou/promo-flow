import { useState } from 'react'
import { Download, Eye, FileText } from 'lucide-react'
import type { Content } from '@/types'
import { getThumbnailUrl } from '@/utils/oss'

export interface ContentCardProps {
  content: Content
  onClick?: () => void
  onDownload?: (content: Content) => void
}

const DEFAULT_ASPECT = 4 / 3

export default function ContentCard({ content, onClick, onDownload }: ContentCardProps) {
  const [imgFailed, setImgFailed] = useState(false)
  const aiStatusText: Record<string, string> = {
    pending: 'AI 待处理',
    processing: 'AI 分析中…',
    failed: 'AI 分析失败',
  }
  const title =
    content.ai_status === 'completed'
      ? (content.title ?? '未命名')
      : (aiStatusText[content.ai_status] ?? content.title ?? '未命名')
  const thumbUrl = getThumbnailUrl(content.file_url, content.content_type, 600, 0)
  const aspectRatio =
    content.media_width && content.media_height
      ? content.media_width / content.media_height
      : DEFAULT_ASPECT

  return (
    <article
      className="group cursor-pointer overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm transition hover:shadow-lg dark:border-gray-700 dark:bg-gray-800"
      onClick={onClick}
    >
      <div
        className="relative w-full overflow-hidden bg-gray-100 dark:bg-gray-700"
        style={{ aspectRatio: String(aspectRatio) }}
      >
        {thumbUrl && !imgFailed ? (
          <>
            <img
              src={thumbUrl}
              alt={title}
              className="h-full w-full object-cover transition-transform group-hover:scale-105"
              onError={() => setImgFailed(true)}
            />
            {content.content_type === 'video' && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="flex size-10 items-center justify-center rounded-full bg-black/50 text-white">
                  <svg className="ml-0.5 size-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex h-full items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200 text-gray-400 dark:from-gray-700 dark:to-gray-800 dark:text-gray-500">
            <FileText className="size-12" />
          </div>
        )}
      </div>

      <div className="p-3">
        <h3 className="mb-1 truncate text-sm font-semibold text-gray-900 dark:text-white">
          {title}
        </h3>

        {content.ai_summary && (
          <p className="mb-2 line-clamp-2 text-xs text-gray-500 dark:text-gray-400">
            {content.ai_summary}
          </p>
        )}

        <div className={`mb-2 flex flex-wrap gap-1 ${content.ai_summary ? 'mt-2' : ''}`}>
          {content.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300"
            >
              {tag}
            </span>
          ))}
        </div>

        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 text-xs text-gray-400 dark:text-gray-500">
            <span className="inline-flex items-center gap-1">
              <Eye className="size-3.5" />
              {content.view_count}
            </span>
            <span className="inline-flex items-center gap-1">
              <Download className="size-3.5" />
              {content.download_count}
            </span>
          </div>

          {onDownload && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onDownload(content)
              }}
              className="inline-flex items-center gap-1 rounded-md bg-purple-50 px-2 py-1 text-xs font-medium text-purple-600 transition hover:bg-purple-100 dark:bg-purple-900/30 dark:text-purple-300 dark:hover:bg-purple-900/50"
            >
              <Download className="size-3.5" />
              下载
            </button>
          )}
        </div>
      </div>
    </article>
  )
}
