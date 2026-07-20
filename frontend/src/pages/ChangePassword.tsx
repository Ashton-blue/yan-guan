import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { changePassword } from '../api/auth';

export default function ChangePassword() {
  const [form, setForm] = useState({ old_password: '', new_password: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { user } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setSubmitting(true);
    try {
      await changePassword(form.old_password, form.new_password);
      setSuccess('密码修改成功');
      setTimeout(() => navigate('/'), 1000);
    } catch (err: any) {
      setError(err.response?.data?.detail || '修改失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10">
      <div className="bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-brand-primary mb-2">修改密码</h1>
        {user?.must_change_password && (
          <p className="text-sm text-orange-600 mb-4">首次登录，请先修改初始密码</p>
        )}

        {error && (
          <div className="bg-red-50 text-red-600 text-sm p-3 rounded mb-4">{error}</div>
        )}
        {success && (
          <div className="bg-green-50 text-green-600 text-sm p-3 rounded mb-4">{success}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">当前密码</label>
            <input
              type="password"
              value={form.old_password}
              onChange={e => setForm({ ...form, old_password: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-brand-primary"
              required
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">新密码（至少6位）</label>
            <input
              type="password"
              value={form.new_password}
              onChange={e => setForm({ ...form, new_password: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-brand-primary"
              required
              minLength={6}
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-brand-primary text-white py-2 rounded hover:bg-brand-primary-light disabled:opacity-50"
          >
            {submitting ? '修改中...' : '确认修改'}
          </button>
        </form>
      </div>
    </div>
  );
}
