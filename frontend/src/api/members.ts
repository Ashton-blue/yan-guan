import client from './client';

export interface MemberResponse {
  id: number;
  user_id: number;
  username: string;
  display_name: string;
  email?: string;
  role: string;
  joined_at: string;
}

export interface MemberAddResponse {
  member: MemberResponse;
  initial_password: string;
}

export async function listMembers(teamId: number): Promise<MemberResponse[]> {
  const res = await client.get(`/teams/${teamId}/members`);
  return res.data;
}

export async function addMember(teamId: number, data: { username: string; display_name: string; email?: string; role: string }): Promise<MemberAddResponse> {
  const res = await client.post(`/teams/${teamId}/members`, data);
  return res.data;
}

export async function removeMember(teamId: number, userId: number) {
  const res = await client.delete(`/teams/${teamId}/members/${userId}`);
  return res.data;
}

export async function resetPassword(teamId: number, userId: number): Promise<{ new_password: string }> {
  const res = await client.post(`/teams/${teamId}/members/${userId}/reset-password`);
  return res.data;
}
