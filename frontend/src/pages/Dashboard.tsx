import { useEffect, useState } from 'react'
import ContentGrid from '@/components/content/ContentGrid'
import { useContent } from '@/hooks/useContent'
import type { Content, ContentStatus, ContentType } from '@/types'

const statusOptions: { value: ContentStatus | ''; label: string }[] = [
  { value: '', label: '全部' },
  { value: 'approved', label: '已通过' },
  { value: 'pending', label: '待审核' },
  { value: 'rejected', label: '已拒绝' },
]

const typeOptions: { value: ContentType | ''; label: string }[] = [
  { value: '', label: '全部' },
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

      <div className="flex flex-wrap gap-4 mb-6">
        {/* 状态筛选 */}
        <div className="flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-gray-700">
          {statusOptions.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => setStatus(o.value as ContentStatus | '')}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                status === o.value
                  ? 'bg-white text-purple-700 shadow-sm dark:bg-gray-800 dark:text-purple-300'
                  : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
        {/* 类型筛选 */}
        <div className="flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-gray-700">
          {typeOptions.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => setContentType(o.value as ContentType | '')}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                contentType === o.value
                  ? 'bg-white text-purple-700 shadow-sm dark:bg-gray-800 dark:text-purple-300'
                  : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20 text-gray-400 dark:text-gray-500">加载中...</div>
      ) : (
        <ContentGrid items={items} />
      )}
    </div>
  )
}
