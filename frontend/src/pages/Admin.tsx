import { useEffect, useState } from 'react'
import { Plus, Trash2, X } from 'lucide-react'
import api from '@/services/api'
import { useSystem } from '@/hooks/useSystem'
import type { CategoryTree, Tag, User } from '@/types'

const roleOptions = [
  { value: 'employee', label: '普通员工' },
  { value: 'reviewer', label: '审核人员' },
  { value: 'admin', label: '管理员' },
]

type TabKey = 'users' | 'categories' | 'tags'

const tabs: { key: TabKey; label: string }[] = [
  { key: 'users', label: '用户管理' },
  { key: 'categories', label: '类目管理' },
  { key: 'tags', label: '标签管理' },
]

export default function Admin() {
  const [activeTab, setActiveTab] = useState<TabKey>('users')

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6 dark:text-white">管理设置</h1>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-gray-700">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? 'bg-white text-purple-700 shadow-sm dark:bg-gray-800 dark:text-purple-300'
                : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'users' && <UsersTab />}
      {activeTab === 'categories' && <CategoriesTab />}
      {activeTab === 'tags' && <TagsTab />}
    </div>
  )
}

// ============================================================
// Users Tab
// ============================================================

function UsersTab() {
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
    await api.patch(`/admin/users/${userId}/role`, { role })
    fetchUsers()
  }

  return (
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
  )
}

// ============================================================
// Categories Tab
// ============================================================

