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
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-2xl shadow-lg p-10 w-80 text-center">
        <div className="text-5xl mb-4">📢</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-1">PromoFlow</h1>
        <p className="text-sm text-gray-500 mb-8">营销内容管理平台</p>
        <button
          onClick={handleFeishuLogin}
          className="w-full bg-blue-500 text-white py-3 rounded-xl font-medium hover:bg-blue-600 transition-colors"
        >
          飞书登录
        </button>
      </div>
    </div>
  )
}
