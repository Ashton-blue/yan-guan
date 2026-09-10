import React, { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'

const NAV = [
  { to: '/dashboard', label: '仪表盘', icon: '📊' },
  { to: '/meetings', label: '组会管理', icon: '📅' },
  { to: '/members', label: '成员管理', icon: '👥' },
  { to: '/account', label: '账户管理', icon: '👤' },
  { to: '/policy', label: '政策助手', icon: '📜' },
]

const Layout: React.FC = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }
  const isActive = (to: string) => location.pathname.startsWith(to)

  return (
    <div className="min-h-screen bg-brand-bg-warm md:flex">
      {/* 移动端顶栏 */}
      <div className="md:hidden fixed top-0 left-0 right-0 bg-white text-brand-ink h-12 flex items-center justify-between px-3 z-40 shadow-sm border-b border-brand-line">
        <button onClick={() => setSidebarOpen(!sidebarOpen)} className="text-xl px-1" aria-label="菜单">☰</button>
        <span className="font-bold">研管·工作台</span>
        <span className="w-7"></span>
      </div>

      {/* 侧边栏遮罩（移动端） */}
      {sidebarOpen && (
        <div className="md:hidden fixed inset-0 bg-black/30 z-40" onClick={() => setSidebarOpen(false)} />
      )}

      {/* 侧边栏（净白） */}
      <aside className={`
        md:sticky md:top-0 fixed inset-y-0 left-0 w-64 bg-white border-r border-brand-line shadow-sm
        transform transition-transform duration-200 z-50 flex flex-col
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        <div className="h-14 flex items-center px-4 border-b border-brand-line flex-shrink-0">
          <span className="text-lg font-bold tracking-wide text-brand-ink">研管·工作台</span>
        </div>

        <nav className="flex-1 px-3 py-3 space-y-1 text-sm overflow-y-auto">
          {NAV.map((item) => (
            <a
              key={item.to}
              href={item.to}
              onClick={() => setSidebarOpen(false)}
              className={`${isActive(item.to) ? 'side-active' : 'side-item'} flex items-center gap-3 px-3 py-2.5 rounded-lg transition`}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </a>
          ))}
        </nav>

        <div className="px-3 py-3 border-t border-brand-line flex-shrink-0">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0 overflow-hidden"
              style={{ backgroundColor: user?.avatar_url ? 'transparent' : '#DBEAFE', color: '#1D4ED8' }}
            >
              {user?.avatar_url ? (
                <img src={user.avatar_url} className="w-9 h-9 rounded-full object-cover" alt="" />
              ) : (
                (user?.name?.[0] || 'U')
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-brand-ink truncate">{user?.name || '用户'}</p>
              <p className="text-xs text-brand-muted">研究室成员</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="mt-2 w-full text-left text-xs text-brand-muted hover:text-brand-danger px-2 py-1.5 rounded transition"
          >
            退出登录
          </button>
        </div>
      </aside>

      {/* 主内容区 */}
      <main className="flex-1 min-w-0 px-4 md:px-6 pb-6 pt-16 md:pt-6">
        <Outlet />
      </main>
    </div>
  )
}

export default Layout
