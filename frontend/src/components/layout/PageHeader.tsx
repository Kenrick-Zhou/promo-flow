import type { ReactNode } from 'react'
import { ArrowLeft } from 'lucide-react'

interface Props {
  title: string
  onBack?: () => void
  backLabel?: string
  actions?: ReactNode
}

export default function PageHeader({ title, onBack, backLabel = '返回上一页', actions }: Props) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <div className="flex min-w-0 items-center gap-3">
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="rounded-lg p-1.5 text-gray-600 transition-colors active:bg-gray-100 dark:text-gray-300 dark:active:bg-gray-700"
            aria-label={backLabel}
          >
            <ArrowLeft className="size-5" />
          </button>
        )}
        <h1 className="truncate text-lg font-bold text-gray-900 dark:text-white">{title}</h1>
      </div>

      {actions ? <div className="shrink-0">{actions}</div> : null}
    </div>
  )
}
