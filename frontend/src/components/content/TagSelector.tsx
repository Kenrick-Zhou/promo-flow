import { useState } from 'react'
import { X } from 'lucide-react'
import type { Tag } from '@/types'

interface Props {
  availableTags: Tag[]
  selectedTags: string[]
  onChange: (tags: string[]) => void
  disabled?: boolean
}

export default function TagSelector({
  availableTags,
  selectedTags,
  onChange,
  disabled = false,
}: Props) {
  const [inputValue, setInputValue] = useState('')

  function handleToggleTag(tagName: string) {
    if (disabled) {
      return
    }

    if (selectedTags.includes(tagName)) {
      onChange(selectedTags.filter((t) => t !== tagName))
    } else {
      onChange([...selectedTags, tagName])
    }
  }

  function handleRemoveTag(tagName: string) {
    if (disabled) {
      return
    }

    onChange(selectedTags.filter((t) => t !== tagName))
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (disabled) {
      return
    }

    if (e.key === 'Enter') {
      e.preventDefault()
      const name = inputValue.trim()
      if (name && !selectedTags.includes(name)) {
        onChange([...selectedTags, name])
      }
      setInputValue('')
    }
  }

  // Custom tags that aren't in the available tag list
  const customSelected = selectedTags.filter((t) => !availableTags.some((at) => at.name === t))

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">标签</label>

      {/* Default tag chips */}
      {availableTags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {availableTags.map((tag) => {
            const isSelected = selectedTags.includes(tag.name)
            return (
              <button
                key={tag.id}
                type="button"
                disabled={disabled}
                onClick={() => handleToggleTag(tag.name)}
                className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  isSelected
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }`}
              >
                {tag.name}
              </button>
            )
          })}
        </div>
      )}

      {/* Selected custom tags */}
      {customSelected.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {customSelected.map((name) => (
            <span
              key={name}
              className="inline-flex items-center gap-1 rounded-full bg-purple-100 px-3 py-1 text-xs font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-300"
            >
              {name}
              <button
                type="button"
                disabled={disabled}
                onClick={() => handleRemoveTag(name)}
                className="ml-0.5 rounded-full p-0.5 hover:bg-purple-200 disabled:cursor-not-allowed disabled:opacity-60 dark:hover:bg-purple-800"
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Input for custom tags */}
      <input
        type="text"
        disabled={disabled}
        className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-700 shadow-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:disabled:bg-gray-900 dark:disabled:text-gray-500"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="输入标签名按回车添加自定义标签"
      />
    </div>
  )
}
