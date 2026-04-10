import { useCallback, useEffect } from 'react'
import { X } from 'lucide-react'
import type { ContentType } from '@/types'

interface Props {
  fileUrl: string
  contentType: ContentType
  alt?: string
  onClose: () => void
}

export default function MediaPreview({ fileUrl, contentType, alt, onClose }: Props) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    },
    [onClose],
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [handleKeyDown])

  function handleBackdropClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-label={alt ?? '媒体预览'}
    >
      <button
        type="button"
        onClick={onClose}
        className="absolute right-4 top-4 z-10 flex size-10 items-center justify-center rounded-full bg-black/50 text-white transition hover:bg-black/70"
        aria-label="关闭预览"
      >
        <X className="size-6" />
      </button>

      {contentType === 'video' ? (
        <video src={fileUrl} controls autoPlay className="max-h-[90vh] max-w-[90vw] rounded-lg">
          <track kind="captions" />
        </video>
      ) : (
        <img
          src={fileUrl}
          alt={alt ?? '图片预览'}
          className="max-h-[90vh] max-w-[90vw] rounded-lg object-contain"
        />
      )}
    </div>
  )
}
