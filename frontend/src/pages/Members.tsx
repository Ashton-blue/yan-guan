import React from 'react'

const Members: React.FC = () => {
  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-brand-ink">👥 成员管理</h1>
          <p className="text-sm text-brand-muted mt-1">管理团队成员和权限</p>
        </div>
        <button className="bg-brand-primary text-white px-4 py-2 rounded-lg text-sm hover:bg-brand-primary-light transition">
          + 添加成员
        </button>
      </div>

      <div className="bg-white rounded-xl border border-brand-line overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-brand-line">
              <th className="text-left px-4 py-3 text-brand-muted font-medium">成员</th>
              <th className="text-left px-4 py-3 text-brand-muted font-medium">邮箱</th>
              <th className="text-left px-4 py-3 text-brand-muted font-medium">角色</th>
              <th className="text-left px-4 py-3 text-brand-muted font-medium">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-brand-line">
            <tr className="hover:bg-brand-bg-warm transition">
              <td className="px-4 py-3 font-medium">墨蓝的京亚</td>
              <td className="px-4 py-3 text-brand-muted">research_test_001@test.com</td>
              <td className="px-4 py-3"><span className="bg-brand-primary/10 text-brand-primary px-2 py-0.5 rounded-full text-xs">教师</span></td>
              <td className="px-4 py-3"><span className="text-brand-muted text-xs">所有者</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Members
