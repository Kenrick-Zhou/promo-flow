import { useCallback, useState } from 'react'
import api from '@/services/api'
import type { SearchResultItem } from '@/types'

interface SearchResultsResponse {
  results: SearchResultItem[]
}

export function useSearch() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const semanticSearch = useCallback(
    async (query: string, limit = 10): Promise<SearchResultItem[]> => {
      setLoading(true)
      setError(null)
      try {
        const { data } = await api.post<SearchResultsResponse>('/search', { query, limit })
        return data.results
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : '请求失败')
        throw e
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  return { loading, error, semanticSearch }
}
