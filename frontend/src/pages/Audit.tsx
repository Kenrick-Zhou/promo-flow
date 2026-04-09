import { useEffect, useState } from 'react'
import LoadingDots from '@/components/ui/LoadingDots'
import { useAudit } from '@/hooks/useAudit'
import type { Content } from '@/types'

export default function Audit() {
  const { loading, listPending, submitAudit, editMetadata } = useAudit()
  const [items, setItems] = useState<Content[]>([])
  const [total, setTotal] = useState(0)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [editSummary, setEditSummary] = useState('')

  useEffect(() => {
    listPending().then((data) => {
      setItems(data.items)
      setTotal(data.total)
    })
  }, [listPending])

  async function handleAudit(id: number, status: 'approved' | 'rejected', comments?: string) {
    await submitAudit(id, { status, comments })
    listPending().then((data) => {
      setItems(data.items)
      setTotal(data.total)
    })
  }

  function startEdit(item: Content) {
    setEditingId(item.id)
    setEditTitle(item.title ?? '')
    setEditSummary(item.ai_summary ?? '')
  }

  async function saveEdit(id: number) {
    const updated = await editMetadata(id, { title: editTitle, ai_summary: editSummary })
    setItems((prev) => prev.map((i) => (i.id === id ? updated : i)))
    setEditingId(null)
  }

  function cancelEdit() {
    setEditingId(null)
  }

  const aiStatusLabel: Record<string, { text: string; className: string }> = {
    pending: { text: 'AI 待处理', className: 'bg-gray-100 text-gray-600' },
    processing: { text: 'AI 分析中', className: 'bg-blue-100 text-blue-700' },
    completed: { text: 'AI 已完成', className: 'bg-green-100 text-green-700' },
    failed: { text: 'AI 失败', className: 'bg-red-100 text-red-700' },
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">审核工作台</h1>
        <span className="rounded-full bg-yellow-100 px-3 py-1 text-sm font-medium text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300">
          待审核 {total} 个
        </span>
      </div>

      {loading ? (
        <LoadingDots label="审核列表加载中…" />
      ) : (
        <div className="space-y-4">
          {items.map((item) => {
            const isEditing = editingId === item.id
            const aiBadge = aiStatusLabel[item.ai_status]
            return (
              <article
                key={item.id}
                className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    {isEditing ? (
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="w-full rounded-md border border-gray-300 px-2 py-1 text-sm font-semibold text-gray-900 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                      />
                    ) : (
                      <h3 className="font-semibold text-gray-900 dark:text-white">
                        {item.title ?? '待AI生成'}
                      </h3>
                    )}
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                      {item.description}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-1">
                      {item.tags.map((t) => (
                        <span
                          key={t}
                          className="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300"
                        >
                          {t}
                        </span>
                      ))}
                      {aiBadge && (
                        <span
                          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${aiBadge.className}`}
                        >
                          {aiBadge.text}
                        </span>
                      )}
                    </div>
                    {item.ai_keywords.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        <span className="text-xs text-gray-400 dark:text-gray-500">
                          AI 关键词：
                        </span>
                        {item.ai_keywords.map((kw) => (
                          <span
                            key={kw}
                            className="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-600 dark:bg-blue-900/30 dark:text-blue-300"
                          >
                            {kw}
                          </span>
                        ))}
                      </div>
                    )}
                    {isEditing ? (
                      <textarea
                        value={editSummary}
                        onChange={(e) => setEditSummary(e.target.value)}
                        rows={2}
                        className="mt-2 w-full rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-600 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
                      />
                    ) : (
                      item.ai_summary && (
                        <p className="mt-2 text-xs italic text-gray-400 dark:text-gray-500">
                          AI 摘要：{item.ai_summary}
                        </p>
                      )
                    )}
                    {item.ai_error && <p className="mt-1 text-xs text-red-500">{item.ai_error}</p>}
                  </div>
                  <div className="flex flex-col gap-2 shrink-0">
                    {isEditing ? (
                      <>
                        <button
                          onClick={() => saveEdit(item.id)}
                          className="inline-flex items-center rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
                        >
                          保存
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="inline-flex items-center rounded-lg bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 dark:bg-gray-600 dark:text-gray-200 dark:hover:bg-gray-500 dark:focus:ring-offset-gray-800"
                        >
                          取消
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => startEdit(item)}
                          className="inline-flex items-center rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-600 shadow-sm transition hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 dark:focus:ring-offset-gray-800"
                        >
                          编辑
                        </button>
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
                      </>
                    )}
                  </div>
                </div>
              </article>
            )
          })}

          {items.length === 0 && (
            <div className="flex flex-col items-center rounded-2xl border border-dashed border-gray-300 py-20 text-gray-400 dark:border-gray-600 dark:text-gray-500">
              <span className="text-5xl mb-4">🎉</span>
              <p className="text-sm">暂无待审核内容</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
