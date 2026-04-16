import { useCallback, useState } from 'react'
import axios, { type AxiosProgressEvent } from 'axios'
import api from '@/services/api'
import type { Content, ContentCreate, ContentListOut } from '@/types'

interface ListParams {
  status?: string
  content_type?: string
  my_uploads?: boolean
  category_id?: number
  primary_category_id?: number
  sort_by?: string
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

  const getPresignedUrl = useCallback(async (filename: string, contentType?: string) => {
    const { data } = await api.get('/contents/presigned-upload', {
      params: { filename, content_type: contentType },
    })
    return data as {
      upload_url: string
      file_key: string
      upload_headers: Record<string, string>
    }
  }, [])

  const createContent = useCallback(
    async (payload: ContentCreate & { file_key: string }): Promise<Content> => {
      const { data } = await api.post<Content>('/contents', payload)
      return data
    },
    [],
  )

  const uploadToPresignedUrl = useCallback(
    async (
      uploadUrl: string,
      file: File,
      headers: Record<string, string>,
      onProgress?: (progress: number) => void,
    ): Promise<void> => {
      await axios.put(uploadUrl, file, {
        headers,
        onUploadProgress: (event: AxiosProgressEvent) => {
          if (!event.total || !onProgress) {
            return
          }

          const progress = Math.min(100, Math.round((event.loaded / event.total) * 100))
          onProgress(progress)
        },
      })
    },
    [],
  )

  const recordView = useCallback(async (contentId: number): Promise<void> => {
    await api.post(`/contents/${contentId}/view`)
  }, [])

  const recordDownload = useCallback(async (contentId: number): Promise<void> => {
    await api.post(`/contents/${contentId}/download`)
  }, [])

  return {
    loading,
    error,
    listContents,
    getPresignedUrl,
    createContent,
    uploadToPresignedUrl,
    recordView,
    recordDownload,
  }
}
