interface Props {
  label?: string
  className?: string
}

export default function LoadingDots({ label = '正在加载，请稍候…', className = '' }: Props) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-4 rounded-2xl border border-dashed border-gray-200 bg-white/80 px-6 py-16 text-center dark:border-gray-700 dark:bg-gray-800/80 ${className}`}
    >
      <span className="sr-only">{label}</span>

      <div className="flex items-center justify-center gap-3" aria-hidden="true">
        <span className="relative flex size-3">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-purple-400 opacity-75" />
          <span className="relative inline-flex size-3 rounded-full bg-purple-600" />
        </span>

        <span className="relative flex size-3 [animation-delay:150ms]">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-purple-400 opacity-75 [animation-delay:150ms]" />
          <span className="relative inline-flex size-3 rounded-full bg-purple-600" />
        </span>

        <span className="relative flex size-3 [animation-delay:300ms]">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-purple-400 opacity-75 [animation-delay:300ms]" />
          <span className="relative inline-flex size-3 rounded-full bg-purple-600" />
        </span>
      </div>

      <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{label}</p>
    </div>
  )
}
