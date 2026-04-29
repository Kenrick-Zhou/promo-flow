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
  }, [loginWithCode, navigate, searchParams, token])

  function handleFeishuLogin() {
    fetch('/api/v1/auth/login')
      .then((r) => r.json())
      .then(({ authorization_url }) => {
        console.log('[方小集] OAuth authorization_url:', authorization_url)
        window.location.href = authorization_url
      })
      .catch((err) => console.error('[方小集] 获取 OAuth URL 失败:', err))
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-br from-orange-50 via-amber-50 to-blue-50 px-4 py-12 dark:from-gray-950 dark:via-gray-900 dark:to-slate-900">
      {/* 装饰：浮动彩色光晕，呼应 logo 配色 */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-32 -left-24 h-96 w-96 rounded-full bg-orange-300/40 blur-3xl dark:bg-orange-500/20"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute top-1/3 -right-24 h-96 w-96 rounded-full bg-blue-300/40 blur-3xl dark:bg-blue-500/20"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-32 left-1/3 h-96 w-96 rounded-full bg-purple-300/30 blur-3xl dark:bg-purple-500/20"
      />

      {/* 装饰：细网格点阵 */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(0,0,0,0.06)_1px,transparent_0)] [background-size:24px_24px] dark:bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.05)_1px,transparent_0)]"
      />

      {/* 主卡片 */}
      <div className="relative z-10 w-full max-w-md">
        <div className="rounded-3xl border border-white/60 bg-white/70 p-10 text-center shadow-2xl shadow-orange-500/10 backdrop-blur-xl dark:border-gray-700/60 dark:bg-gray-900/70 dark:shadow-black/40">
          {/* Logo + 光环 */}
          <div className="relative mx-auto mb-6 h-32 w-32">
            <div
              aria-hidden
              className="absolute inset-0 rounded-full bg-gradient-to-br from-orange-400/40 via-amber-300/40 to-blue-400/40 blur-2xl"
            />
            <img
              src="/logo.png"
              alt="方小集"
              className="relative h-32 w-32 animate-[float_4s_ease-in-out_infinite] object-contain drop-shadow-[0_8px_24px_rgba(251,146,60,0.35)]"
            />
          </div>

          {/* 品牌名（渐变文字） */}
          <h1 className="bg-gradient-to-r from-orange-500 via-amber-500 to-blue-500 bg-clip-text text-3xl font-extrabold tracking-tight text-transparent">
            方小集
          </h1>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">智能营销素材管理平台</p>

          {/* 分割装饰 */}
          <div className="my-7 flex items-center justify-center gap-2">
            <span className="h-px w-12 bg-gradient-to-r from-transparent to-gray-300 dark:to-gray-600" />
            <span className="h-1.5 w-1.5 rounded-full bg-orange-400" />
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
            <span className="h-px w-12 bg-gradient-to-l from-transparent to-gray-300 dark:to-gray-600" />
          </div>

          {/* 飞书登录按钮 */}
          <button
            onClick={handleFeishuLogin}
            className="group inline-flex w-full items-center justify-center gap-2.5 rounded-2xl bg-gradient-to-r from-[#3370FF] to-[#1456F0] px-5 py-3.5 text-sm font-medium text-white shadow-lg shadow-blue-500/30 transition-all hover:-translate-y-0.5 hover:shadow-xl hover:shadow-blue-500/40 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 active:translate-y-0 dark:focus:ring-offset-gray-900"
          >
            <FeishuIcon className="h-5 w-5" />
            <span>飞书登录</span>
            <svg
              className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden
            >
              <path
                fillRule="evenodd"
                d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* 底部品牌小字（fixed 固定在视口底部） */}
      <p className="fixed inset-x-0 bottom-6 z-20 text-center text-xs text-gray-500 dark:text-gray-500">
        © {new Date().getFullYear()} 有方大健康 · 本数科技
      </p>

      {/* 自定义浮动动画 */}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-6px); }
        }
      `}</style>
    </div>
  )
}

function FeishuIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 1024 1024" fill="currentColor" aria-hidden>
      <path d="M159.402667 385.365333c1.058133 0.136533 2.030933 0.6144 2.798933 1.365334 52.258133 49.442133 327.168 313.821867 568.797867 303.701333a155.136 155.136 0 0 0 59.682133-17.066667c9.8816-5.137067 19.643733 3.1232 12.458667 11.639467-44.680533 52.992-133.666133 130.901333-280.149334 149.026133a528.247467 528.247467 0 0 1-350.6688-75.844266 42.7008 42.7008 0 0 1-18.568533-35.413334l-0.085333-331.5712a5.0688 5.0688 0 0 1 5.7344-5.853866z m686.609066-6.536533c40.669867 0.682667 80.7936 9.454933 118.016 25.856a2.850133 2.850133 0 0 1 0.8192 3.498667 2.850133 2.850133 0 0 1-0.8192 0.989866 543.044267 543.044267 0 0 0-72.533333 121.941334c-6.1952 15.906133-17.885867 39.4752-27.221333 57.6-8.994133 17.442133-21.2992 33.7408-38.741334 42.734933a142.557867 142.557867 0 0 1-53.896533 15.36c-73.130667 2.850133-151.005867-16.605867-227.140267-48.0768-12.356267-5.12-13.824-21.9136-3.191466-30.020267a505.429333 505.429333 0 0 0 75.434666-70.843733 317.525333 317.525333 0 0 1 229.2736-119.04zM662.818133 187.767467c0.648533 0.733867 57.258667 63.5392 88.098134 140.3392 6.912 17.2032-3.413333 35.703467-20.548267 42.8032a351.624533 351.624533 0 0 0-139.434667 104.6016c-3.549867 4.096-7.168 8.0896-10.8544 12.032-7.236267 7.765333-19.677867 6.638933-25.787733-2.048-52.087467-74.018133-163.464533-222.2592-265.710933-291.549867a3.3792 3.3792 0 0 1 2.269866-6.178133h371.968z" />
    </svg>
  )
}
