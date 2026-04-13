import { useState } from 'react'
import type { Content } from '@/types'
import { getThumbnailUrl } from '@/utils/oss'

interface Props {
  content: Content
  onClick?: () => void
}

const DEFAULT_ASPECT = 4 / 3

export default function MasonryCard({ content, onClick }: Props) {
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
      {/* Media with original aspect ratio */}
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
          <div className="flex h-full items-center justify-center">
            <span className="text-4xl">📄</span>
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

        <div className="mb-2 flex flex-wrap gap-1">
          {content.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300"
            >
              {tag}
            </span>
          ))}
        </div>

        <p className="text-xs text-gray-400 dark:text-gray-500">— by {content.uploaded_by_name}</p>
      </div>
    </article>
  )
}
