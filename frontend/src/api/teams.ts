import client from './client';

export interface TeamResponse {
  id: number;
  name: string;
  school?: string;
  research_area?: string;
  description?: string;
  meeting_time?: string;
  is_active: boolean;
  owner_id: number;
  member_count: number;
  created_at: string;
}

export interface TeamListItem {
  id: number;
  name: string;
  role: string;
}

export async function createTeam(data: { name: string; school?: string; research_area?: string; description?: string }): Promise<TeamResponse> {
  const res = await client.post('/teams', data);
  return res.data;
}

export async function listMyTeams(): Promise<TeamListItem[]> {
  const res = await client.get('/teams');
  return res.data;
}

export async function getTeam(teamId: number): Promise<TeamResponse> {
  const res = await client.get(`/teams/${teamId}`);
  return res.data;
}
