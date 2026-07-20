import client from './client';

export interface UserInfo {
  id: number;
  username: string;
  display_name: string;
  email?: string;
  phone?: string;
  avatar_url?: string;
  is_system_admin: boolean;
  must_change_password: boolean;
}

export interface AuthMeResponse {
  user: UserInfo;
  teams: { id: number; name: string; role: string }[];
}

export async function login(username: string, password: string) {
  const res = await client.post('/auth/login', { username, password });
  return res.data;
}

export async function register(data: { username: string; password: string; display_name: string; email?: string }) {
  const res = await client.post('/auth/register', data);
  return res.data;
}

export async function getMe(): Promise<AuthMeResponse> {
  const res = await client.get('/auth/me');
  return res.data;
}

export async function changePassword(old_password: string, new_password: string) {
  const res = await client.post('/auth/change-password', { old_password, new_password });
  return res.data;
}
