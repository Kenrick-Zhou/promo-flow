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
      <h1 className="text-2xl font-bold text-gray-900 mb-6">管理设置</h1>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600">姓名</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">角色</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">加入时间</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {users.map((user) => (
              <tr key={user.id}>
                <td className="px-4 py-3 text-gray-900">{user.name}</td>
                <td className="px-4 py-3">
                  <select
                    className="border border-gray-300 rounded px-2 py-1 text-xs"
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
                <td className="px-4 py-3 text-gray-500">
                  {new Date(user.created_at).toLocaleDateString('zh-CN')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && users.length === 0 && (
          <p className="text-center py-10 text-gray-400">暂无用户</p>
        )}
      </div>
    </div>
  )
}
