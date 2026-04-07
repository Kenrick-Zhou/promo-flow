import { useState } from 'react'
import api from '@/services/api'
import ContentGrid from '@/components/content/ContentGrid'
import type { Content, SearchResultItem } from '@/types'

export default function Search() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResultItem[]>([])
  const [answer, setAnswer] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState<'search' | 'rag'>('search')

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setAnswer(null)
    try {
      if (mode === 'rag') {
        const { data } = await api.post('/search/rag', { query, limit: 5 })
        setResults(
          (data.sources as Partial<Content>[]).map((c) => ({
            content: c as Content,
            score: 1,
          })),
        )
        setAnswer(data.answer)
      } else {
        const { data } = await api.post<SearchResultItem[]>('/search', { query, limit: 10 })
        setResults(data)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6 dark:text-white">智能搜索</h1>

      <form onSubmit={handleSearch} className="flex gap-3 mb-4">
        <input
          className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-700 shadow-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          placeholder="搜索素材，例如：夏季促销图片"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-700 shadow-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          value={mode}
          onChange={(e) => setMode(e.target.value as 'search' | 'rag')}
        >
          <option value="search">语义检索</option>
          <option value="rag">AI 问答</option>
        </select>
        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed dark:focus:ring-offset-gray-900"
        >
          {loading ? '搜索中...' : '搜索'}
        </button>
      </form>

      {answer && (
        <div className="rounded-xl border border-purple-200 bg-purple-50 p-4 mb-6 dark:border-purple-800 dark:bg-purple-900/20">
          <p className="text-sm font-semibold text-purple-700 mb-1 dark:text-purple-300">AI 回答</p>
          <p className="text-sm leading-relaxed text-gray-800 dark:text-gray-200">{answer}</p>
        </div>
      )}

      <ContentGrid items={results.map((r) => r.content)} />
    </div>
  )
}
