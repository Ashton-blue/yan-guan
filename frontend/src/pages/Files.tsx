import React, { useCallback, useEffect, useRef, useState } from 'react'
import { teamApi, Team } from '../api/teams'
import {
  Folder, FileItem,
  filesApi,
} from '../api/files'

const MANAGER_ROLES = ['owner', 'supervisor', 'co_manager']
const VIS_LABELS: Record<string, string> = { team: '团队', teacher_only: '仅导师', private: '仅本人' }
const VIS_COLORS: Record<string, string> = {
  team: 'bg-blue-50 text-blue-700',
  teacher_only: 'bg-amber-50 text-amber-700',
  private: 'bg-slate-100 text-slate-600',
}

const fmtSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
const fmt = (iso: string | null) => {
  if (!iso) return ''
  const d = new Date(iso)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

const Files: React.FC = () => {
  const [team, setTeam] = useState<Team | null>(null)
  const [forbidden, setForbidden] = useState(false)
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState('')

  // 文件夹状态
  const [currentFolder, setCurrentFolder] = useState<number | null>(null)
  const [breadcrumb, setBreadcrumb] = useState<{ id: number | null; name: string }[]>([{ id: null, name: '全部文件' }])
  const [rootFolders, setRootFolders] = useState<Folder[]>([])
  const [subFolders, setSubFolders] = useState<Folder[]>([])
  const [showCreateFolder, setShowCreateFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [newFolderVis, setNewFolderVis] = useState('team')

  // 文件列表
  const [files, setFiles] = useState<FileItem[]>([])
  const [view, setView] = useState<'grid' | 'list'>('grid')

  // 预览
  const [preview, setPreview] = useState<FileItem | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  // 上传
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadVis, setUploadVis] = useState('team')

  // 编辑
  const [editTarget, setEditTarget] = useState<FileItem | null>(null)
  const [editName, setEditName] = useState('')
  const [editVis, setEditVis] = useState('team')

  const teamId = team?.id
  const canManage = MANAGER_ROLES.includes(team?.role || '')

  const flash = (t: string) => { setMsg(t); setTimeout(() => setMsg(''), 3000) }

  const loadFolders = useCallback(async (tid: number | undefined, parentId: number | null) => {
    if (!tid) return
    try {
      const r = await filesApi.listFolders(tid, parentId ?? undefined)
      const list = r?.data || []
      if (parentId === null) setRootFolders(list)
      else setSubFolders(list)
    } catch (e: any) {
      if (e?.response?.status === 403) setForbidden(true)
      else console.error(e)
    }
  }, [])

  const loadFiles = useCallback(async (tid: number | undefined, folderId: number | null) => {
    if (!tid) return
    try {
      const r = await filesApi.listFiles(tid, { folder_id: folderId ?? undefined })
      setFiles(r?.data?.items || [])
    } catch (e: any) {
      if (e?.response?.status === 403) setForbidden(true)
      else console.error(e)
    }
  }, [])

  useEffect(() => {
    const run = async () => {
      try {
        const teamsRes = await teamApi.listTeams()
        const teams = teamsRes.data || []
        const lab = teams.find((t) => t.name.includes('研究室')) || teams[0] || null
        setTeam(lab)
        if (lab) {
          // P3 修复：初始加载显式传 lab.id（此时 teamId 因 stale closure 仍为 undefined）
          await loadFolders(lab.id, null)
          await loadFiles(lab.id, null)
        }
      } catch (e: any) {
        if (e?.response?.status === 403) setForbidden(true)
      } finally {
        setLoading(false)
      }
    }
    run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 面包屑
  const openFolder = (id: number | null, name: string) => {
    if (id === null) {
      setCurrentFolder(null)
      setBreadcrumb([{ id: null, name: '全部文件' }])
      loadFolders(teamId, null)
      loadFiles(teamId, null)
      setSubFolders([])
    } else {
      // 构建面包屑路径：简化为 根 > 当前
      const crumb = breadcrumb.length > 1 ? [...breadcrumb.slice(0, -1), { id, name }] : [{ id: null, name: '全部文件' }, { id, name }]
      setCurrentFolder(id)
      setBreadcrumb(crumb)
      loadFolders(teamId, id)
      loadFiles(teamId, id)
    }
  }

  const doUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f || !teamId) return
    setUploading(true)
    try {
      const r = await filesApi.uploadFile(teamId, f, currentFolder, uploadVis)
      flash(`上传成功：${r.data.name} (v${r.data.version})`)
      await loadFiles(teamId, currentFolder)
    } catch (err: any) {
      flash(err?.response?.data?.detail || '上传失败')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const openPreview = async (f: FileItem) => {
    setPreview(f)
    setPreviewUrl(null)
    if (!teamId) return
    const url = filesApi.downloadFileUrl(teamId, f.id)
    setPreviewUrl(url)
  }

  const closePreview = () => { setPreview(null); setPreviewUrl(null) }

  const isPreviewable = (mime: string | null) => mime?.startsWith('image/') || mime === 'application/pdf'

  const doDeleteFile = async (id: number) => {
    if (!teamId) return
    if (!confirm('确认删除该文件？')) return
    try {
      await filesApi.deleteFile(teamId, id)
      flash('文件已删除')
      await loadFiles(teamId, currentFolder)
    } catch (e: any) {
      flash(e?.response?.data?.detail || '删除失败')
    }
  }

  const openEdit = (f: FileItem) => {
    setEditTarget(f)
    setEditName(f.name)
    setEditVis(f.visibility)
  }

  const saveEdit = async () => {
    if (!teamId || !editTarget) return
    try {
      await filesApi.updateFile(teamId, editTarget.id, { name: editName.trim() || undefined, visibility: editVis })
      flash('文件已更新')
      setEditTarget(null)
      await loadFiles(teamId, currentFolder)
    } catch (e: any) {
      flash(e?.response?.data?.detail || '更新失败')
    }
  }

  const doCreateFolder = async () => {
    if (!teamId || !newFolderName.trim()) { flash('请输入文件夹名称'); return }
    try {
      await filesApi.createFolder(teamId, { name: newFolderName.trim(), parent_id: currentFolder, visibility: newFolderVis })
      flash('文件夹已创建')
      setShowCreateFolder(false)
      setNewFolderName('')
      await loadFolders(teamId, currentFolder)
    } catch (e: any) {
      flash(e?.response?.data?.detail || '创建失败')
    }
  }

  const doDeleteFolder = async (id: number, name: string) => {
    if (!teamId) return
    if (!confirm(`确认删除文件夹「${name}」？（仅空文件夹可删除）`)) return
    try {
      await filesApi.deleteFolder(teamId, id)
      flash('文件夹已删除')
      await loadFolders(teamId, currentFolder)
    } catch (e: any) {
      flash(e?.response?.data?.detail || '删除失败')
    }
  }

  if (loading) return <div className="p-6 text-sm text-slate-400">加载中…</div>
  if (forbidden) return (
    <div className="p-6">
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-amber-800 text-sm">
        ⚠️ 您没有访问该团队的权限，请联系团队管理员。
      </div>
    </div>
  )

  const currentFolders = currentFolder === null ? rootFolders : subFolders

  return (
    <div className="space-y-4">
      {/* 页头 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold text-brand-ink">文件管理</h1>
        <div className="flex items-center gap-2 flex-wrap">
          {/* 视图切换 */}
          <div className="flex rounded-lg overflow-hidden border border-brand-line text-xs z-10 relative">
            <button
              onClick={() => setView('grid')}
              className={`px-3 py-1.5 ${view === 'grid' ? 'bg-blue-50 text-blue-700 font-medium' : 'bg-white text-slate-500'}`}
            >
              网格
            </button>
            <button
              onClick={() => setView('list')}
              className={`px-3 py-1.5 ${view === 'list' ? 'bg-blue-50 text-blue-700 font-medium' : 'bg-white text-slate-500'}`}
            >
              列表
            </button>
          </div>
          {/* 上传按钮 */}
          {canManage && (
            <div className="relative">
              <input ref={fileInputRef} type="file" className="hidden" onChange={doUpload} />
              <select
                value={uploadVis}
                onChange={(e) => setUploadVis(e.target.value)}
                className="absolute right-full mr-1 top-0 h-full w-24 text-xs border border-brand-line rounded-lg pr-2 bg-white"
              >
                <option value="team">团队可见</option>
                <option value="teacher_only">仅导师</option>
                <option value="private">仅本人</option>
              </select>
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="bg-blue-600 text-white text-sm px-4 py-2 rounded-xl hover:bg-blue-700 transition disabled:opacity-50"
              >
                {uploading ? '上传中…' : '⬆ 上传文件'}
              </button>
            </div>
          )}
          {/* 新建文件夹 */}
          {canManage && (
            <button
              onClick={() => setShowCreateFolder(true)}
              className="bg-white border border-brand-line text-sm px-4 py-2 rounded-xl hover:bg-slate-50 transition"
            >
              + 新建文件夹
            </button>
          )}
        </div>
      </div>

      {/* 面包屑 */}
      <nav className="flex items-center gap-1 text-sm text-slate-500 flex-wrap">
        {breadcrumb.map((b, i) => (
          <React.Fragment key={i}>
            {i > 0 && <span>/</span>}
            <button
              onClick={() => openFolder(b.id, b.name)}
              className={`hover:text-blue-600 ${i === breadcrumb.length - 1 ? 'font-medium text-brand-ink' : ''}`}
            >
              {b.name}
            </button>
          </React.Fragment>
        ))}
      </nav>

      {/* 消息提示 */}
      {msg && <div className="bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 text-xs text-blue-700">{msg}</div>}

      {/* 子文件夹网格 */}
      {currentFolders.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
          {currentFolders.map((f) => (
            <div key={f.id} className="relative group">
              <button
                onClick={() => openFolder(f.id, f.name)}
                className="w-full p-3 rounded-xl border border-brand-line bg-white hover:border-blue-300 hover:bg-blue-50/30 transition text-left"
              >
                <span className="text-xl">📁</span>
                <p className="mt-1 text-sm font-medium text-brand-ink truncate">{f.name}</p>
                <span className={`inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded ${VIS_COLORS[f.visibility] || VIS_COLORS.team}`}>
                  {VIS_LABELS[f.visibility] || f.visibility}
                </span>
              </button>
              {canManage && (
                <button
                  onClick={() => doDeleteFolder(f.id, f.name)}
                  className="absolute top-1 right-1 text-slate-300 hover:text-red-500 text-xs opacity-0 group-hover:opacity-100 transition"
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 文件网格 */}
      {view === 'grid' ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
          {files.map((f) => (
            <div key={f.id} className="relative group">
              <button
                onClick={() => openPreview(f)}
                className="w-full p-3 rounded-xl border border-brand-line bg-white hover:border-blue-300 hover:bg-blue-50/30 transition text-left"
              >
                <span className="text-xl">
                  {f.mime_type?.startsWith('image/') ? '🖼️' :
                   f.mime_type === 'application/pdf' ? '📄' :
                   f.mime_type?.startsWith('video/') ? '🎬' :
                   f.mime_type?.startsWith('audio/') ? '🎵' : '📎'}
                </span>
                <p className="mt-1 text-sm font-medium text-brand-ink truncate">{f.name}</p>
                <p className="text-[10px] text-slate-400">{fmtSize(f.size)} · v{f.version} · {fmt(f.created_at).slice(0, 10)}</p>
                <span className={`inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded ${VIS_COLORS[f.visibility] || VIS_COLORS.team}`}>
                  {VIS_LABELS[f.visibility] || f.visibility}
                </span>
              </button>
              {canManage && (
                <div className="absolute top-1 right-1 flex gap-1 opacity-0 group-hover:opacity-100 transition">
                  <button onClick={() => openEdit(f)} className="text-slate-300 hover:text-blue-500 text-xs" title="编辑">✎</button>
                  <button onClick={() => doDeleteFile(f.id)} className="text-slate-300 hover:text-red-500 text-xs" title="删除">✕</button>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-brand-line overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500">
              <tr>
                <th className="px-3 py-2 text-left">名称</th>
                <th className="px-3 py-2 text-left hidden sm:table-cell">大小</th>
                <th className="px-3 py-2 text-left hidden md:table-cell">版本</th>
                <th className="px-3 py-2 text-left">可见性</th>
                <th className="px-3 py-2 text-left hidden sm:table-cell">上传者</th>
                <th className="px-3 py-2 text-left hidden md:table-cell">时间</th>
                {canManage && <th className="px-3 py-2 w-16"></th>}
              </tr>
            </thead>
            <tbody>
              {files.map((f) => (
                <tr key={f.id} className="border-t border-brand-line hover:bg-slate-50/50">
                  <td className="px-3 py-2">
                    <button onClick={() => openPreview(f)} className="text-blue-600 hover:underline truncate max-w-40 block md:max-w-60">
                      {f.name}
                    </button>
                  </td>
                  <td className="px-3 py-2 text-slate-500 hidden sm:table-cell">{fmtSize(f.size)}</td>
                  <td className="px-3 py-2 text-slate-500 hidden md:table-cell">v{f.version}</td>
                  <td className="px-3 py-2">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${VIS_COLORS[f.visibility] || VIS_COLORS.team}`}>
                      {VIS_LABELS[f.visibility] || f.visibility}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-slate-500 hidden sm:table-cell">{f.uploaded_by_name || '-'}</td>
                  <td className="px-3 py-2 text-slate-400 hidden md:table-cell">{fmt(f.created_at)}</td>
                  {canManage && (
                    <td className="px-3 py-2 text-right">
                      <button onClick={() => openEdit(f)} className="text-slate-400 hover:text-blue-500 mr-2 text-xs">✎</button>
                      <button onClick={() => doDeleteFile(f.id)} className="text-slate-400 hover:text-red-500 text-xs">✕</button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          {files.length === 0 && <p className="text-center py-6 text-sm text-slate-400">暂无文件</p>}
        </div>
      )}

      {files.length === 0 && currentFolders.length === 0 && view === 'grid' && (
        <p className="text-center py-8 text-sm text-slate-400">当前目录为空，可以上传文件或新建文件夹</p>
      )}

      {/* 新建文件夹弹窗 */}
      {showCreateFolder && (
        <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-5 w-full max-w-sm shadow-xl">
            <h3 className="text-sm font-bold text-brand-ink mb-3">新建文件夹</h3>
            <input
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              placeholder="文件夹名称"
              className="w-full border border-brand-line rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
            <select
              value={newFolderVis}
              onChange={(e) => setNewFolderVis(e.target.value)}
              className="w-full border border-brand-line rounded-lg px-3 py-2 text-sm mb-4 bg-white"
            >
              <option value="team">团队可见</option>
              <option value="teacher_only">仅导师</option>
              <option value="private">仅本人</option>
            </select>
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowCreateFolder(false)} className="text-sm text-slate-500 px-3 py-1.5">取消</button>
              <button onClick={doCreateFolder} className="text-sm text-white bg-blue-600 px-4 py-1.5 rounded-lg">创建</button>
            </div>
          </div>
        </div>
      )}

      {/* 预览弹窗 */}
      {preview && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={closePreview}>
          <div className="bg-white rounded-xl p-4 w-full max-w-2xl max-h-[80vh] overflow-auto shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-brand-ink truncate flex-1">{preview.name}</h3>
              <div className="flex items-center gap-2">
                {previewUrl && (
                  <a
                    href={previewUrl}
                    download={preview.name}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-blue-600 hover:underline"
                  >
                    下载
                  </a>
                )}
                <button onClick={closePreview} className="text-slate-400 hover:text-slate-600 text-lg">✕</button>
              </div>
            </div>
            <div className="text-xs text-slate-500 mb-2 space-y-0.5">
              <p>大小：{fmtSize(preview.size)} · 版本：v{preview.version} · 可见性：{VIS_LABELS[preview.visibility] || preview.visibility}</p>
              <p>上传者：{preview.uploaded_by_name || '-'} · 时间：{fmt(preview.created_at)}</p>
            </div>
            {previewUrl && isPreviewable(preview.mime_type) ? (
              preview.mime_type?.startsWith('image/') ? (
                <img src={previewUrl} alt={preview.name} className="max-h-[50vh] mx-auto rounded-lg" />
              ) : (
                <iframe src={previewUrl} className="w-full h-[50vh] rounded-lg border border-brand-line" title={preview.name} />
              )
            ) : (
              <div className="p-8 text-center text-slate-400 text-sm">
                该文件类型不支持在线预览，
                {previewUrl && <a href={previewUrl} download={preview.name} className="text-blue-600 hover:underline ml-1">点击下载</a>}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 编辑弹窗 */}
      {editTarget && (
        <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-5 w-full max-w-sm shadow-xl">
            <h3 className="text-sm font-bold text-brand-ink mb-3">编辑文件</h3>
            <label className="text-xs text-slate-500 block mb-1">名称</label>
            <input
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="w-full border border-brand-line rounded-lg px-3 py-2 text-sm mb-3"
            />
            <label className="text-xs text-slate-500 block mb-1">可见性</label>
            <select
              value={editVis}
              onChange={(e) => setEditVis(e.target.value)}
              className="w-full border border-brand-line rounded-lg px-3 py-2 text-sm mb-4 bg-white"
            >
              <option value="team">团队可见</option>
              <option value="teacher_only">仅导师</option>
              <option value="private">仅本人</option>
            </select>
            <div className="flex justify-end gap-2">
              <button onClick={() => setEditTarget(null)} className="text-sm text-slate-500 px-3 py-1.5">取消</button>
              <button onClick={saveEdit} className="text-sm text-white bg-blue-600 px-4 py-1.5 rounded-lg">保存</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Files
