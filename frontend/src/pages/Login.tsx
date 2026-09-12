import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const Login: React.FC = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || '登录失败，请检查邮箱和密码')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-bg-warm">
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-brand-ink">智汇·研管</h1>
          <p className="text-brand-muted mt-2">科研政策智能助手</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
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
              placeholder="请输入密码"
              required
            />
          </div>

          {error && (
            <div className="text-red-500 text-sm">{error}</div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-brand-primary text-white py-2.5 rounded-lg hover:bg-brand-primary-light transition disabled:opacity-50"
          >
            {isLoading ? '登录中...' : '登录'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <Link to="/register" className="text-sm text-brand-primary hover:underline">
            还没有账号？立即注册
          </Link>
        </div>

        <div className="mt-4 p-3 bg-brand-bg-warm rounded-lg">
          <p className="text-xs text-brand-muted">测试账号：</p>
          <p className="text-xs text-brand-muted mt-1">教师：research_test_001@test.com / YanGuan2026!</p>
        </div>
      </div>
    </div>
  )
}

export default Login
