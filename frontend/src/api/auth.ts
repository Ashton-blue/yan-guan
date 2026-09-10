import api from './client'

export interface User {
  id: number
  email: string
  name: string
  avatar_url?: string | null
  research_area?: string | null
  bio?: string | null
  status?: string
  must_change_password: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export const authApi = {
  // 注册
  register: (data: { email: string; password: string; name: string }) =>
    api.post<any, { data: { message: string; user: User } }>('/auth/register', data),

  // 登录
  login: (data: { email: string; password: string }) =>
    api.post<any, { data: TokenResponse }>('/auth/login', data),

  // 获取当前用户信息
  getMe: () =>
    api.get<any, { data: User }>('/auth/me'),

  // 修改密码
  changePassword: (data: { old_password: string; new_password: string }) =>
    api.post('/auth/change-password', data),

  // 刷新token
  refreshToken: (refresh_token: string) =>
    api.post<any, { data: { access_token: string } }>('/auth/refresh', null, {
      params: { refresh_token }
    }),
}
