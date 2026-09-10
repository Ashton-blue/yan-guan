import api from './client'

export interface Member {
  id: number
  user_id: number
  email: string
  name: string
  role: string
  created_at: string
}

export const memberApi = {
  // 获取团队成员列表
  listMembers: (teamId: number) =>
    api.get<any, { data: Member[] }>(`/teams/${teamId}/members`),

  // 添加成员
  addMember: (teamId: number, data: { email: string; role: string }) =>
    api.post<any, { data: Member }>(`/teams/${teamId}/members`, data),

  // 更新成员
  updateMember: (teamId: number, memberId: number, data: { role?: string; is_active?: boolean }) =>
    api.put(`/teams/${teamId}/members/${memberId}`, data),

  // 移除成员
  removeMember: (teamId: number, memberId: number) =>
    api.delete(`/teams/${teamId}/members/${memberId}`),

  // 获取当前用户角色
  getMyRole: (teamId: number) =>
    api.get<any, { data: { role: string } }>(`/teams/${teamId}/members/me`),
}
