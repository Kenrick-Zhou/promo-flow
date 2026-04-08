import type { CategoryTree } from '@/types'

interface Props {
  categories: CategoryTree[]
  primaryId: number | null
  secondaryId: number | null
  onPrimaryChange: (id: number | null) => void
  onSecondaryChange: (id: number | null) => void
}

export default function CategorySelector({
  categories,
  primaryId,
  secondaryId,
  onPrimaryChange,
  onSecondaryChange,
}: Props) {
  const selectedPrimary = categories.find((c) => c.id === primaryId)
  const secondaryOptions = selectedPrimary?.children ?? []

  function handlePrimaryChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value ? Number(e.target.value) : null
    onPrimaryChange(val)
    onSecondaryChange(null) // Reset secondary when primary changes
  }

  function handleSecondaryChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value ? Number(e.target.value) : null
    onSecondaryChange(val)
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      <div>
        <label
          htmlFor="primary-category"
          className="block text-sm font-medium text-gray-700 dark:text-gray-200"
        >
          一级类目
        </label>
        <select
          id="primary-category"
          className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-700 shadow-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          value={primaryId ?? ''}
          onChange={handlePrimaryChange}
          required
        >
          <option value="">请选择一级类目</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label
          htmlFor="secondary-category"
          className="block text-sm font-medium text-gray-700 dark:text-gray-200"
        >
          二级类目
        </label>
        <select
          id="secondary-category"
          className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-700 shadow-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          value={secondaryId ?? ''}
          onChange={handleSecondaryChange}
          disabled={!primaryId}
          required
        >
          <option value="">请选择二级类目</option>
          {secondaryOptions.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
