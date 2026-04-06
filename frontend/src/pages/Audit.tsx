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
        <h1 className="text-2xl font-bold text-gray-900">审核工作台</h1>
        <span className="text-sm text-gray-500">待审核 {total} 个</span>
      </div>

      {loading && <p className="text-gray-400 text-center py-10">加载中...</p>}

      <div className="space-y-4">
        {items.map((item) => (
          <div key={item.id} className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900">{item.title}</h3>
                <p className="text-sm text-gray-500 mt-1">{item.description}</p>
                <div className="flex flex-wrap gap-1 mt-2">
                  {item.tags.map((t) => (
                    <span key={t} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                      {t}
                    </span>
                  ))}
                </div>
                {item.ai_summary && (
                  <p className="text-xs text-gray-400 mt-2 italic">AI 摘要：{item.ai_summary}</p>
                )}
              </div>
              <div className="flex gap-2 shrink-0">
                <button
                  onClick={() => handleAudit(item.id, 'approved')}
                  className="px-4 py-2 bg-green-500 text-white text-sm rounded-lg hover:bg-green-600"
                >
                  通过
                </button>
                <button
                  onClick={() => handleAudit(item.id, 'rejected')}
                  className="px-4 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600"
                >
                  驳回
                </button>
              </div>
            </div>
          </div>
        ))}

        {!loading && items.length === 0 && (
          <div className="flex flex-col items-center py-20 text-gray-400">
            <span className="text-5xl mb-4">🎉</span>
            <p>暂无待审核内容</p>
          </div>
        )}
      </div>
    </div>
  )
}
