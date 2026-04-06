import { useCallback, useState } from 'react'
import api from '@/services/api'
import type { Content, ContentCreate, ContentListOut } from '@/types'

interface ListParams {
  status?: string
  content_type?: string
  my_uploads?: boolean
  offset?: number
  limit?: number
}

export function useContent() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const listContents = useCallback(async (params?: ListParams): Promise<ContentListOut> => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<ContentListOut>('/contents', { params })
      return data
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '请求失败')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const getPresignedUrl = useCallback(async (filename: string) => {
    const { data } = await api.get('/contents/presigned-upload', { params: { filename } })
    return data as { upload_url: string; file_key: string }
  }, [])

  const createContent = useCallback(
    async (payload: ContentCreate & { file_key: string }): Promise<Content> => {
      const { file_key, ...body } = payload
      const { data } = await api.post<Content>(
        `/contents?file_key=${encodeURIComponent(file_key)}`,
        body,
      )
      return data
    },
    [],
  )

  return { loading, error, listContents, getPresignedUrl, createContent }
}
