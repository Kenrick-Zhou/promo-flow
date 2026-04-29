interface Props {
  open: boolean
  title: string
  description?: string
}

export default function Toast({ open, title, description }: Props) {
  if (!open) {
    return null
  }

  return (
    <div
      className="pointer-events-none fixed inset-x-4 bottom-24 z-[60] flex justify-center sm:inset-x-auto sm:right-6 sm:top-6 sm:bottom-auto"
      aria-live="polite"
      aria-atomic="true"
    >
      <div
        role="status"
        className="w-full max-w-sm rounded-2xl border border-purple-200 bg-white/95 px-4 py-3 shadow-lg ring-1 ring-black/5 backdrop-blur dark:border-purple-800 dark:bg-gray-900/95"
      >
        <p className="text-sm font-semibold text-gray-900 dark:text-white">{title}</p>
        {description && (
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">{description}</p>
        )}
      </div>
    </div>
  )
}
