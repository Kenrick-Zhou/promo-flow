import { useState } from 'react'
import api from '@/services/api'
import ContentGrid from '@/components/content/ContentGrid'
import type { SearchResultItem } from '@/types'

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
          (data.sources as { id: number; title: string; ai_summary: string | null }[]).map((c) => ({
            content: c,
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
      <h1 className="text-2xl font-bold text-gray-900 mb-6">智能搜索</h1>

      <form onSubmit={handleSearch} className="flex gap-3 mb-4">
        <input
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm"
          placeholder="搜索素材，例如：夏季促销图片"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={mode}
          onChange={(e) => setMode(e.target.value as 'search' | 'rag')}
        >
          <option value="search">语义检索</option>
          <option value="rag">AI 问答</option>
        </select>
        <button
          type="submit"
          disabled={loading}
          className="bg-purple-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
        >
          {loading ? '搜索中...' : '搜索'}
        </button>
      </form>

      {answer && (
        <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 mb-6 text-sm text-gray-800 leading-relaxed">
          <p className="font-semibold text-purple-700 mb-1">AI 回答</p>
          {answer}
        </div>
      )}

      <ContentGrid items={results.map((r) => r.content)} />
    </div>
  )
}
