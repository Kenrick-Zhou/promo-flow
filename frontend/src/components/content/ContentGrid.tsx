import type { Content } from '@/types'
import ContentCard from './ContentCard'

export interface ContentGridProps {
  items: Content[]
  onSelect?: (content: Content) => void
  onDownload?: (content: Content) => void
}

export default function ContentGrid({ items, onSelect, onDownload }: ContentGridProps) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 py-20 text-gray-400 dark:border-gray-600 dark:text-gray-500">
        <span className="text-5xl mb-4">📭</span>
        <p className="text-sm">暂无素材</p>
      </div>
    )
  }

  return (
    <div className="columns-2 gap-4 sm:columns-2 md:columns-3 lg:columns-4">
      {items.map((c) => (
        <div key={c.id} className="mb-4 break-inside-avoid">
          <ContentCard content={c} onClick={() => onSelect?.(c)} onDownload={onDownload} />
        </div>
      ))}
    </div>
  )
}
