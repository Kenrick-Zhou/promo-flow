import { useEffect, useMemo, useState } from 'react'
import { useContent } from '@/hooks/useContent'
import { useSystem } from '@/hooks/useSystem'
import CategorySelector from '@/components/content/CategorySelector'
import UploadProgressDialog from '@/components/content/UploadProgressDialog'
import LoadingDots from '@/components/ui/LoadingDots'
import TagSelector from '@/components/content/TagSelector'
import type { CategoryTree, ContentType, Tag } from '@/types'

const IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg', 'tiff', 'heic', 'heif']
const VIDEO_EXTENSIONS = ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm', 'm4v']

const typeLabel: Record<string, string> = { image: '图片', video: '视频' }

interface Props {
  onSuccess?: () => void
}

type UploadStage = 'idle' | 'preparing' | 'uploading' | 'registering'

function getErrorMessage(error: unknown): string {
  if (error instanceof TypeError) {
    return '文件上传被对象存储拦截，请联系管理员检查 OSS 跨域（CORS）配置'
  }

  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof error.response === 'object' &&
    error.response !== null &&
    'data' in error.response &&
    typeof error.response.data === 'object' &&
    error.response.data !== null &&
    'message' in error.response.data &&
    typeof error.response.data.message === 'string'
  ) {
    return error.response.data.message
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  return '上传失败，请重试'
}

function detectContentType(filename: string): ContentType | null {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (!ext) return null
  if (IMAGE_EXTENSIONS.includes(ext)) return 'image'
  if (VIDEO_EXTENSIONS.includes(ext)) return 'video'
  return null
}

export default function UploadForm({ onSuccess }: Props) {
  const { getPresignedUrl, createContent, uploadToPresignedUrl } = useContent()
  const { listCategories, listTags } = useSystem()

  const [file, setFile] = useState<File | null>(null)
  const [contentType, setContentType] = useState<ContentType | null>(null)
  const [description, setDescription] = useState('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [primaryCategoryId, setPrimaryCategoryId] = useState<number | null>(null)
  const [secondaryCategoryId, setSecondaryCategoryId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [initialLoading, setInitialLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [uploadStage, setUploadStage] = useState<UploadStage>('idle')
  const [uploadProgress, setUploadProgress] = useState(0)

  const [categories, setCategories] = useState<CategoryTree[]>([])
  const [availableTags, setAvailableTags] = useState<Tag[]>([])

  useEffect(() => {
    Promise.all([listCategories(), listTags()])
      .then(([loadedCategories, loadedTags]) => {
        setCategories(loadedCategories)
        setAvailableTags(loadedTags)
      })
      .catch(() => {
        setError('基础数据加载失败，请刷新页面后重试')
      })
      .finally(() => {
        setInitialLoading(false)
      })
  }, [listCategories, listTags])

  useEffect(() => {
    if (uploadStage !== 'registering') {
      return
    }

    const timer = window.setInterval(() => {
      setUploadProgress((current) => (current >= 98 ? current : current + 1))
    }, 600)

    return () => window.clearInterval(timer)
  }, [uploadStage])

  const progressCopy = useMemo(() => {
    switch (uploadStage) {
      case 'preparing':
        return {
          title: '正在准备上传',
          hint: '正在向服务器申请安全上传地址，马上就好。',
        }
      case 'uploading':
        return {
          title: '正在上传文件',
          hint: '文件正在传输中，进度会随网络和文件大小实时更新。',
        }
      case 'registering':
        return {
          title: '正在生成素材记录',
          hint: '文件已上传完成，正在保存素材信息并触发后续分析，请耐心等待。',
        }
      case 'idle':
      default:
        return {
          title: '正在处理上传',
          hint: '请稍候…',
        }
    }
  }, [uploadStage])

  if (initialLoading) {
    return <LoadingDots label="正在加载类目与系统默认标签…" className="max-w-lg" />
  }

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
    if (!file || !contentType || !secondaryCategoryId || isSubmitting) return

    setError(null)
    setIsSubmitting(true)
    setUploadStage('preparing')
    setUploadProgress(8)

    try {
      const uploadContentType = file.type || 'application/octet-stream'
      const { upload_url, file_key, upload_headers } = await getPresignedUrl(
        file.name,
        uploadContentType,
      )

      setUploadStage('uploading')
      setUploadProgress(12)

      await uploadToPresignedUrl(upload_url, file, upload_headers, (progress) => {
        const mappedProgress = 12 + Math.round(progress * 0.76)
        setUploadProgress(Math.min(88, mappedProgress))
      })

      setUploadStage('registering')
      setUploadProgress(92)

      await createContent({
        description: description || undefined,
        tag_names: selectedTags,
        content_type: contentType,
        category_id: secondaryCategoryId,
        file_key,
      })

      setUploadProgress(100)
      setUploadStage('idle')
      setIsSubmitting(false)
      onSuccess?.()
    } catch (submitError: unknown) {
      setIsSubmitting(false)
      setUploadStage('idle')
      setUploadProgress(0)
      setError(getErrorMessage(submitError))
      return
    }
  }

  return (
    <>
      <UploadProgressDialog
        open={isSubmitting}
        progress={uploadProgress}
        title={progressCopy.title}
        hint={progressCopy.hint}
        fileName={file?.name}
      />

      <form onSubmit={handleSubmit} className="max-w-lg space-y-5" aria-busy={isSubmitting}>
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
            disabled={isSubmitting}
            className="mt-1.5 w-full text-sm text-gray-500 file:mr-4 file:rounded-lg file:border-0 file:bg-purple-50 file:px-4 file:py-2.5 file:text-sm file:font-medium file:text-purple-700 hover:file:bg-purple-100 disabled:cursor-not-allowed disabled:opacity-60 dark:text-gray-400 dark:file:bg-purple-900/30 dark:file:text-purple-300"
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
          disabled={isSubmitting}
        />

        <TagSelector
          availableTags={availableTags}
          selectedTags={selectedTags}
          onChange={setSelectedTags}
          disabled={isSubmitting}
        />

        <div>
          <label
            htmlFor="description"
            className="block text-sm font-medium text-gray-700 dark:text-gray-200"
          >
            描述（可选）
          </label>
          <textarea
            id="description"
            disabled={isSubmitting}
            className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-700 shadow-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:disabled:bg-gray-900 dark:disabled:text-gray-500"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting || !contentType || !secondaryCategoryId}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-purple-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:focus:ring-offset-gray-900"
        >
          {isSubmitting ? '上传处理中...' : '提交上传'}
        </button>
      </form>
    </>
  )
}
