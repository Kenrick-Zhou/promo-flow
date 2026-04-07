import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { useAuthStore } from '@/store/auth'

export default function Login() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { loginWithCode } = useAuth()
  const token = useAuthStore((s) => s.token)
  const didCallRef = useRef(false)

  useEffect(() => {
    if (token) {
      navigate('/')
      return
    }
    const code = searchParams.get('code')
    if (code && !didCallRef.current) {
      didCallRef.current = true
      loginWithCode(code)
        .then(() => navigate('/'))
        .catch(() => {})
    }
  }, [])

  function handleFeishuLogin() {
    fetch('/api/v1/auth/login')
      .then((r) => r.json())
      .then(({ authorization_url }) => {
        console.log('[PromoFlow] OAuth authorization_url:', authorization_url)
        window.location.href = authorization_url
      })
      .catch((err) => console.error('[PromoFlow] 获取 OAuth URL 失败:', err))
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="w-full max-w-sm rounded-2xl border border-gray-200 bg-white p-10 text-center shadow-lg dark:border-gray-700 dark:bg-gray-800">
        <div className="text-5xl mb-4">📢</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-1 dark:text-white">PromoFlow</h1>
        <p className="text-sm text-gray-500 mb-8 dark:text-gray-400">营销内容管理平台</p>
        <button
          onClick={handleFeishuLogin}
          className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-blue-500 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
        >
          飞书登录
        </button>
      </div>
    </div>
  )
}
