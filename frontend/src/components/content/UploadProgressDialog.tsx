interface Props {
  open: boolean
  progress: number
  title: string
  hint: string
  fileName?: string
}

export default function UploadProgressDialog({ open, progress, title, hint, fileName }: Props) {
  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/35 p-4 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-progress-title"
        className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl ring-1 ring-gray-200 dark:bg-gray-900 dark:ring-gray-700"
      >
        <div className="space-y-5">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full bg-purple-50 px-3 py-1 text-xs font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
              <span className="relative flex size-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-purple-400 opacity-75" />
                <span className="relative inline-flex size-2.5 rounded-full bg-purple-600" />
              </span>
              正在处理上传，请勿关闭页面
            </div>

            <div className="flex items-start justify-between gap-4">
              <div>
                <h2
                  id="upload-progress-title"
                  className="text-lg font-semibold text-gray-900 dark:text-white"
                >
                  {title}
                </h2>
                <p className="mt-1 text-sm leading-6 text-gray-500 dark:text-gray-400">{hint}</p>
              </div>

              <span className="shrink-0 text-sm font-semibold text-purple-700 dark:text-purple-300">
                {progress}%
              </span>
            </div>
          </div>

          <div className="space-y-2">
            <span className="sr-only">上传进度</span>
            <div className="h-3 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
              <div
                className="h-full rounded-full bg-purple-600 transition-[width] duration-300 ease-out"
                style={{ width: `${progress}%` }}
                aria-hidden="true"
              />
            </div>
            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>上传中</span>
              <span>完成后将自动跳转成功页</span>
            </div>
          </div>

          {fileName && (
            <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-800/70 dark:text-gray-300">
              <p className="font-medium text-gray-800 dark:text-gray-100">当前文件</p>
              <p className="mt-1 truncate">{fileName}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
