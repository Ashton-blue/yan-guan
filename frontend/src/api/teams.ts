import api from './client'

export interface Team {
  id: number
  name: string
  description: string
  role: string
  created_at: string
}

export const teamApi = {
  // 获取团队列表
  listTeams: () => api.get<any, { data: Team[] }>('/teams'),

  // 创建团队
  createTeam: (data: { name: string; description?: string }) =>
    api.post<any, { data: Team }>('/teams', data),

  // 获取团队详情
  getTeam: (teamId: number) =>
    api.get<any, { data: Team }>(`/teams/${teamId}`),

  // 更新团队
  updateTeam: (teamId: number, data: { name?: string; description?: string }) =>
    api.put(`/teams/${teamId}`, data),

  // 删除团队
  deleteTeam: (teamId: number) =>
    api.delete(`/teams/${teamId}`),
}
