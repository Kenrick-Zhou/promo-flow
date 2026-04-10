import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { LayoutGrid, Upload, ClipboardCheck, Settings, LogOut } from 'lucide-react'

const navItems = [
  { to: '/', label: '素材广场', icon: LayoutGrid },
  { to: '/upload', label: '上传素材', icon: Upload },
]

const reviewerItems = [{ to: '/audit', label: '审核工作台', icon: ClipboardCheck }]
const adminItems = [{ to: '/admin', label: '管理设置', icon: Settings }]

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
    <div className="flex h-screen w-60 flex-col justify-between border-e border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800 sticky top-0">
      <div className="px-4 py-6">
        <span className="grid h-10 w-full place-content-center rounded-lg bg-purple-50 text-lg font-bold tracking-wide text-purple-600 dark:bg-purple-900 dark:text-purple-300">
          方小集
        </span>

        <ul className="mt-6 space-y-1">
          {allItems.map((item) => {
            const isActive = location.pathname === item.to
            const Icon = item.icon
            return (
              <li key={item.to}>
                <Link
                  to={item.to}
                  className={`flex items-center gap-3 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300'
                      : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-200'
                  }`}
                >
                  <Icon className="size-5" />
                  {item.label}
                </Link>
              </li>
            )
          })}
        </ul>
      </div>

      <div className="sticky inset-x-0 bottom-0 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3 p-4">
          <div className="size-10 rounded-full bg-purple-100 grid place-content-center text-sm font-semibold text-purple-700 dark:bg-purple-900 dark:text-purple-300">
            {user?.name?.[0] ?? '?'}
          </div>

          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate dark:text-white">
              {user?.name}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">{user?.role}</p>
          </div>

          <button
            onClick={() => {
              logout()
              navigate('/login')
            }}
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
            title="退出登录"
          >
            <LogOut className="size-5" />
          </button>
        </div>
      </div>
    </div>
  )
}
