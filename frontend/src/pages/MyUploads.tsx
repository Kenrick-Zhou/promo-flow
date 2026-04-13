import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import MasonryGrid from '@/components/content/MasonryGrid'
import ContentDetail from '@/components/content/ContentDetail'
import LoadingDots from '@/components/ui/LoadingDots'
import { useContent } from '@/hooks/useContent'
import type { Content, ContentStatus } from '@/types'
import { clsx } from 'clsx'

const STATUS_TABS: Array<{ key: ContentStatus; label: string }> = [
  { key: 'pending', label: '待审核' },
  { key: 'approved', label: '已通过' },
  { key: 'rejected', label: '已拒绝' },
]

export default function MyUploads() {
  const navigate = useNavigate()
  const { listContents, loading } = useContent()
  const [items, setItems] = useState<Content[]>([])
  const [status, setStatus] = useState<ContentStatus>('pending')
  const [selectedContent, setSelectedContent] = useState<Content | null>(null)

  useEffect(() => {
    listContents({
      my_uploads: true,
      status,
    }).then((r) => {
      setItems(r.items)
    })
  }, [status, listContents])

  return (
    <div>
      {/* 顶部导航 */}
      <div className="mb-4 flex items-center gap-3">
        <button
          onClick={() => navigate('/me')}
          className="rounded-lg p-1.5 text-gray-600 transition-colors active:bg-gray-100 dark:text-gray-300 dark:active:bg-gray-700"
        >
          <ArrowLeft className="size-5" />
        </button>
        <h1 className="text-lg font-bold text-gray-900 dark:text-white">我的上传</h1>
      </div>

      {/* 状态筛选 */}
      <div className="mb-4 flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-gray-700">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setStatus(tab.key)}
            className={clsx(
              'flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
              status === tab.key
                ? 'bg-white text-purple-700 shadow-sm dark:bg-gray-800 dark:text-purple-300'
                : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingDots label="加载中…" />
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-gray-400">
          <p>暂无上传内容</p>
        </div>
      ) : (
        <MasonryGrid items={items} onSelect={(c) => setSelectedContent(c)} />
      )}

      {selectedContent && (
        <ContentDetail content={selectedContent} onClose={() => setSelectedContent(null)} />
      )}
    </div>
  )
}
