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
  return (
    <div
      className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      {/* Thumbnail */}
      <div className="w-full h-40 bg-gray-100 flex items-center justify-center text-gray-400">
        {content.content_type === 'image' && content.file_url ? (
          <img src={content.file_url} alt={content.title} className="w-full h-full object-cover" />
        ) : (
          <span className="text-4xl">{content.content_type === 'video' ? '🎬' : '📄'}</span>
        )}
      </div>

      <div className="p-4">
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-sm font-semibold text-gray-900 truncate flex-1 mr-2">
            {content.title}
          </h3>
          <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${badge.className}`}>
            {badge.text}
          </span>
        </div>

        {content.ai_summary && (
          <p className="text-xs text-gray-500 line-clamp-2 mb-2">{content.ai_summary}</p>
        )}

        <div className="flex flex-wrap gap-1">
          {content.tags.slice(0, 3).map((tag) => (
            <span key={tag} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
              {tag}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
