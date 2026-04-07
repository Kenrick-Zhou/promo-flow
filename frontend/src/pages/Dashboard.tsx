import { useEffect, useState } from 'react'
import ContentGrid from '@/components/content/ContentGrid'
import { useContent } from '@/hooks/useContent'
import type { Content, ContentStatus, ContentType } from '@/types'

const statusOptions: { value: ContentStatus | ''; label: string }[] = [
  { value: '', label: '全部状态' },
  { value: 'approved', label: '已通过' },
  { value: 'pending', label: '待审核' },
  { value: 'rejected', label: '已拒绝' },
]

const typeOptions: { value: ContentType | ''; label: string }[] = [
  { value: '', label: '全部类型' },
  { value: 'image', label: '图片' },
  { value: 'video', label: '视频' },
  { value: 'document', label: '文档' },
]

export default function Dashboard() {
  const { listContents, loading } = useContent()
  const [items, setItems] = useState<Content[]>([])
  const [total, setTotal] = useState(0)
  const [status, setStatus] = useState<ContentStatus | ''>('')
  const [contentType, setContentType] = useState<ContentType | ''>('')

  useEffect(() => {
    listContents({ status: status || undefined, content_type: contentType || undefined }).then(
      (r) => {
        setItems(r.items)
        setTotal(r.total)
      },
    )
  }, [status, contentType])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">素材广场</h1>
        <span className="rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-300">
          共 {total} 个素材
        </span>
      </div>

      <div className="flex gap-3 mb-6">
        <select
          className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-700 shadow-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          value={status}
          onChange={(e) => setStatus(e.target.value as ContentStatus | '')}
        >
          {statusOptions.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-700 shadow-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          value={contentType}
          onChange={(e) => setContentType(e.target.value as ContentType | '')}
        >
          {typeOptions.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="flex justify-center py-20 text-gray-400 dark:text-gray-500">加载中...</div>
      ) : (
        <ContentGrid items={items} />
      )}
    </div>
  )
}
