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
    <form onSubmit={handleSubmit} className="space-y-4 max-w-lg">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">素材类型</label>
        <select
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
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
        <label className="block text-sm font-medium text-gray-700 mb-1">选择文件</label>
        <input
          type="file"
          className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">标题</label>
        <input
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          maxLength={256}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">描述（可选）</label>
        <textarea
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none"
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">标签（逗号分隔）</label>
        <input
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          placeholder="营销,促销,夏季"
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-purple-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
      >
        {loading ? '上传中...' : '提交上传'}
      </button>
    </form>
  )
}
