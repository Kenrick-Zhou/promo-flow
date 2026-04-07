import { useState } from 'react'
import UploadForm from '@/components/content/UploadForm'
import { CircleCheckBig } from 'lucide-react'

export default function Upload() {
  const [success, setSuccess] = useState(false)

  if (success) {
    return (
      <div className="flex flex-col items-center rounded-2xl border border-dashed border-gray-300 py-20 gap-4 dark:border-gray-600">
        <CircleCheckBig className="size-12 text-green-500" />
        <p className="text-lg font-semibold text-gray-800 dark:text-gray-200">
          上传成功！等待审核中
        </p>
        <button
          className="rounded-lg bg-purple-50 px-4 py-2 text-sm font-medium text-purple-700 transition hover:bg-purple-100 dark:bg-purple-900/30 dark:text-purple-300 dark:hover:bg-purple-900/50"
          onClick={() => setSuccess(false)}
        >
          继续上传
        </button>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6 dark:text-white">上传素材</h1>
      <UploadForm onSuccess={() => setSuccess(true)} />
    </div>
  )
}
