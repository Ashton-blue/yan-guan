import api from './client'

// ---------- 账户管理（P0 批次 A） ----------

export interface UserProfile {
  id: number
  email: string
  name: string
  avatar_url: string | null
  research_area: string | null
  bio: string | null
  status: string
  must_change_password: boolean
  created_at: string
}

export interface ProfileUpdate {
  name?: string
  avatar_url?: string
  research_area?: string
  bio?: string
}

export interface TeamInvite {
  id: number
  code: string
  role: string
  status: string
  invited_by_name: string | null
  expires_at: string | null
  created_at: string
}

export interface MemberRow {
  id: number
  user_id: number
  email: string
  name: string
  role: string
  invited_by: number | null
  created_at: string
}

export const accountApi = {
  // 个人资料
  getMe: () => api.get<any, { data: UserProfile }>('/users/me'),
  updateMe: (data: ProfileUpdate) => api.put<any, { data: UserProfile }>('/users/me', data),

  // 团队邀请码
  listInvites: (teamId: number) =>
    api.get<any, { data: TeamInvite[] }>(`/teams/${teamId}/invites`),
  createInvite: (teamId: number, data: { role?: string; valid_days?: number }) =>
    api.post<any, { data: TeamInvite }>(`/teams/${teamId}/invites`, data),
  revokeInvite: (teamId: number, inviteId: number) =>
    api.delete<any, { message: string }>(`/teams/${teamId}/invites/${inviteId}`),
  joinTeam: (code: string) =>
    api.post<any, { message: string; team_id: number; role: string }>('/teams/join', { code }),

  // 团队成员生命周期（角色/状态调整、移除）
  listMembers: (teamId: number) =>
    api.get<any, { data: MemberRow[] }>(`/teams/${teamId}/members`),
  patchMember: (teamId: number, userId: number, data: { role?: string; is_active?: boolean }) =>
    api.patch<any, { user_id: number; role: string; is_active: boolean; changed: Record<string, unknown> }>(
      `/teams/${teamId}/members/${userId}`, data),
  removeMember: (teamId: number, userId: number) =>
    api.delete<any, { message: string }>(`/teams/${teamId}/members/${userId}`),

  // 密码找回 / 管理员重置
  forgotPassword: (email: string) =>
    api.post<any, { message: string; target_name?: string }>('/auth/forgot-password', { email }),
  resetMemberPassword: (memberId: number, newPassword: string) =>
    api.post<any, { message: string }>('/auth/reset-password', { member_id: memberId, new_password: newPassword }),
}
