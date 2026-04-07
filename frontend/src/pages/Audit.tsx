import { useEffect, useState } from 'react'
import api from '@/services/api'
import type { Content } from '@/types'

export default function Audit() {
  const [items, setItems] = useState<Content[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)

  async function fetchPending() {
    setLoading(true)
    try {
      const { data } = await api.get('/audit/pending')
      setItems(data.items)
      setTotal(data.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPending()
  }, [])

  async function handleAudit(id: number, status: 'approved' | 'rejected', comments?: string) {
    await api.post(`/audit/${id}`, { status, comments })
    fetchPending()
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">审核工作台</h1>
        <span className="rounded-full bg-yellow-100 px-3 py-1 text-sm font-medium text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300">
          待审核 {total} 个
        </span>
      </div>

      {loading && <p className="text-gray-400 text-center py-10 dark:text-gray-500">加载中...</p>}

      <div className="space-y-4">
        {items.map((item) => (
          <article
            key={item.id}
            className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-gray-900 dark:text-white">{item.title}</h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{item.description}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {item.tags.map((t) => (
                    <span
                      key={t}
                      className="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300"
                    >
                      {t}
                    </span>
                  ))}
                </div>
                {item.ai_summary && (
                  <p className="mt-2 text-xs italic text-gray-400 dark:text-gray-500">
                    AI 摘要：{item.ai_summary}
                  </p>
                )}
              </div>
              <div className="flex gap-2 shrink-0">
                <button
                  onClick={() => handleAudit(item.id, 'approved')}
                  className="inline-flex items-center rounded-lg bg-green-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-400 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
                >
                  通过
                </button>
                <button
                  onClick={() => handleAudit(item.id, 'rejected')}
                  className="inline-flex items-center rounded-lg bg-red-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
                >
                  驳回
                </button>
              </div>
            </div>
          </article>
        ))}

        {!loading && items.length === 0 && (
          <div className="flex flex-col items-center rounded-2xl border border-dashed border-gray-300 py-20 text-gray-400 dark:border-gray-600 dark:text-gray-500">
            <span className="text-5xl mb-4">🎉</span>
            <p className="text-sm">暂无待审核内容</p>
          </div>
        )}
      </div>
    </div>
  )
}
