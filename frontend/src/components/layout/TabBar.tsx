import { Link, useLocation } from 'react-router-dom'
import { LayoutGrid, Plus, User } from 'lucide-react'
import { clsx } from 'clsx'

const tabs = [
  { to: '/', label: '广场', icon: LayoutGrid },
  { to: '/me', label: '我的', icon: User },
] as const

export default function TabBar() {
  const location = useLocation()

  return (
    <nav className="fixed inset-x-0 bottom-0 z-50 border-t border-gray-200 bg-white/95 backdrop-blur-sm dark:border-gray-700 dark:bg-gray-800/95">
      <div className="mx-auto flex max-w-screen-xl items-center justify-around py-1">
        {/* 广场 */}
        <Link
          to={tabs[0].to}
          className={clsx(
            'flex flex-col items-center gap-0.5 px-4 py-1.5 text-xs font-medium transition-colors',
            location.pathname === tabs[0].to
              ? 'text-purple-600 dark:text-purple-400'
              : 'text-gray-500 dark:text-gray-400',
          )}
        >
          <LayoutGrid className="size-5" />
          <span>{tabs[0].label}</span>
        </Link>

        {/* 中间 + 号按钮 */}
        <Link
          to="/upload"
          className="flex -mt-5 size-12 items-center justify-center rounded-full bg-purple-600 text-white shadow-lg transition-transform active:scale-95 hover:bg-purple-700"
        >
          <Plus className="size-7" />
        </Link>

        {/* 我的 */}
        <Link
          to={tabs[1].to}
          className={clsx(
            'flex flex-col items-center gap-0.5 px-4 py-1.5 text-xs font-medium transition-colors',
            location.pathname.startsWith('/me')
              ? 'text-purple-600 dark:text-purple-400'
              : 'text-gray-500 dark:text-gray-400',
          )}
        >
          <User className="size-5" />
          <span>{tabs[1].label}</span>
        </Link>
      </div>
    </nav>
  )
}
