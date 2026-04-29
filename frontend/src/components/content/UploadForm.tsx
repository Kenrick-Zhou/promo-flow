import { useEffect, useMemo, useRef, useState } from 'react'
import { useContent } from '@/hooks/useContent'
import { useSystem } from '@/hooks/useSystem'
import CategorySelector from '@/components/content/CategorySelector'
import UploadProgressDialog from '@/components/content/UploadProgressDialog'
import LoadingDots from '@/components/ui/LoadingDots'
import TagSelector from '@/components/content/TagSelector'
import type { CategoryTree, ContentBatchItem, ContentType, Tag } from '@/types'
import { getCurrentUserName, track } from '@/utils/track'

const IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg', 'tiff', 'heic', 'heif']
const VIDEO_EXTENSIONS = ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm', 'm4v']

const typeLabel: Record<string, string> = { image: '图片', video: '视频' }

interface Props {
  onSuccess?: () => void
}

type UploadStage = 'idle' | 'preparing' | 'uploading' | 'registering'

interface SelectedFile {
  id: string
  file: File
  contentType: ContentType
}

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

function makeId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export default function UploadForm({ onSuccess }: Props) {
  const { getPresignedUrl, createContentsBatch, uploadToPresignedUrl } = useContent()
  const { listCategories, listTags } = useSystem()

  const [files, setFiles] = useState<SelectedFile[]>([])
  const [isDragActive, setIsDragActive] = useState(false)
  const [description, setDescription] = useState('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [primaryCategoryId, setPrimaryCategoryId] = useState<number | null>(null)
  const [secondaryCategoryId, setSecondaryCategoryId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [initialLoading, setInitialLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [uploadStage, setUploadStage] = useState<UploadStage>('idle')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [perFileProgress, setPerFileProgress] = useState<Record<string, number>>({})

  const [categories, setCategories] = useState<CategoryTree[]>([])
  const [availableTags, setAvailableTags] = useState<Tag[]>([])

  const fileInputRef = useRef<HTMLInputElement | null>(null)

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
          title: files.length > 1 ? `正在上传文件（共 ${files.length} 个）` : '正在上传文件',
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
  }, [uploadStage, files.length])

  if (initialLoading) {
    return <LoadingDots label="正在加载类目与系统默认标签…" className="mx-auto max-w-lg" />
  }

  function appendFiles(incoming: FileList | File[] | null) {
    if (!incoming) return

    const list = Array.from(incoming)
    if (list.length === 0) return

    const accepted: SelectedFile[] = []
    const rejected: string[] = []

    for (const file of list) {
      const detected = detectContentType(file.name)
      if (!detected) {
        rejected.push(file.name)
        continue
      }
      accepted.push({ id: makeId(), file, contentType: detected })
    }

    if (rejected.length > 0) {
      setError(`以下文件类型不受支持，已忽略：${rejected.join('、')}`)
    } else {
      setError(null)
    }

    if (accepted.length > 0) {
      setFiles((prev) => [...prev, ...accepted])
    }
  }

  function removeFile(id: string) {
    setFiles((prev) => prev.filter((f) => f.id !== id))
  }

  function clearAllFiles() {
    setFiles([])
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    appendFiles(e.target.files)
    e.target.value = ''
  }

  function handleDragOver(e: React.DragEvent<HTMLLabelElement>) {
    e.preventDefault()
    if (isSubmitting) return
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
    if (isSubmitting) return
    appendFiles(e.dataTransfer.files)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (isSubmitting) {
      return
    }

    if (files.length === 0) {
      setError('请至少选择一个图片或视频文件')
      return
    }

    if (!secondaryCategoryId) {
      setError('请选择二级类目后再提交上传')
      return
    }

    setError(null)
    setIsSubmitting(true)
    setUploadStage('preparing')
    setUploadProgress(5)
    setPerFileProgress({})

    const submitFiles = files
    const totalSize = submitFiles.reduce((acc, f) => acc + (f.file.size || 1), 0)

    track('upload_click', {
      user_name: getCurrentUserName(),
      file_count: submitFiles.length,
    })

    try {
      // Step 1: request presigned URLs in parallel
      const presignedResults = await Promise.all(
        submitFiles.map(async (entry) => {
          const uploadContentType = entry.file.type || 'application/octet-stream'
          const presigned = await getPresignedUrl(entry.file.name, uploadContentType)
          return { entry, presigned }
        }),
      )

      // Step 2: upload all files in parallel; track per-file progress
      setUploadStage('uploading')
      setUploadProgress(10)

      await Promise.all(
        presignedResults.map(({ entry, presigned }) =>
          uploadToPresignedUrl(
            presigned.upload_url,
            entry.file,
            presigned.upload_headers,
            (progress) => {
              setPerFileProgress((prev) => {
                const next = { ...prev, [entry.id]: progress }
                const uploaded = submitFiles.reduce((acc, f) => {
                  const p = next[f.id] ?? 0
                  return acc + (f.file.size || 1) * p
                }, 0)
                const overall = totalSize > 0 ? uploaded / totalSize : 0
                const mapped = 10 + Math.round(overall * 0.78)
                setUploadProgress(Math.min(88, mapped))
                return next
              })
            },
          ),
        ),
      )

      // Step 3: register all contents in a single batch call
      setUploadStage('registering')
      setUploadProgress(92)

      const batchItems: ContentBatchItem[] = presignedResults.map(({ entry, presigned }) => ({
        content_type: entry.contentType,
        file_key: presigned.file_key,
      }))

      await createContentsBatch({
        files: batchItems,
        description: description || undefined,
        tag_names: selectedTags,
        category_id: secondaryCategoryId,
      })

      setUploadProgress(100)
      setUploadStage('idle')
      setIsSubmitting(false)
      track('upload_success', {
        user_name: getCurrentUserName(),
        file_count: submitFiles.length,
      })
      onSuccess?.()
    } catch (submitError: unknown) {
      setIsSubmitting(false)
      setUploadStage('idle')
      setUploadProgress(0)
      setError(getErrorMessage(submitError))
      return
    }
  }

  const dialogFileName =
    files.length === 1
      ? files[0].file.name
      : files.length > 1
        ? `${files.length} 个文件`
        : undefined

  return (
    <>
      <UploadProgressDialog
        open={isSubmitting}
        progress={uploadProgress}
        title={progressCopy.title}
        hint={progressCopy.hint}
        fileName={dialogFileName}
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
              {isDragActive ? '松开即可添加素材' : '拖拽素材到这里，或点击选择文件（支持多选）'}
            </span>
            <span className="mt-1.5 block text-xs leading-5 text-gray-500 sm:text-sm dark:text-gray-400">
              支持图片和视频混合上传，所选文件将共享下方填写的类目、标签和描述
            </span>

            <input
              id="file-input"
              ref={fileInputRef}
              type="file"
              accept="image/*,video/*"
              multiple
              disabled={isSubmitting}
              className="sr-only"
              onChange={handleFileChange}
            />
          </label>

          {files.length === 0 ? (
            <div className="mt-3 text-xs text-gray-500 sm:text-sm dark:text-gray-400">
              尚未选择文件
            </div>
          ) : (
            <div className="mt-3 space-y-2">
              <div className="flex items-center justify-between text-xs text-gray-500 sm:text-sm dark:text-gray-400">
                <span>
                  已选择{' '}
                  <span className="font-semibold text-gray-700 dark:text-gray-200">
                    {files.length}
                  </span>{' '}
                  个文件
                </span>
                <button
                  type="button"
                  onClick={clearAllFiles}
                  disabled={isSubmitting}
                  className="text-xs font-medium text-purple-600 hover:text-purple-700 disabled:cursor-not-allowed disabled:opacity-50 dark:text-purple-300 dark:hover:text-purple-200"
                >
                  全部清除
                </button>
              </div>
              <ul className="divide-y divide-gray-100 rounded-xl border border-gray-200 dark:divide-gray-800 dark:border-gray-700">
                {files.map((entry) => {
                  const progress = perFileProgress[entry.id]
                  return (
                    <li
                      key={entry.id}
                      className="flex items-center gap-3 px-3 py-2 text-xs sm:text-sm"
                    >
                      <span className="inline-block shrink-0 rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                        {typeLabel[entry.contentType]}
                      </span>
                      <span className="min-w-0 flex-1 truncate text-gray-700 dark:text-gray-200">
                        {entry.file.name}
                      </span>
                      {isSubmitting && uploadStage === 'uploading' && progress !== undefined && (
                        <span className="shrink-0 text-xs text-gray-500 dark:text-gray-400">
                          {progress}%
                        </span>
                      )}
                      {!isSubmitting && (
                        <button
                          type="button"
                          onClick={() => removeFile(entry.id)}
                          className="shrink-0 text-xs font-medium text-gray-400 hover:text-red-600 dark:text-gray-500 dark:hover:text-red-400"
                          aria-label={`移除 ${entry.file.name}`}
                        >
                          移除
                        </button>
                      )}
                    </li>
                  )
                })}
              </ul>
            </div>
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
            描述（可选，将应用于所有文件）
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
          disabled={isSubmitting || files.length === 0 || !secondaryCategoryId}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-purple-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:focus:ring-offset-gray-900"
        >
          {isSubmitting
            ? '上传处理中...'
            : files.length > 1
              ? `批量上传 ${files.length} 个文件`
              : '提交上传'}
        </button>
      </form>
    </>
  )
}
