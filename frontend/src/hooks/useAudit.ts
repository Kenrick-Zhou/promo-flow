import { useCallback, useState } from 'react'
import api from '@/services/api'
import type { Content, ContentListOut, ContentStatus } from '@/types'

interface AuditDecision {
  status: 'approved' | 'rejected'
  comments?: string
}

interface MetadataEdit {
  title?: string
  description?: string
  ai_summary?: string
  tag_names?: string[]
  category_id?: number
  ai_keywords?: string[]
  thumbnail_key?: string | null
}

interface ListAuditItemsOptions {
  silent?: boolean
  offset?: number
  limit?: number
}

export function useAudit() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const listAuditItems = useCallback(
    async (status: ContentStatus, options: ListAuditItemsOptions = {}): Promise<ContentListOut> => {
      const { silent = false, offset, limit } = options

      if (!silent) {
        setLoading(true)
        setError(null)
      }

      try {
        const { data } = await api.get<ContentListOut>('/contents', {
          params: { status, offset, limit },
        })
        return data
      } catch (e: unknown) {
        if (!silent) {
          setError(e instanceof Error ? e.message : '请求失败')
        }
        throw e
      } finally {
        if (!silent) {
          setLoading(false)
        }
      }
    },
    [],
  )

  const submitAudit = useCallback(async (id: number, decision: AuditDecision): Promise<void> => {
    await api.post(`/audit/${id}`, decision)
  }, [])

  const editMetadata = useCallback(async (id: number, edit: MetadataEdit): Promise<Content> => {
    const { data } = await api.patch<Content>(`/audit/${id}/metadata`, edit)
    return data
  }, [])

  return { loading, error, listAuditItems, submitAudit, editMetadata }
}
