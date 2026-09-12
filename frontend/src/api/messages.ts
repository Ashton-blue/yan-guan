import api from './client'

// ---------- 讯息管理（P0 批次 B · 模块4） ----------
// 与 teams.ts / meetings.ts 保持一致：调用方通过 r.data 取业务体。

export interface Message {
  id: number
  team_id: number
  user_id: number
  sender_id: number | null
  sender_name: string | null
  msg_type: string
  title: string
  content: string | null
  reference_type: string | null
  reference_id: number | null
  is_read: boolean
  read_at: string | null
  created_at: string
}

export interface MessageListResponse {
  items: Message[]
  total: number
  page: number
  page_size: number
  unread_count: number
}

export type MessageTab = 'all' | 'notifications' | 'at_me'

export const messagesApi = {
  list: (teamId: number, tab: MessageTab = 'all', page = 1, pageSize = 20) =>
    api.get<any, { data: MessageListResponse }>('/messages', {
      params: { team_id: teamId, tab, page, page_size: pageSize },
    }),

  markRead: (teamId: number, msgId: number) =>
    api.put<any, { data: { message: string; total_unread: number } }>(`/messages/${msgId}/read`, null, {
      params: { team_id: teamId },
    }),

  markAllRead: (teamId: number) =>
    api.put<any, { data: { message: string; total_unread: number } }>('/messages/read-all', null, {
      params: { team_id: teamId },
    }),

  send: (
    teamId: number,
    data: { recipient_id: number; title: string; content?: string | null; msg_type?: string },
  ) =>
    api.post<any, { data: Message }>('/messages', data, { params: { team_id: teamId } }),
}
