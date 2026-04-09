import { useCallback, useState } from 'react'
import api from '@/services/api'
import type { Content, ContentListOut } from '@/types'

interface AuditDecision {
  status: 'approved' | 'rejected'
  comments?: string
}

interface MetadataEdit {
  title?: string
  ai_summary?: string
}

interface ListPendingOptions {
  silent?: boolean
}

export function useAudit() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const listPending = useCallback(
    async (options: ListPendingOptions = {}): Promise<ContentListOut> => {
      const { silent = false } = options

      if (!silent) {
        setLoading(true)
        setError(null)
      }

      try {
        const { data } = await api.get<ContentListOut>('/audit/pending')
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

  return { loading, error, listPending, submitAudit, editMetadata }
}
