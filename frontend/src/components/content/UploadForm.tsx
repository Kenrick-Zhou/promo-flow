import { useState } from 'react'
import { useContent } from '@/hooks/useContent'
import type { ContentType } from '@/types'

const contentTypes: ContentType[] = ['image', 'video', 'document']
const typeLabel: Record<ContentType, string> = { image: '图片', video: '视频', document: '文档' }

export default function UploadForm({ onSuccess }: { onSuccess?: () => void }) {
  const { getPresignedUrl, createContent, loading } = useContent()
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [tags, setTags] = useState('')
  const [contentType, setContentType] = useState<ContentType>('image')
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return
    setError(null)
    try {
      const { upload_url, file_key } = await getPresignedUrl(file.name)
      await fetch(upload_url, { method: 'PUT', body: file })
      await createContent({
        title,
        description: description || undefined,
        tags: tags
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean),
        content_type: contentType,
        file_key,
      })
      onSuccess?.()
    } catch {
      setError('上传失败，请重试')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 max-w-lg">
      <div>
        <label
          htmlFor="content-type"
          className="block text-sm font-medium text-gray-700 dark:text-gray-200"
        >
          素材类型
        </label>
        <select
          id="content-type"
          className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-700 shadow-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          value={contentType}
          onChange={(e) => setContentType(e.target.value as ContentType)}
        >
          {contentTypes.map((t) => (
            <option key={t} value={t}>
              {typeLabel[t]}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label
          htmlFor="file-input"
          className="block text-sm font-medium text-gray-700 dark:text-gray-200"
        >
          选择文件
        </label>
        <input
          id="file-input"
          type="file"
          className="mt-1.5 w-full text-sm text-gray-500 file:mr-4 file:rounded-lg file:border-0 file:bg-purple-50 file:px-4 file:py-2.5 file:text-sm file:font-medium file:text-purple-700 hover:file:bg-purple-100 dark:text-gray-400 dark:file:bg-purple-900/30 dark:file:text-purple-300"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          required
        />
      </div>

      <div>
        <label
          htmlFor="title"
          className="block text-sm font-medium text-gray-700 dark:text-gray-200"
        >
          标题
        </label>
        <input
          id="title"
          type="text"
          className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-700 shadow-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          maxLength={256}
        />
      </div>

      <div>
        <label
          htmlFor="description"
          className="block text-sm font-medium text-gray-700 dark:text-gray-200"
        >
          描述（可选）
        </label>
        <textarea
          id="description"
          className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-700 shadow-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>

      <div>
        <label
          htmlFor="tags"
          className="block text-sm font-medium text-gray-700 dark:text-gray-200"
        >
          标签（逗号分隔）
        </label>
        <input
          id="tags"
          type="text"
          className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-700 shadow-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          placeholder="营销,促销,夏季"
        />
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-purple-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed dark:focus:ring-offset-gray-900"
      >
        {loading ? '上传中...' : '提交上传'}
      </button>
    </form>
  )
}
