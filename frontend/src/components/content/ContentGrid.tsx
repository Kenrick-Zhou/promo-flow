import type { Content } from '@/types'
import ContentCard from './ContentCard'

interface Props {
  items: Content[]
  onSelect?: (content: Content) => void
}

export default function ContentGrid({ items, onSelect }: Props) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 py-20 text-gray-400 dark:border-gray-600 dark:text-gray-500">
        <span className="text-5xl mb-4">📭</span>
        <p className="text-sm">暂无素材</p>
      </div>
    )
  }
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
      {items.map((c) => (
        <ContentCard key={c.id} content={c} onClick={() => onSelect?.(c)} />
      ))}
    </div>
  )
}
