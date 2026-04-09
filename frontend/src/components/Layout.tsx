import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

export default function Layout() {
  return (
    <div className="min-h-screen" style={{ background: 'var(--color-bg)' }}>
      <Sidebar />
      <main className="ml-64 p-6 min-h-screen">
        <Outlet />
      </main>
    </div>
  )
}
