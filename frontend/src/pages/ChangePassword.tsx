import React from 'react'

const ChangePassword: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-bg-warm">
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-brand-ink mb-6 text-center">修改密码</h1>
        <form className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-brand-ink mb-1">原密码</label>
            <input type="password" className="w-full px-4 py-2.5 border border-brand-line rounded-lg focus:outline-none focus:border-brand-primary bg-brand-bg-warm/50" />
          </div>
          <div>
            <label className="block text-sm font-medium text-brand-ink mb-1">新密码</label>
            <input type="password" className="w-full px-4 py-2.5 border border-brand-line rounded-lg focus:outline-none focus:border-brand-primary bg-brand-bg-warm/50" />
          </div>
          <div>
            <label className="block text-sm font-medium text-brand-ink mb-1">确认新密码</label>
            <input type="password" className="w-full px-4 py-2.5 border border-brand-line rounded-lg focus:outline-none focus:border-brand-primary bg-brand-bg-warm/50" />
          </div>
          <button type="submit" className="w-full bg-brand-primary text-white py-2.5 rounded-lg hover:bg-brand-primary-light transition">
            确认修改
          </button>
        </form>
      </div>
    </div>
  )
}

export default ChangePassword
