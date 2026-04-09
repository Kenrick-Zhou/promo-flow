import type { Content } from '@/types'

interface Props {
  content: Content
  onClick?: () => void
}

const statusLabel: Record<string, { text: string; className: string }> = {
  pending: { text: '待审核', className: 'bg-yellow-100 text-yellow-700' },
  approved: { text: '已通过', className: 'bg-green-100 text-green-700' },
  rejected: { text: '已拒绝', className: 'bg-red-100 text-red-700' },
}

export default function ContentCard({ content, onClick }: Props) {
  const badge = statusLabel[content.status]

  const aiStatusText: Record<string, string> = {
    pending: 'AI 待处理',
    processing: 'AI 分析中…',
    failed: 'AI 分析失败',
  }
  const title =
    content.ai_status === 'completed'
      ? (content.title ?? '未命名')
      : (aiStatusText[content.ai_status] ?? content.title ?? '未命名')

  return (
    <article
      className="group cursor-pointer overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm transition hover:shadow-lg dark:border-gray-700 dark:bg-gray-800"
      onClick={onClick}
    >
      {/* Thumbnail */}
      <div className="flex h-40 w-full items-center justify-center overflow-hidden bg-gray-100 dark:bg-gray-700">
        {content.content_type === 'image' && content.file_url ? (
          <img
            src={content.file_url}
            alt={title}
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
          />
        ) : (
          <span className="text-4xl">{content.content_type === 'video' ? '🎬' : '📄'}</span>
        )}
      </div>

      <div className="p-4">
        <div className="mb-1 flex items-center justify-between gap-2">
          <h3 className="truncate text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
          <span
            className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${badge.className}`}
          >
            {badge.text}
          </span>
        </div>

        {content.ai_summary && (
          <p className="mb-2 line-clamp-2 text-xs text-gray-500 dark:text-gray-400">
            {content.ai_summary}
          </p>
        )}

        <div className="flex flex-wrap gap-1">
          {content.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </article>
  )
}
