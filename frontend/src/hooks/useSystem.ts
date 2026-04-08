import { useCallback, useState } from 'react'
import api from '@/services/api'
import type {
  Category,
  CategoryCreate,
  CategoryTree,
  CategoryUpdate,
  Tag,
  TagCreate,
  TagReorderItem,
  TagUpdate,
} from '@/types'

export function useSystem() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // ============================================================
  // Categories
  // ============================================================

  const listCategories = useCallback(async (): Promise<CategoryTree[]> => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<CategoryTree[]>('/categories')
      return data
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '请求失败')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const createCategory = useCallback(async (payload: CategoryCreate): Promise<Category> => {
    const { data } = await api.post<Category>('/admin/categories', payload)
    return data
  }, [])

  const updateCategory = useCallback(
    async (id: number, payload: CategoryUpdate): Promise<Category> => {
      const { data } = await api.patch<Category>(`/admin/categories/${id}`, payload)
      return data
    },
    [],
  )

  const deleteCategory = useCallback(async (id: number): Promise<void> => {
    await api.delete(`/admin/categories/${id}`)
  }, [])

  // ============================================================
  // Tags
  // ============================================================

  const listTags = useCallback(async (): Promise<Tag[]> => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<Tag[]>('/tags')
      return data
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '请求失败')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const createTag = useCallback(async (payload: TagCreate): Promise<Tag> => {
    const { data } = await api.post<Tag>('/admin/tags', payload)
    return data
  }, [])

  const updateTag = useCallback(async (id: number, payload: TagUpdate): Promise<Tag> => {
    const { data } = await api.patch<Tag>(`/admin/tags/${id}`, payload)
    return data
  }, [])

  const deleteTag = useCallback(async (id: number): Promise<void> => {
    await api.delete(`/admin/tags/${id}`)
  }, [])

  const reorderTags = useCallback(async (items: TagReorderItem[]): Promise<Tag[]> => {
    const { data } = await api.put<Tag[]>('/admin/tags/reorder', { items })
    return data
  }, [])

  return {
    loading,
    error,
    listCategories,
    createCategory,
    updateCategory,
    deleteCategory,
    listTags,
    createTag,
    updateTag,
    deleteTag,
    reorderTags,
  }
}
