import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import UploadForm from '@/components/content/UploadForm'
import PageHeader from '@/components/layout/PageHeader'
import { CircleCheckBig } from 'lucide-react'
import { navigateBack } from '@/utils/navigation'

export default function Upload() {
  const navigate = useNavigate()
  const [success, setSuccess] = useState(false)

  function handleBack() {
    navigateBack(navigate, '/')
  }

  if (success) {
    return (
      <div className="mx-auto flex w-full max-w-3xl justify-center">
        <div className="flex w-full flex-col items-center gap-4 rounded-2xl border border-dashed border-gray-300 bg-white px-6 py-20 text-center shadow-sm dark:border-gray-600 dark:bg-gray-900">
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
      </div>
    )
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl justify-center">
      <div className="w-full max-w-2xl">
        <PageHeader title="上传素材" onBack={handleBack} />

        <UploadForm onSuccess={() => setSuccess(true)} />
      </div>
    </div>
  )
}
