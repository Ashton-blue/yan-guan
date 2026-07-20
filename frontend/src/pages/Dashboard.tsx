import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getTeam } from '../api/teams';
import { listMembers } from '../api/members';

export default function Dashboard() {
  const { currentTeam } = useAuth();
  const [team, setTeam] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!currentTeam) return;
    setLoading(true);
    Promise.all([
      getTeam(currentTeam.id),
      listMembers(currentTeam.id),
    ])
      .then(([t, m]) => {
        setTeam(t);
        setMembers(m);
      })
      .finally(() => setLoading(false));
  }, [currentTeam]);

  if (!currentTeam) {
    return (
      <div className="text-center mt-20">
        <p className="text-gray-500 mb-4">您还没有创建或加入任何团队</p>
        <a href="/team/create" className="bg-brand-primary text-white px-6 py-2 rounded hover:bg-brand-primary-light">
          创建团队
        </a>
      </div>
    );
  }

  if (loading) return <div className="text-center mt-10 text-gray-500">加载中...</div>;

  const ownerCount = members.filter(m => m.role === 'owner').length;
  const supCount = members.filter(m => m.role === 'supervisor').length;
  const studentCount = members.filter(m => m.role === 'student').length;

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-800 mb-6">
        {team?.name || currentTeam.name}
        <span className="ml-2 text-sm font-normal text-gray-400">
          · {currentTeam.role === 'owner' ? '教师' : currentTeam.role === 'supervisor' ? '主管' : '成员'}
        </span>
      </h1>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-4 rounded-lg shadow-sm border-l-4 border-brand-primary">
          <div className="text-2xl font-bold text-brand-primary">{members.length}</div>
          <div className="text-sm text-gray-500">总成员</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow-sm border-l-4 border-blue-500">
          <div className="text-2xl font-bold text-blue-600">{ownerCount}</div>
          <div className="text-sm text-gray-500">教师</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow-sm border-l-4 border-orange-500">
          <div className="text-2xl font-bold text-orange-600">{supCount}</div>
          <div className="text-sm text-gray-500">主管</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow-sm border-l-4 border-green-500">
          <div className="text-2xl font-bold text-green-600">{studentCount}</div>
          <div className="text-sm text-gray-500">学生</div>
        </div>
      </div>

      {/* 团队信息 */}
      {team && (
        <div className="bg-white p-6 rounded-lg shadow-sm">
          <h2 className="font-bold text-gray-700 mb-3">团队信息</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            {team.school && <div><span className="text-gray-400">院校：</span>{team.school}</div>}
            {team.research_area && <div><span className="text-gray-400">领域：</span>{team.research_area}</div>}
            {team.description && <div className="col-span-2"><span className="text-gray-400">简介：</span>{team.description}</div>}
          </div>
        </div>
      )}
    </div>
  );
}
