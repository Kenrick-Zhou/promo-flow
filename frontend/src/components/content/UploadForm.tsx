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
  const [isDragActive, setIsDragActive] = useState(false)
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
    return <LoadingDots label="正在加载类目与系统默认标签…" className="mx-auto max-w-lg" />
  }

  function handleSelectedFile(selected: File | null) {
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
      return
    }

    setContentType(null)
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    handleSelectedFile(e.target.files?.[0] ?? null)
  }

  function handleDragOver(e: React.DragEvent<HTMLLabelElement>) {
    e.preventDefault()

    if (isSubmitting) {
      return
    }

    setIsDragActive(true)
  }

  function handleDragLeave(e: React.DragEvent<HTMLLabelElement>) {
    const relatedTarget = e.relatedTarget
    if (relatedTarget instanceof Node && e.currentTarget.contains(relatedTarget)) {
      return
    }

    setIsDragActive(false)
  }

  function handleDrop(e: React.DragEvent<HTMLLabelElement>) {
    e.preventDefault()
    setIsDragActive(false)

    if (isSubmitting) {
      return
    }

    handleSelectedFile(e.dataTransfer.files?.[0] ?? null)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (isSubmitting) {
      return
    }

    if (!file || !contentType) {
      setError('请选择要上传的图片或视频文件')
      return
    }

    if (!secondaryCategoryId) {
      setError('请选择二级类目后再提交上传')
      return
    }

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

      <form
        onSubmit={handleSubmit}
        className="mx-auto w-full max-w-2xl space-y-5"
        aria-busy={isSubmitting}
      >
        <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5 dark:border-gray-700 dark:bg-gray-900">
          <label
            htmlFor="file-input"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`block rounded-xl border-2 border-dashed px-4 py-5 text-center transition sm:px-5 sm:py-6 ${
              isDragActive
                ? 'border-purple-500 bg-purple-50/80 dark:border-purple-400 dark:bg-purple-900/20'
                : 'border-gray-300 hover:border-purple-400 hover:bg-purple-50/50 dark:border-gray-600 dark:hover:border-purple-500 dark:hover:bg-purple-900/10'
            } ${isSubmitting ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
          >
            <span className="mx-auto flex size-10 items-center justify-center rounded-full bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-300">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
                className="size-5"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 16.5V7.5m0 0-3 3m3-3 3 3M3.75 15a4.5 4.5 0 0 0 4.5 4.5h7.5a4.5 4.5 0 0 0 1.342-8.796 5.25 5.25 0 0 0-10.318-1.227A4.5 4.5 0 0 0 3.75 15Z"
                />
              </svg>
            </span>

            <span className="mt-3 block text-sm font-semibold text-gray-900 sm:text-base dark:text-white">
              {isDragActive ? '松开即可上传素材' : '拖拽素材到这里，或点击选择文件'}
            </span>
            <span className="mt-1.5 block text-xs leading-5 text-gray-500 sm:text-sm dark:text-gray-400">
              支持图片和视频文件，PC 端可直接拖拽，移动端点击此区域即可选择
            </span>

            <input
              id="file-input"
              type="file"
              accept="image/*,video/*"
              disabled={isSubmitting}
              className="sr-only"
              onChange={handleFileChange}
            />
          </label>

          <div className="mt-3 flex min-h-5 flex-wrap items-center gap-2 text-xs text-gray-500 sm:text-sm dark:text-gray-400">
            {file ? (
              <>
                <span className="font-medium text-gray-700 dark:text-gray-200">已选择：</span>
                <span className="break-all">{file.name}</span>
              </>
            ) : (
              <span>尚未选择文件</span>
            )}

            {contentType && (
              <span className="inline-block rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                {typeLabel[contentType]}
              </span>
            )}
          </div>
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
