import { useCallback, useState } from 'react'
import api from '@/services/api'
import type { ContentListOut } from '@/types'

interface AuditDecision {
  status: 'approved' | 'rejected'
  comments?: string
}

export function useAudit() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const listPending = useCallback(async (): Promise<ContentListOut> => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<ContentListOut>('/audit/pending')
      return data
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '请求失败')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const submitAudit = useCallback(async (id: number, decision: AuditDecision): Promise<void> => {
    await api.post(`/audit/${id}`, decision)
  }, [])

  return { loading, error, listPending, submitAudit }
}
