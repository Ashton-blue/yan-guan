import api from './client'

// ---------- 组会管理（P0 批次 A · 模块2） ----------

export type MeetingType = 'journal' | 'progress' | 'defense'

export const MEETING_TYPE_LABELS: Record<MeetingType, string> = {
  journal: '文献报告',
  progress: '进展汇报',
  defense: '答辩预演',
}

export const MEETING_STATUS_LABELS: Record<string, string> = {
  upcoming: '未开始',
  finished: '已结束',
  cancelled: '已取消',
}

export interface AgendaItem {
  id: number
  seq: number
  time_slot: string | null
  content: string
  presenter_id: number | null
  presenter_name: string | null
}

export interface MeetingAction {
  id: number
  content: string
  owner_id: number | null
  owner_name: string | null
  due_date: string | null
  status: string
  completed_at: string | null
}

export interface Meeting {
  id: number
  team_id: number
  title: string
  meeting_type: MeetingType
  start_at: string
  end_at: string | null
  location: string | null
  presenter_id: number | null
  presenter_name: string | null
  description: string | null
  status: string
  created_at: string
}

export interface MeetingDetail extends Meeting {
  agenda: AgendaItem[]
  actions: MeetingAction[]
}

export interface MeetingCreateInput {
  title: string
  meeting_type: MeetingType
  start_at: string
  end_at?: string
  location?: string
  presenter_id?: number
  description?: string
  status?: string
}

export interface MeetingUpdateInput {
  title?: string
  meeting_type?: MeetingType
  start_at?: string
  end_at?: string
  location?: string
  presenter_id?: number
  description?: string
  status?: string
}

export interface AgendaItemInput {
  seq?: number
  time_slot?: string
  content: string
  presenter_id?: number
}

export interface ActionInput {
  content: string
  owner_id?: number
  due_date?: string
}

export interface ActionUpdateInput {
  content?: string
  owner_id?: number
  due_date?: string
  status?: 'open' | 'done' | 'cancelled'
  completed_at?: string
}

export const meetingsApi = {
  list: (teamId: number, type?: MeetingType) =>
    api.get<any, { data: Meeting[] }>(`/meetings`, {
      params: type ? { team_id: teamId, type } : { team_id: teamId },
    }),
  detail: (teamId: number, id: number) =>
    api.get<any, { data: MeetingDetail }>(`/meetings/${id}`, { params: { team_id: teamId } }),
  create: (teamId: number, data: MeetingCreateInput) =>
    api.post<any, { data: MeetingDetail }>(`/meetings`, data, { params: { team_id: teamId } }),
  update: (teamId: number, id: number, data: MeetingUpdateInput) =>
    api.put<any, { data: MeetingDetail }>(`/meetings/${id}`, data, { params: { team_id: teamId } }),
  remove: (teamId: number, id: number) =>
    api.delete<any, { message: string }>(`/meetings/${id}`, { params: { team_id: teamId } }),

  addAgenda: (teamId: number, id: number, data: AgendaItemInput) =>
    api.post<any, { data: AgendaItem }>(`/meetings/${id}/agenda`, data, { params: { team_id: teamId } }),
  deleteAgenda: (teamId: number, id: number, itemId: number) =>
    api.delete<any, { message: string }>(`/meetings/${id}/agenda/${itemId}`, { params: { team_id: teamId } }),

  addAction: (teamId: number, id: number, data: ActionInput) =>
    api.post<any, { data: MeetingAction }>(`/meetings/${id}/actions`, data, { params: { team_id: teamId } }),
  updateAction: (teamId: number, id: number, actionId: number, data: ActionUpdateInput) =>
    api.patch<any, { data: MeetingAction }>(`/meetings/${id}/actions/${actionId}`, data, { params: { team_id: teamId } }),
}
