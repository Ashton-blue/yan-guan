import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { register } from '../api/auth';

export default function Register() {
  const [form, setForm] = useState({ username: '', password: '', display_name: '', email: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { setAuth } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const data = await register(form);
      setAuth(data);
      navigate('/team/create');
    } catch (err: any) {
      setError(err.response?.data?.detail || '注册失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-bg-warm">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-sm">
        <h1 className="text-2xl font-bold text-brand-primary text-center mb-2">注册教师账号</h1>
        <p className="text-sm text-gray-500 text-center mb-6">注册后即可创建研究室团队</p>

        {error && (
          <div className="bg-red-50 text-red-600 text-sm p-3 rounded mb-4">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">登录账号</label>
            <input
              type="text"
              value={form.username}
              onChange={e => setForm({ ...form, username: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-brand-primary"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">姓名</label>
            <input
              type="text"
              value={form.display_name}
              onChange={e => setForm({ ...form, display_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-brand-primary"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">密码</label>
            <input
              type="password"
              value={form.password}
              onChange={e => setForm({ ...form, password: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-brand-primary"
              required
              minLength={6}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">邮箱（可选）</label>
            <input
              type="email"
              value={form.email}
              onChange={e => setForm({ ...form, email: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-brand-primary"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-brand-primary text-white py-2 rounded hover:bg-brand-primary-light disabled:opacity-50"
          >
            {submitting ? '注册中...' : '注册'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-4">
          已有账号？<Link to="/login" className="text-brand-primary hover:underline">登录</Link>
        </p>
      </div>
    </div>
  );
}
