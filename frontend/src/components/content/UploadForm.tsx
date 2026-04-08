import { useEffect, useState } from 'react'
import { useContent } from '@/hooks/useContent'
import { useSystem } from '@/hooks/useSystem'
import CategorySelector from '@/components/content/CategorySelector'
import TagSelector from '@/components/content/TagSelector'
import type { CategoryTree, ContentType, Tag } from '@/types'

const IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg', 'tiff', 'heic', 'heif']
const VIDEO_EXTENSIONS = ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm', 'm4v']

const typeLabel: Record<string, string> = { image: '图片', video: '视频' }

function detectContentType(filename: string): ContentType | null {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (!ext) return null
  if (IMAGE_EXTENSIONS.includes(ext)) return 'image'
  if (VIDEO_EXTENSIONS.includes(ext)) return 'video'
  return null
}

export default function UploadForm({ onSuccess }: { onSuccess?: () => void }) {
  const { getPresignedUrl, createContent, loading } = useContent()
  const { listCategories, listTags } = useSystem()

  const [file, setFile] = useState<File | null>(null)
  const [contentType, setContentType] = useState<ContentType | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [primaryCategoryId, setPrimaryCategoryId] = useState<number | null>(null)
  const [secondaryCategoryId, setSecondaryCategoryId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [categories, setCategories] = useState<CategoryTree[]>([])
  const [availableTags, setAvailableTags] = useState<Tag[]>([])

  useEffect(() => {
    listCategories()
      .then(setCategories)
      .catch(() => {})
    listTags()
      .then(setAvailableTags)
      .catch(() => {})
  }, [listCategories, listTags])

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0] ?? null
    setFile(selected)
    if (selected) {
      const detected = detectContentType(selected.name)
      if (!detected) {
        setError('不支持的文件类型，请上传图片或视频文件')
        setContentType(null)
      } else {
        setError(null)
        setContentType(detected)
      }
    } else {
      setContentType(null)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file || !contentType || !secondaryCategoryId) return
    setError(null)
    try {
      const { upload_url, file_key } = await getPresignedUrl(file.name)
      await fetch(upload_url, { method: 'PUT', body: file })
      await createContent({
        title,
        description: description || undefined,
        tag_names: selectedTags,
        content_type: contentType,
        category_id: secondaryCategoryId,
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
          htmlFor="file-input"
          className="block text-sm font-medium text-gray-700 dark:text-gray-200"
        >
          选择文件
        </label>
        <input
          id="file-input"
          type="file"
          accept="image/*,video/*"
          className="mt-1.5 w-full text-sm text-gray-500 file:mr-4 file:rounded-lg file:border-0 file:bg-purple-50 file:px-4 file:py-2.5 file:text-sm file:font-medium file:text-purple-700 hover:file:bg-purple-100 dark:text-gray-400 dark:file:bg-purple-900/30 dark:file:text-purple-300"
          onChange={handleFileChange}
          required
        />
        {contentType && (
          <span className="mt-1.5 inline-block rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
            {typeLabel[contentType]}
          </span>
        )}
      </div>

      <CategorySelector
        categories={categories}
        primaryId={primaryCategoryId}
        secondaryId={secondaryCategoryId}
        onPrimaryChange={setPrimaryCategoryId}
        onSecondaryChange={setSecondaryCategoryId}
      />

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

      <TagSelector
        availableTags={availableTags}
        selectedTags={selectedTags}
        onChange={setSelectedTags}
      />

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading || !contentType || !secondaryCategoryId}
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-purple-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed dark:focus:ring-offset-gray-900"
      >
        {loading ? '上传中...' : '提交上传'}
      </button>
    </form>
  )
}
