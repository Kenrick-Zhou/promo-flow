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

      {/* 状态筛选（吸顶） */}
      <div className="sticky top-0 z-20 -mx-4 mb-6 border-b border-gray-200/70 bg-gray-50/95 px-4 py-2 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-gray-50/80 dark:border-gray-800/80 dark:bg-gray-900/95 dark:supports-[backdrop-filter]:bg-gray-900/80">
        <div className="grid w-full grid-cols-3 rounded-2xl border border-gray-200 bg-white p-1 shadow-sm dark:border-gray-700 dark:bg-gray-800">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setStatus(tab.key)}
              className={clsx(
                'rounded-lg px-4 py-2 text-center text-sm font-medium transition-all duration-300',
                status === tab.key
                  ? 'bg-purple-600 text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white',
              )}
              aria-pressed={status === tab.key}
            >
              {tab.label}
            </button>
          ))}
        </div>
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
