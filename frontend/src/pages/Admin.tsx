import { useEffect, useState } from 'react'
import api from '@/services/api'
import type { User } from '@/types'

const roleOptions = [
  { value: 'employee', label: '普通员工' },
  { value: 'reviewer', label: '审核人员' },
  { value: 'admin', label: '管理员' },
]

export default function Admin() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)

  async function fetchUsers() {
    setLoading(true)
    try {
      const { data } = await api.get<User[]>('/admin/users')
      setUsers(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  async function handleRoleChange(userId: number, role: string) {
    await api.patch(`/admin/users/${userId}/role`, null, { params: { role } })
    fetchUsers()
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6 dark:text-white">管理设置</h1>
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <table className="w-full text-sm">
          <thead className="border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900">
            <tr>
              <th className="whitespace-nowrap px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
                姓名
              </th>
              <th className="whitespace-nowrap px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
                角色
              </th>
              <th className="whitespace-nowrap px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
                加入时间
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {users.map((user) => (
              <tr
                key={user.id}
                className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                <td className="whitespace-nowrap px-4 py-3 font-medium text-gray-900 dark:text-white">
                  {user.name}
                </td>
                <td className="whitespace-nowrap px-4 py-3">
                  <select
                    className="rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-xs text-gray-700 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                    value={user.role}
                    onChange={(e) => handleRoleChange(user.id, e.target.value)}
                  >
                    {roleOptions.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-gray-500 dark:text-gray-400">
                  {new Date(user.created_at).toLocaleDateString('zh-CN')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && users.length === 0 && (
          <p className="text-center py-10 text-gray-400 dark:text-gray-500">暂无用户</p>
        )}
      </div>
    </div>
  )
}
