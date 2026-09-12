import React from 'react'
import { Link } from 'react-router-dom'

const Dashboard: React.FC = () => {
  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-brand-ink">📊 仪表盘</h1>
          <p className="text-sm text-brand-muted mt-1">欢迎使用智汇·研管系统</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-brand-line p-5">
          <div className="text-3xl font-bold text-brand-primary">12</div>
          <div className="text-sm text-brand-muted mt-1">政策文档</div>
        </div>
        <div className="bg-white rounded-xl border border-brand-line p-5">
          <div className="text-3xl font-bold text-brand-primary">8</div>
          <div className="text-sm text-brand-muted mt-1">申报材料</div>
        </div>
        <div className="bg-white rounded-xl border border-brand-line p-5">
          <div className="text-3xl font-bold text-green-500">3</div>
          <div className="text-sm text-brand-muted mt-1">即将到期</div>
        </div>
        <div className="bg-white rounded-xl border border-brand-line p-5">
          <div className="text-3xl font-bold text-blue-500">25</div>
          <div className="text-sm text-brand-muted mt-1">问答记录</div>
        </div>
      </div>

      <div className="mt-6 bg-white rounded-xl border border-brand-line p-5">
        <h2 className="font-medium text-brand-ink mb-4">快速导航</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Link to="/policy" className="p-3 bg-brand-bg-warm rounded-lg text-center hover:bg-brand-primary hover:text-white transition">
            📜 政策助手
          </Link>
          <Link to="/members" className="p-3 bg-brand-bg-warm rounded-lg text-center hover:bg-brand-primary hover:text-white transition">
            👥 成员管理
          </Link>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