function CategoriesTab() {
  const { listCategories, createCategory, updateCategory, deleteCategory } = useSystem()
  const [categories, setCategories] = useState<CategoryTree[]>([])
  const [newPrimaryName, setNewPrimaryName] = useState('')
  const [newPrimaryDesc, setNewPrimaryDesc] = useState('')
  const [addingChildFor, setAddingChildFor] = useState<number | null>(null)
  const [newChildName, setNewChildName] = useState('')
  const [newChildDesc, setNewChildDesc] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [editDesc, setEditDesc] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function refresh() {
    const data = await listCategories()
    setCategories(data)
  }

  useEffect(() => {
    void (async () => {
      const data = await listCategories()
      setCategories(data)
    })()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAddPrimary() {
    if (!newPrimaryName.trim() || !newPrimaryDesc.trim() || submitting) return
    setError(null)
    setSubmitting(true)
    try {
      await createCategory({ name: newPrimaryName.trim(), description: newPrimaryDesc.trim() })
      setNewPrimaryName('')
      setNewPrimaryDesc('')
      await refresh()
    } catch {
      setError('创建失败，类目名可能已存在')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleAddChild(parentId: number) {
    if (!newChildName.trim() || !newChildDesc.trim() || submitting) return
    setError(null)
    setSubmitting(true)
    try {
      await createCategory({
        name: newChildName.trim(),
        description: newChildDesc.trim(),
        parent_id: parentId,
      })
      setNewChildName('')
      setNewChildDesc('')
      setAddingChildFor(null)
      await refresh()
    } catch {
      setError('创建失败，类目名可能已存在')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleSaveEdit(id: number) {
    if (!editName.trim() || !editDesc.trim()) return
    setError(null)
    try {
      await updateCategory(id, { name: editName.trim(), description: editDesc.trim() })
      setEditingId(null)
      await refresh()
    } catch {
      setError('更新失败')
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await deleteCategory(id)
      await refresh()
    } catch {
      setError('删除失败，该类目下可能有子类目或素材')
    }
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Add primary category */}
      <div className="flex flex-col gap-2 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-200">添加一级类目</p>
        <div className="flex gap-2">
          <input
            type="text"
            className="w-40 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
            value={newPrimaryName}
            onChange={(e) => setNewPrimaryName(e.target.value)}
            placeholder="类目名称"
          />
          <input
            type="text"
            className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
            value={newPrimaryDesc}
            onChange={(e) => setNewPrimaryDesc(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddPrimary()}
            placeholder="类目说明（如：开业/环创/业绩/技师）"
          />
          <button
            onClick={handleAddPrimary}
            disabled={submitting}
            className="inline-flex items-center gap-1 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
          >
            <Plus className="size-4" />
            添加
          </button>
        </div>
      </div>

      {/* Category tree */}
      <div className="space-y-3">
        {categories.map((primary) => (
          <div
            key={primary.id}
            className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
          >
            {/* Primary category header */}
            <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-gray-700">
              {editingId === primary.id ? (
                <div className="flex items-center gap-2 flex-1 mr-2">
                  <input
                    type="text"
                    className="w-28 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    placeholder="类目名称"
                    autoFocus
                  />
                  <input
                    type="text"
                    className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                    value={editDesc}
                    onChange={(e) => setEditDesc(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSaveEdit(primary.id)}
                    placeholder="类目说明"
                  />
                  <button
                    onClick={() => handleSaveEdit(primary.id)}
                    className="text-sm text-purple-600 hover:text-purple-700"
                  >
                    保存
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    className="text-sm text-gray-400 hover:text-gray-600"
                  >
                    取消
                  </button>
                </div>
              ) : (
                <div
                  className="flex flex-col cursor-pointer hover:text-purple-600 group"
                  onClick={() => {
                    setEditingId(primary.id)
                    setEditName(primary.name)
                    setEditDesc(primary.description)
                  }}
                >
                  <span className="font-medium text-gray-900 group-hover:text-purple-600 dark:text-white">
                    {primary.name}
                  </span>
                  {primary.description && (
                    <span className="text-xs text-gray-400 dark:text-gray-500">
                      {primary.description}
                    </span>
                  )}
                </div>
              )}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setAddingChildFor(addingChildFor === primary.id ? null : primary.id)
                    setNewChildName('')
                  }}
                  className="text-sm text-purple-600 hover:text-purple-700"
                >
                  + 添加子类目
                </button>
                <button
                  onClick={() => handleDelete(primary.id)}
                  className="rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20"
                >
                  <Trash2 className="size-4" />
                </button>
              </div>
            </div>

            {/* Secondary categories */}
            <div className="px-4 py-2">
              {primary.children.length === 0 && addingChildFor !== primary.id && (
                <p className="py-2 text-sm text-gray-400 dark:text-gray-500">暂无子类目</p>
              )}
              <div className="flex flex-wrap gap-2">
                {primary.children.map((child) => (
                  <span
                    key={child.id}
                    className="group inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1.5 text-sm text-gray-700 dark:bg-gray-700 dark:text-gray-300"
                  >
                    {editingId === child.id ? (
                      <>
                        <input
                          type="text"
                          className="w-20 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs dark:border-gray-600 dark:bg-gray-700"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          placeholder="名称"
                          autoFocus
                        />
                        <input
                          type="text"
                          className="w-32 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs dark:border-gray-600 dark:bg-gray-700"
                          value={editDesc}
                          onChange={(e) => setEditDesc(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && handleSaveEdit(child.id)}
                          placeholder="说明"
                        />
                        <button
                          onClick={() => handleSaveEdit(child.id)}
                          className="text-xs text-purple-600"
                        >
                          保存
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="text-xs text-gray-400"
                        >
                          <X className="size-3" />
                        </button>
                      </>
                    ) : (
                      <>
                        <span
                          className="cursor-pointer hover:text-purple-600"
                          onClick={() => {
                            setEditingId(child.id)
                            setEditName(child.name)
                            setEditDesc(child.description)
                          }}
                        >
                          {child.name}
                        </span>
                        <button
                          onClick={() => handleDelete(child.id)}
                          className="ml-0.5 hidden rounded-full p-0.5 text-gray-400 hover:text-red-500 group-hover:inline-flex"
                        >
                          <X className="size-3" />
                        </button>
                      </>
                    )}
                  </span>
                ))}

                {/* Add child input */}
                {addingChildFor === primary.id && (
                  <div className="inline-flex items-center gap-1">
                    <input
                      type="text"
                      className="w-24 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                      value={newChildName}
                      onChange={(e) => setNewChildName(e.target.value)}
                      placeholder="名称"
                      autoFocus
                    />
                    <input
                      type="text"
                      className="w-36 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                      value={newChildDesc}
                      onChange={(e) => setNewChildDesc(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleAddChild(primary.id)}
                      placeholder="说明"
                    />
                    <button
                      onClick={() => handleAddChild(primary.id)}
                      disabled={submitting}
                      className="rounded-lg bg-purple-600 px-3 py-1.5 text-sm text-white hover:bg-purple-700 disabled:opacity-50"
                    >
                      添加
                    </button>
                    <button
                      onClick={() => setAddingChildFor(null)}
                      className="rounded-lg p-1.5 text-gray-400 hover:text-gray-600"
                    >
                      <X className="size-4" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {categories.length === 0 && (
          <p className="text-center py-10 text-gray-400 dark:text-gray-500">
            暂无类目，请添加一级类目
          </p>
        )}
      </div>
    </div>
  )
}

// ============================================================
// Tags Tab
// ============================================================

function TagsTab() {
  const { listTags, createTag, updateTag, deleteTag } = useSystem()
  const [tags, setTags] = useState<Tag[]>([])
  const [newTagName, setNewTagName] = useState('')
  const [isSystem, setIsSystem] = useState(true)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    const data = await listTags()
    setTags(data)
  }

  useEffect(() => {
    void (async () => {
      const data = await listTags()
      setTags(data)
    })()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAdd() {
    if (!newTagName.trim()) return
    setError(null)
    try {
      await createTag({ name: newTagName.trim(), is_system: isSystem })
      setNewTagName('')
      await refresh()
    } catch {
      setError('创建失败，标签名可能已存在')
    }
  }

  async function handleSaveEdit(id: number) {
    if (!editName.trim()) return
    setError(null)
    try {
      await updateTag(id, { name: editName.trim() })
      setEditingId(null)
      await refresh()
    } catch {
      setError('更新失败')
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await deleteTag(id)
      await refresh()
    } catch {
      setError('删除失败，该标签可能正在被素材使用')
    }
  }

  async function handleToggleSystem(tag: Tag) {
    try {
      await updateTag(tag.id, { is_system: !tag.is_system })
      await refresh()
    } catch {
      setError('更新失败')
    }
  }

  const systemTags = tags.filter((t) => t.is_system)
  const customTags = tags.filter((t) => !t.is_system)

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Add tag */}
      <div className="flex gap-2">
        <input
          type="text"
          className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          value={newTagName}
          onChange={(e) => setNewTagName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          placeholder="输入标签名称"
        />
        <label className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-300">
          <input
            type="checkbox"
            checked={isSystem}
            onChange={(e) => setIsSystem(e.target.checked)}
            className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
          />
          系统默认
        </label>
        <button
          onClick={handleAdd}
          className="inline-flex items-center gap-1 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700"
        >
          <Plus className="size-4" />
          添加标签
        </button>
      </div>

      {/* System tags */}
      <div>
        <h3 className="mb-3 text-sm font-medium text-gray-500 dark:text-gray-400">系统默认标签</h3>
        <div className="flex flex-wrap gap-2">
          {systemTags.map((tag) => (
            <TagChip
              key={tag.id}
              tag={tag}
              editingId={editingId}
              editName={editName}
              setEditingId={setEditingId}
              setEditName={setEditName}
              onSave={handleSaveEdit}
              onDelete={handleDelete}
              onToggleSystem={handleToggleSystem}
            />
          ))}
          {systemTags.length === 0 && (
            <p className="text-sm text-gray-400 dark:text-gray-500">暂无系统默认标签</p>
          )}
        </div>
      </div>

      {/* Custom tags */}
      {customTags.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-medium text-gray-500 dark:text-gray-400">
            用户自定义标签
          </h3>
          <div className="flex flex-wrap gap-2">
            {customTags.map((tag) => (
              <TagChip
                key={tag.id}
                tag={tag}
                editingId={editingId}
                editName={editName}
                setEditingId={setEditingId}
                setEditName={setEditName}
                onSave={handleSaveEdit}
                onDelete={handleDelete}
                onToggleSystem={handleToggleSystem}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

interface TagChipProps {
  tag: Tag
  editingId: number | null
  editName: string
  setEditingId: (id: number | null) => void
  setEditName: (name: string) => void
  onSave: (id: number) => void
  onDelete: (id: number) => void
  onToggleSystem: (tag: Tag) => void
}

function TagChip({
  tag,
  editingId,
  editName,
  setEditingId,
  setEditName,
  onSave,
  onDelete,
  onToggleSystem,
}: TagChipProps) {
  if (editingId === tag.id) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1.5 dark:bg-gray-700">
        <input
          type="text"
          className="w-20 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs dark:border-gray-600 dark:bg-gray-700"
          value={editName}
          onChange={(e) => setEditName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSave(tag.id)}
          autoFocus
        />
        <button onClick={() => onSave(tag.id)} className="text-xs text-purple-600">
          保存
        </button>
        <button onClick={() => setEditingId(null)} className="text-xs text-gray-400">
          <X className="size-3" />
        </button>
      </span>
    )
  }

  return (
    <span
      className={`group inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-sm ${
        tag.is_system
          ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'
          : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
      }`}
    >
      <span
        className="cursor-pointer hover:underline"
        onClick={() => {
          setEditingId(tag.id)
          setEditName(tag.name)
        }}
      >
        {tag.name}
      </span>
      <button
        onClick={() => onToggleSystem(tag)}
        className="ml-0.5 hidden text-[10px] opacity-60 hover:opacity-100 group-hover:inline-flex"
        title={tag.is_system ? '取消系统标签' : '设为系统标签'}
      >
        {tag.is_system ? '取消默认' : '设为默认'}
      </button>
      <button
        onClick={() => onDelete(tag.id)}
        className="ml-0.5 hidden rounded-full p-0.5 text-gray-400 hover:text-red-500 group-hover:inline-flex"
      >
        <X className="size-3" />
      </button>
    </span>
  )
}
