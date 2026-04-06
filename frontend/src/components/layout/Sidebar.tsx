import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

const navItems = [
  { to: '/', label: '素材广场' },
  { to: '/upload', label: '上传素材' },
  { to: '/search', label: '智能搜索' },
]

const reviewerItems = [{ to: '/audit', label: '审核工作台' }]
const adminItems = [{ to: '/admin', label: '管理设置' }]

export default function Sidebar() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const allItems = [
    ...navItems,
    ...(user?.role === 'reviewer' || user?.role === 'admin' ? reviewerItems : []),
    ...(user?.role === 'admin' ? adminItems : []),
  ]

  return (
    <aside className="w-56 shrink-0 border-r border-gray-200 flex flex-col h-screen sticky top-0">
      <div className="px-6 py-5 border-b border-gray-200">
        <span className="text-xl font-bold text-purple-600">PromoFlow</span>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {allItems.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              location.pathname === item.to
                ? 'bg-purple-50 text-purple-700'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="px-4 py-4 border-t border-gray-200">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-full bg-purple-200 flex items-center justify-center text-purple-700 font-semibold text-sm">
            {user?.name?.[0] ?? '?'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">{user?.name}</p>
            <p className="text-xs text-gray-500">{user?.role}</p>
          </div>
        </div>
        <button
          onClick={() => {
            logout()
            navigate('/login')
          }}
          className="w-full text-left text-xs text-gray-500 hover:text-gray-700"
        >
          退出登录
        </button>
      </div>
    </aside>
  )
}
