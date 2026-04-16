import { Outlet } from 'react-router-dom'
import TabBar from './TabBar'

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-50 dark:bg-gray-900">
      <main className="flex-1 overflow-x-clip px-4 pb-20 pt-4">
        <div className="mx-auto max-w-screen-xl">
          <Outlet />
        </div>
      </main>
      <TabBar />
    </div>
  )
}
