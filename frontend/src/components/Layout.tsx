import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, teams, currentTeam, setCurrentTeam, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* 顶部导航 */}
      <header className="bg-brand-primary text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="text-xl font-bold tracking-wide">智汇·研管</Link>

            {/* 团队切换器 */}
            {teams.length > 1 && currentTeam && (
              <select
                className="bg-brand-primary-light text-white text-sm rounded px-2 py-1 border border-white/30"
                value={`${currentTeam.id}`}
                onChange={(e) => {
                  const t = teams.find(t => t.id === Number(e.target.value));
                  if (t) setCurrentTeam(t);
                }}
              >
                {teams.map(t => (
                  <option key={t.id} value={t.id}>
                    {t.name} · {t.role === 'owner' ? '教师' : t.role === 'supervisor' ? '主管' : t.role === 'co_manager' ? '协管员' : '成员'}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="flex items-center gap-4 text-sm">
            {currentTeam && (
              <span className="text-white/80">{currentTeam.name}</span>
            )}
            {user && (
              <>
                <span className="text-white/90">{user.display_name}</span>
                <button onClick={handleLogout} className="text-white/70 hover:text-white">退出</button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* 二级导航 */}
      {currentTeam && user && (
        <nav className="bg-white border-b shadow-sm">
          <div className="max-w-7xl mx-auto px-4 flex gap-6 h-10 items-center text-sm">
            <Link to="/" className="text-gray-600 hover:text-brand-primary">仪表盘</Link>
            <Link to="/members" className="text-gray-600 hover:text-brand-primary">成员管理</Link>
          </div>
        </nav>
      )}

      {/* 主内容 */}
      <main className="flex-1 max-w-7xl mx-auto px-4 py-6 w-full">
        {children}
      </main>
    </div>
  );
}
