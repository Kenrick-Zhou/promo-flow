import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import ContentGrid from '@/components/content/ContentGrid'
import ContentDetail from '@/components/content/ContentDetail'
import LoadingDots from '@/components/ui/LoadingDots'
import Toast from '@/components/ui/Toast'
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
  const { listContents, loading, recordView, recordDownload } = useContent()
  const [items, setItems] = useState<Content[]>([])
  const [status, setStatus] = useState<ContentStatus>('pending')
  const [selectedContent, setSelectedContent] = useState<Content | null>(null)
  const [showDownloadToast, setShowDownloadToast] = useState(false)

  useEffect(() => {
    listContents({
      my_uploads: true,
      status,
    }).then((r) => {
      setItems(r.items)
    })
  }, [status, listContents])

  useEffect(() => {
    if (!showDownloadToast) {
      return
    }

    const timeoutId = window.setTimeout(() => {
      setShowDownloadToast(false)
    }, 3000)

    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [showDownloadToast])

  function handleSelectContent(content: Content) {
    setSelectedContent(content)
    recordView(content.id).then(() => {
      setItems((prev) =>
        prev.map((c) => (c.id === content.id ? { ...c, view_count: c.view_count + 1 } : c)),
      )
    })
  }

  async function handleDownload(content: Content) {
    try {
      await recordDownload(content.id)
      setItems((prev) =>
        prev.map((c) => (c.id === content.id ? { ...c, download_count: c.download_count + 1 } : c)),
      )
      setShowDownloadToast(true)
    } catch {
      setShowDownloadToast(false)
    }
  }

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
        <ContentGrid items={items} onSelect={handleSelectContent} onDownload={handleDownload} />
      )}

      {selectedContent && (
        <ContentDetail content={selectedContent} onClose={() => setSelectedContent(null)} />
      )}

      <Toast
        open={showDownloadToast}
        title="已通过方小集Bot发送"
        description="请查看您的飞书消息"
      />
    </div>
  )
}
