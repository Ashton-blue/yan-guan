import api from './client'

// ---------- 文件管理（P0 批次 B · 模块3） ----------
// 注意：client.ts 的 axios 实例不解包 response.data，
// 与 teams.ts / meetings.ts 保持一致，调用方通过 r.data 取业务体。

export interface Folder {
  id: number
  team_id: number
  parent_id: number | null
  name: string
  visibility: string
  created_by: number | null
  created_at: string
}

export interface FileItem {
  id: number
  team_id: number
  folder_id: number | null
  name: string
  original_name: string
  mime_type: string | null
  size: number
  storage_path: string
  visibility: string
  version: number
  uploaded_by: number | null
  uploaded_by_name: string | null
  created_at: string
  updated_at: string
}

export interface FileListResponse {
  items: FileItem[]
  total: number
  page: number
  page_size: number
}

export interface FileUpdatePayload {
  name?: string
  folder_id?: number | null
  visibility?: string
}

export const filesApi = {
  listFolders: (teamId: number, parentId?: number | null) =>
    api.get<any, { data: Folder[] }>('/folders', {
      params: { team_id: teamId, parent_id: parentId ?? undefined },
    }),

  createFolder: (teamId: number, data: { name: string; parent_id?: number | null; visibility?: string }) =>
    api.post<any, { data: Folder }>('/folders', data, { params: { team_id: teamId } }),

  deleteFolder: (teamId: number, folderId: number) =>
    api.delete<any, { data: { message: string } }>(`/folders/${folderId}`, { params: { team_id: teamId } }),

  listFiles: (teamId: number, params: { folder_id?: number | null; page?: number; page_size?: number }) =>
    api.get<any, { data: FileListResponse }>('/files', {
      params: { team_id: teamId, ...params },
    }),

  uploadFile: (teamId: number, file: File, folderId?: number | null, visibility?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    const params: Record<string, any> = { team_id: teamId, visibility: visibility || 'team' }
    if (folderId != null) params.folder_id = folderId
    return api.post<any, { data: { id: number; name: string; version: number; message: string } }>(
      '/files/upload',
      formData,
      { params, headers: { 'Content-Type': 'multipart/form-data' } },
    )
  },

  downloadFileUrl: (teamId: number, fileId: number) => {
    const token = localStorage.getItem('access_token')
    const base = (import.meta.env.VITE_API_URL as string) || '/api/v1'
    return `${base}/files/${fileId}/download?team_id=${teamId}&token=${token}`
  },

  updateFile: (teamId: number, fileId: number, data: FileUpdatePayload) =>
    api.patch<any, { data: { message: string; id: number } }>(`/files/${fileId}`, data, { params: { team_id: teamId } }),

  deleteFile: (teamId: number, fileId: number) =>
    api.delete<any, { data: { message: string } }>(`/files/${fileId}`, { params: { team_id: teamId } }),
}
