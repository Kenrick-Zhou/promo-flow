import { ChevronLeft, ChevronRight } from 'lucide-react'

interface PaginationProps {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
  /** Number of sibling pages to show on each side of the current page */
  siblingCount?: number
  className?: string
}

const ELLIPSIS = '...' as const

type PageItem = number | typeof ELLIPSIS

function buildPageItems(page: number, totalPages: number, siblingCount: number): PageItem[] {
  // Total slots = first + last + current + 2*siblings + 2*ellipsis
  const totalSlots = siblingCount * 2 + 5

  if (totalPages <= totalSlots) {
    return Array.from({ length: totalPages }, (_, i) => i + 1)
  }

  const leftSibling = Math.max(page - siblingCount, 1)
  const rightSibling = Math.min(page + siblingCount, totalPages)
  const showLeftEllipsis = leftSibling > 2
  const showRightEllipsis = rightSibling < totalPages - 1

  const items: PageItem[] = [1]

  if (showLeftEllipsis) {
    items.push(ELLIPSIS)
  } else {
    for (let i = 2; i < leftSibling; i++) {
      items.push(i)
    }
  }

  for (let i = leftSibling; i <= rightSibling; i++) {
    if (i !== 1 && i !== totalPages) {
      items.push(i)
    }
  }

  if (showRightEllipsis) {
    items.push(ELLIPSIS)
  } else {
    for (let i = rightSibling + 1; i < totalPages; i++) {
      items.push(i)
    }
  }

  items.push(totalPages)
  return items
}

export default function Pagination({
  page,
  totalPages,
  onPageChange,
  siblingCount = 1,
  className = '',
}: PaginationProps) {
  if (totalPages <= 1) {
    return null
  }

  const items = buildPageItems(page, totalPages, siblingCount)
  const isFirst = page <= 1
  const isLast = page >= totalPages

  const baseBtn =
    'inline-flex h-9 min-w-9 items-center justify-center rounded-lg border border-gray-200 bg-white px-3 text-sm font-medium text-gray-700 transition hover:border-purple-300 hover:text-purple-700 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-gray-200 disabled:hover:text-gray-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:border-purple-500/40 dark:hover:text-purple-300'
  const activeBtn =
    'inline-flex h-9 min-w-9 items-center justify-center rounded-lg bg-purple-600 px-3 text-sm font-semibold text-white shadow-sm'

  return (
    <nav
      className={`flex flex-wrap items-center justify-center gap-1.5 ${className}`}
      aria-label="分页导航"
    >
      <button
        type="button"
        onClick={() => onPageChange(page - 1)}
        disabled={isFirst}
        className={baseBtn}
        aria-label="上一页"
      >
        <ChevronLeft className="size-4" />
        <span className="ml-1 hidden sm:inline">上一页</span>
      </button>

      {items.map((item, idx) =>
        item === ELLIPSIS ? (
          <span
            key={`ellipsis-${idx}`}
            className="inline-flex h-9 min-w-9 items-center justify-center px-1 text-sm text-gray-400 dark:text-gray-500"
            aria-hidden="true"
          >
            …
          </span>
        ) : (
          <button
            key={item}
            type="button"
            onClick={() => onPageChange(item)}
            className={item === page ? activeBtn : baseBtn}
            aria-current={item === page ? 'page' : undefined}
            aria-label={`第 ${item} 页`}
          >
            {item}
          </button>
        ),
      )}

      <button
        type="button"
        onClick={() => onPageChange(page + 1)}
        disabled={isLast}
        className={baseBtn}
        aria-label="下一页"
      >
        <span className="mr-1 hidden sm:inline">下一页</span>
        <ChevronRight className="size-4" />
      </button>
    </nav>
  )
}
