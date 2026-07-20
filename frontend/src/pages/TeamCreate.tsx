import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createTeam } from '../api/teams';

export default function TeamCreate() {
  const [form, setForm] = useState({ name: '', school: '', research_area: '', description: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await createTeam(form);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || '创建失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-lg mx-auto mt-10">
      <div className="bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-brand-primary mb-2">创建研究室团队</h1>
        <p className="text-sm text-gray-500 mb-6">首次使用，请先创建您的研究室团队</p>

        {error && (
          <div className="bg-red-50 text-red-600 text-sm p-3 rounded mb-4">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">团队名称 *</label>
            <input
              type="text"
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-brand-primary"
              required
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">所属院校</label>
            <input
              type="text"
              value={form.school}
              onChange={e => setForm({ ...form, school: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-brand-primary"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">研究领域</label>
            <input
              type="text"
              value={form.research_area}
              onChange={e => setForm({ ...form, research_area: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-brand-primary"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">团队简介</label>
            <textarea
              value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-brand-primary"
              rows={3}
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-brand-primary text-white py-2 rounded hover:bg-brand-primary-light disabled:opacity-50"
          >
            {submitting ? '创建中...' : '创建团队'}
          </button>
        </form>
      </div>
    </div>
  );
}
