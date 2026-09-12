import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const Register: React.FC = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }

    try {
      await register(email, password, name)
      setSuccess(true)
      setTimeout(() => navigate('/login'), 2000)
    } catch (err: any) {
      setError(err.response?.data?.detail || '注册失败')
    }
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-bg-warm">
        <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md text-center">
          <div className="text-green-500 text-5xl mb-4">✓</div>
          <h2 className="text-xl font-bold text-brand-ink mb-2">注册成功！</h2>
          <p className="text-brand-muted">正在跳转到登录页面...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-bg-warm">
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-brand-ink">创建账号</h1>
          <p className="text-brand-muted mt-2">加入智汇·研管</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-brand-ink mb-1">姓名</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2.5 border border-brand-line rounded-lg focus:outline-none focus:border-brand-primary bg-brand-bg-warm/50"
              placeholder="请输入姓名"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-brand-ink mb-1">邮箱</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2.5 border border-brand-line rounded-lg focus:outline-none focus:border-brand-primary bg-brand-bg-warm/50"
              placeholder="请输入邮箱"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-brand-ink mb-1">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 border border-brand-line rounded-lg focus:outline-none focus:border-brand-primary bg-brand-bg-warm/50"
              placeholder="请输入密码（至少6位）"
              minLength={6}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-brand-ink mb-1">确认密码</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-2.5 border border-brand-line rounded-lg focus:outline-none focus:border-brand-primary bg-brand-bg-warm/50"
              placeholder="请再次输入密码"
              minLength={6}
              required
            />
          </div>

          {error && (
            <div className="text-red-500 text-sm">{error}</div>
          )}

          <button
            type="submit"
            className="w-full bg-brand-primary text-white py-2.5 rounded-lg hover:bg-brand-primary-light transition"
          >
            注册
          </button>
        </form>

        <div className="mt-6 text-center">
          <a href="/login" className="text-sm text-brand-primary hover:underline">
            已有账号？立即登录
          </a>
        </div>
      </div>
    </div>
  )
}

export default Register
