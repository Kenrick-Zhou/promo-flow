import { useEffect, useRef, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import type { CategoryTree } from '@/types'

interface Props {
  categories: CategoryTree[]
  primaryId: number | null
  secondaryId: number | null
  onPrimaryChange: (id: number | null) => void
  onSecondaryChange: (id: number | null) => void
  disabled?: boolean
}

interface DropdownProps {
  id: string
  label: string
  placeholder: string
  options: CategoryTree[]
  value: number | null
  onChange: (id: number | null) => void
  disabled?: boolean
  required?: boolean
}

function CategoryDropdown({
  id,
  label,
  placeholder,
  options,
  value,
  onChange,
  disabled = false,
  required = false,
}: DropdownProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const selected = options.find((o) => o.id === value) ?? null

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div ref={ref} className="relative">
      <label htmlFor={id} className="block text-sm font-medium text-gray-700 dark:text-gray-200">
        {label}
      </label>
      {/* Hidden native select for form validation */}
      <select
        id={id}
        className="sr-only"
        value={value ?? ''}
        onChange={() => {}}
        required={required}
        tabIndex={-1}
        aria-hidden="true"
      >
        <option value="" />
        {options.map((o) => (
          <option key={o.id} value={o.id} />
        ))}
      </select>
      <button
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setOpen((v) => !v)}
        className={`mt-1.5 flex w-full items-center justify-between gap-2 rounded-lg border px-4 py-2.5 text-left text-sm shadow-sm transition
          focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500
          ${disabled ? 'cursor-not-allowed opacity-50 bg-gray-50 border-gray-200 dark:bg-gray-900 dark:border-gray-700' : 'cursor-pointer bg-white border-gray-300 hover:border-gray-400 dark:bg-gray-800 dark:border-gray-600 dark:hover:border-gray-500'}`}
      >
        <span className="min-w-0 flex-1">
          {selected ? (
            <>
              <span className="block truncate font-medium text-gray-900 dark:text-white">
                {selected.name}
              </span>
              {selected.description && (
                <span className="block truncate text-xs text-gray-400 dark:text-gray-500">
                  {selected.description}
                </span>
              )}
            </>
          ) : (
            <span className="text-gray-400 dark:text-gray-500">{placeholder}</span>
          )}
        </span>
        <ChevronDown
          className={`size-4 shrink-0 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <ul
          className="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-800"
          role="listbox"
        >
          {options.map((opt) => (
            <li
              key={opt.id}
              role="option"
              aria-selected={opt.id === value}
              onClick={() => {
                onChange(opt.id)
                setOpen(false)
              }}
              className={`cursor-pointer px-4 py-2 transition-colors hover:bg-purple-50 dark:hover:bg-purple-900/20
                ${opt.id === value ? 'bg-purple-50 dark:bg-purple-900/30' : ''}`}
            >
              <span
                className={`block text-sm font-medium ${opt.id === value ? 'text-purple-700 dark:text-purple-300' : 'text-gray-900 dark:text-white'}`}
              >
                {opt.name}
              </span>
              {opt.description && (
                <span className="block text-xs text-gray-400 dark:text-gray-500">
                  {opt.description}
                </span>
              )}
            </li>
          ))}
          {options.length === 0 && (
            <li className="px-4 py-2 text-sm text-gray-400 dark:text-gray-500">暂无选项</li>
          )}
        </ul>
      )}
    </div>
  )
}

export default function CategorySelector({
  categories,
  primaryId,
  secondaryId,
  onPrimaryChange,
  onSecondaryChange,
  disabled = false,
}: Props) {
  const selectedPrimary = categories.find((c) => c.id === primaryId)
  const secondaryOptions = selectedPrimary?.children ?? []

  function handlePrimaryChange(id: number | null) {
    onPrimaryChange(id)
    onSecondaryChange(null) // Reset secondary when primary changes
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      <CategoryDropdown
        id="primary-category"
        label="一级类目"
        placeholder="请选择一级类目"
        options={categories}
        value={primaryId}
        onChange={handlePrimaryChange}
        disabled={disabled}
        required
      />
      <CategoryDropdown
        id="secondary-category"
        label="二级类目"
        placeholder="请选择二级类目"
        options={secondaryOptions}
        value={secondaryId}
        onChange={onSecondaryChange}
        disabled={disabled || !primaryId}
        required
      />
    </div>
  )
}
