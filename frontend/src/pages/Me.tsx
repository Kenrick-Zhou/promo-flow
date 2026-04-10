import { Link, useNavigate } from 'react-router-dom'
import { Upload, ClipboardCheck, Settings, LogOut, ChevronRight } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'

const ROLE_LABELS: Record<string, string> = {
  employee: '普通员工',
  reviewer: '审核人员',
  admin: '管理员',
}

export default function Me() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const isReviewerOrAdmin = user?.role === 'reviewer' || user?.role === 'admin'
  const isAdmin = user?.role === 'admin'

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="space-y-4">
      {/* 用户信息 */}
      <div className="flex items-center gap-4 rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800">
        {user?.avatar_url ? (
          <img
            src={user.avatar_url}
            alt={user.name}
            className="size-14 rounded-full object-cover"
          />
        ) : (
          <div className="grid size-14 place-content-center rounded-full bg-purple-100 text-xl font-semibold text-purple-700 dark:bg-purple-900 dark:text-purple-300">
            {user?.name?.[0] ?? '?'}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="truncate text-lg font-semibold text-gray-900 dark:text-white">
            {user?.name}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {ROLE_LABELS[user?.role ?? ''] ?? user?.role}
          </p>
        </div>
      </div>

      {/* 功能菜单 */}
      <div className="overflow-hidden rounded-2xl bg-white shadow-sm dark:bg-gray-800">
        <MenuItem to="/me/uploads" icon={Upload} label="我的上传" />
        {isReviewerOrAdmin && <MenuItem to="/audit" icon={ClipboardCheck} label="审核工作台" />}
        {isAdmin && <MenuItem to="/admin" icon={Settings} label="管理设置" />}
      </div>

      {/* 退出登录 */}
      <div className="overflow-hidden rounded-2xl bg-white shadow-sm dark:bg-gray-800">
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 px-5 py-4 text-red-500 transition-colors active:bg-gray-50 dark:active:bg-gray-700"
        >
          <LogOut className="size-5" />
          <span className="text-sm font-medium">退出登录</span>
        </button>
      </div>
    </div>
  )
}

interface MenuItemProps {
  to: string
  icon: React.ComponentType<{ className?: string }>
  label: string
}

function MenuItem({ to, icon: Icon, label }: MenuItemProps) {
  return (
    <Link
      to={to}
      className="flex items-center gap-3 border-b border-gray-100 px-5 py-4 transition-colors last:border-b-0 active:bg-gray-50 dark:border-gray-700 dark:active:bg-gray-700"
    >
      <Icon className="size-5 text-gray-600 dark:text-gray-400" />
      <span className="flex-1 text-sm font-medium text-gray-900 dark:text-gray-100">{label}</span>
      <ChevronRight className="size-4 text-gray-400" />
    </Link>
  )
}
