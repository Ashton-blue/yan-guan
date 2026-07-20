import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { listMembers, addMember, removeMember, resetPassword, MemberResponse } from '../api/members';

const ROLE_LABELS: Record<string, string> = {
  owner: '教师',
  supervisor: '主管',
  co_manager: '协管员',
  student: '学生',
};

export default function Members() {
  const { currentTeam } = useAuth();
  const [members, setMembers] = useState<MemberResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState({ username: '', display_name: '', role: 'student' });
  const [addError, setAddError] = useState('');
  const [addResult, setAddResult] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);

  const loadMembers = async () => {
    if (!currentTeam) return;
    setLoading(true);
    try {
      const data = await listMembers(currentTeam.id);
      setMembers(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMembers();
  }, [currentTeam]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentTeam) return;
    setAddError('');
    setAddResult(null);
    setSubmitting(true);
    try {
      const result = await addMember(currentTeam.id, addForm);
      setAddResult(result);
      setAddForm({ username: '', display_name: '', role: 'student' });
      loadMembers();
    } catch (err: any) {
      setAddError(err.response?.data?.detail || '添加失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemove = async (userId: number, name: string) => {
    if (!currentTeam || !window.confirm(`确认移除成员「${name}」？`)) return;
    try {
      await removeMember(currentTeam.id, userId);
      loadMembers();
    } catch (err: any) {
      alert(err.response?.data?.detail || '移除失败');
    }
  };

  const handleResetPwd = async (userId: number, name: string) => {
    if (!currentTeam || !window.confirm(`确认重置「${name}」的密码？`)) return;
    try {
      const result = await resetPassword(currentTeam.id, userId);
      alert(`新密码：${result.new_password}\n请告知成员登录后修改密码。`);
    } catch (err: any) {
      alert(err.response?.data?.detail || '重置失败');
    }
  };

  if (!currentTeam) return null;

  const canManage = ['owner', 'supervisor', 'co_manager'].includes(currentTeam.role);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800">成员管理</h1>
        {canManage && (
          <button
            onClick={() => { setShowAdd(!showAdd); setAddResult(null); }}
            className="bg-brand-primary text-white px-4 py-2 rounded text-sm hover:bg-brand-primary-light"
          >
            {showAdd ? '取消' : '+ 新增成员'}
          </button>
        )}
      </div>

      {/* 新增成员表单 */}
      {showAdd && (
        <div className="bg-white p-6 rounded-lg shadow-sm mb-6">
          <h2 className="font-bold text-gray-700 mb-4">新增成员</h2>

          {addError && <div className="bg-red-50 text-red-600 text-sm p-3 rounded mb-4">{addError}</div>}

          {addResult && (
            <div className="bg-green-50 text-green-700 text-sm p-3 rounded mb-4">
              添加成功！<br />
              成员：{addResult.member.display_name}（{addResult.member.username}）<br />
              初始密码：<strong className="text-brand-primary">{addResult.initial_password}</strong>
              <br />
              <span className="text-gray-500">请将密码告知该成员，首次登录将强制修改。</span>
            </div>
          )}

          <form onSubmit={handleAdd} className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">账号 *</label>
              <input
                type="text"
                value={addForm.username}
                onChange={e => setAddForm({ ...addForm, username: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-brand-primary"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">姓名 *</label>
              <input
                type="text"
                value={addForm.display_name}
                onChange={e => setAddForm({ ...addForm, display_name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-brand-primary"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">角色</label>
              <select
                value={addForm.role}
                onChange={e => setAddForm({ ...addForm, role: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-brand-primary"
              >
                <option value="student">学生</option>
                <option value="co_manager">协管员</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={submitting}
                className="bg-brand-primary text-white px-4 py-2 rounded text-sm hover:bg-brand-primary-light disabled:opacity-50 w-full"
              >
                {submitting ? '添加中...' : '添加'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 成员列表 */}
      {loading ? (
        <div className="text-center text-gray-500">加载中...</div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500">
              <tr>
                <th className="text-left px-4 py-3">姓名</th>
                <th className="text-left px-4 py-3">账号</th>
                <th className="text-left px-4 py-3">角色</th>
                <th className="text-left px-4 py-3">加入时间</th>
                {canManage && <th className="text-right px-4 py-3">操作</th>}
              </tr>
            </thead>
            <tbody className="divide-y">
              {members.map(m => (
                <tr key={m.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{m.display_name}</td>
                  <td className="px-4 py-3 text-gray-500">{m.username}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium
                      ${m.role === 'owner' ? 'bg-red-50 text-brand-primary' :
                        m.role === 'supervisor' ? 'bg-orange-50 text-orange-600' :
                        m.role === 'co_manager' ? 'bg-blue-50 text-blue-600' :
                        'bg-gray-50 text-gray-600'}`}>
                      {ROLE_LABELS[m.role] || m.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{new Date(m.joined_at).toLocaleDateString()}</td>
                  {canManage && m.role !== 'owner' && (
                    <td className="px-4 py-3 text-right space-x-2">
                      <button
                        onClick={() => handleResetPwd(m.user_id, m.display_name)}
                        className="text-blue-600 hover:underline text-xs"
                      >
                        重置密码
                      </button>
                      <button
                        onClick={() => handleRemove(m.user_id, m.display_name)}
                        className="text-red-500 hover:underline text-xs"
                      >
                        移除
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
