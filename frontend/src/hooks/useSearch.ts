import { useCallback, useState } from 'react'
import api from '@/services/api'
import type { Content, SearchResultItem } from '@/types'

export interface RagResult {
  answer: string
  sources: SearchResultItem[]
}

export function useSearch() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const semanticSearch = useCallback(
    async (query: string, limit = 10): Promise<SearchResultItem[]> => {
      setLoading(true)
      setError(null)
      try {
        const { data } = await api.post<SearchResultItem[]>('/search', { query, limit })
        return data
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : '请求失败')
        throw e
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  const ragQuery = useCallback(async (query: string, limit = 5): Promise<RagResult> => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.post('/search/rag', { query, limit })
      return {
        answer: data.answer as string,
        sources: (data.sources as Partial<Content>[]).map((c) => ({
          content: c as Content,
          score: 1,
        })),
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '请求失败')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  return { loading, error, semanticSearch, ragQuery }
}
