import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import { useAuthStore } from '@/store/auth'
import Dashboard from '@/pages/Dashboard'
import Upload from '@/pages/Upload'
import Audit from '@/pages/Audit'
import Admin from '@/pages/Admin'
import Login from '@/pages/Login'
import Me from '@/pages/Me'
import MyUploads from '@/pages/MyUploads'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user)
  return user?.role === 'admin' ? <>{children}</> : <Navigate to="/" replace />
}

function ReviewerRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user)
  return user?.role === 'reviewer' || user?.role === 'admin' ? (
    <>{children}</>
  ) : (
    <Navigate to="/" replace />
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <PrivateRoute>
              <Layout />
            </PrivateRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="upload" element={<Upload />} />
          <Route path="me" element={<Me />} />
          <Route path="me/uploads" element={<MyUploads />} />
          <Route
            path="audit"
            element={
              <ReviewerRoute>
                <Audit />
              </ReviewerRoute>
            }
          />
          <Route
            path="admin"
            element={
              <AdminRoute>
                <Admin />
              </AdminRoute>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
