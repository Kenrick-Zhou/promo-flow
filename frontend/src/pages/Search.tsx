import { useState } from 'react'
import ContentGrid from '@/components/content/ContentGrid'
import { useSearch } from '@/hooks/useSearch'
import type { SearchResultItem } from '@/types'

export default function Search() {
  const { loading, semanticSearch } = useSearch()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResultItem[]>([])

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    const data = await semanticSearch(query)
    setResults(data)
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
        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed dark:focus:ring-offset-gray-900"
        >
          {loading ? '搜索中...' : '搜索'}
        </button>
      </form>

      <ContentGrid items={results.map((r) => r.content)} />
    </div>
  )
}
