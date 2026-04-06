import { useState } from 'react'
import UploadForm from '@/components/content/UploadForm'

export default function Upload() {
  const [success, setSuccess] = useState(false)

  if (success) {
    return (
      <div className="flex flex-col items-center py-20 gap-4">
        <span className="text-5xl">✅</span>
        <p className="text-lg font-semibold text-gray-800">上传成功！等待审核中</p>
        <button className="text-purple-600 underline text-sm" onClick={() => setSuccess(false)}>
          继续上传
        </button>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">上传素材</h1>
      <UploadForm onSuccess={() => setSuccess(true)} />
    </div>
  )
}
