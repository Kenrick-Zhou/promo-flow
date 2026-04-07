import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-900">
      <Sidebar />
      <main className="flex-1 px-8 py-6 overflow-auto">
        <div className="mx-auto max-w-screen-xl">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
