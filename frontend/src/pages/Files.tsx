import React, { useCallback, useEffect, useRef, useState } from 'react'
import { teamApi, Team } from '../api/teams'
import {
  Folder, FileItem, FolderSearchItem,
  filesApi, FileTypeFilter, FileSortBy,
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

  // 搜索
  const [searchMode, setSearchMode] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchType, setSearchType] = useState<FileTypeFilter>('all')
  const [searchSort, setSearchSort] = useState<FileSortBy>('newest')
  const [searchRecursive, setSearchRecursive] = useState(true)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchFileResults, setSearchFileResults] = useState<FileItem[]>([])
  const [searchFolderResults, setSearchFolderResults] = useState<FolderSearchItem[]>([])
  const [searchTotal, setSearchTotal] = useState(0)
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

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

  // 搜索
  const doSearch = useCallback(async (tid: number | undefined, q: string, type: FileTypeFilter, sort: FileSortBy, recursive: boolean, folderId: number | null) => {
    if (!tid) return
    setSearchLoading(true)
    try {
      const r = await filesApi.search(tid, {
        q,
        file_type: type,
        sort_by: sort,
        recursive,
        folder_id: folderId ?? undefined,
        page: 1,
        page_size: 50,
      })
      setSearchFileResults(r?.data?.files?.items || [])
      setSearchFolderResults(r?.data?.folders?.items || [])
      setSearchTotal(r?.data?.files?.total || 0)
    } catch (e: any) {
      if (e?.response?.status === 403) setForbidden(true)
      else console.error(e)
    } finally {
      setSearchLoading(false)
    }
  }, [])

  const triggerSearch = useCallback((q: string) => {
    if (!teamId) return
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    if (q.trim() === '' && searchType === 'all') {
      // 空关键词 + 全类型 = 退出搜索
      setSearchMode(false)
      setSearchFileResults([])
      setSearchFolderResults([])
      return
    }
    setSearchMode(true)
    searchTimerRef.current = setTimeout(() => {
      doSearch(teamId, q, searchType, searchSort, searchRecursive, currentFolder)
    }, 300)
  }, [teamId, searchType, searchSort, searchRecursive, currentFolder, doSearch])

  // 搜索参数变化时重新搜
  useEffect(() => {
    if (!searchMode || !teamId) return
    doSearch(teamId, searchQuery, searchType, searchSort, searchRecursive, currentFolder)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchType, searchSort, searchRecursive])

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
    // 退出搜索模式
    setSearchMode(false)
    setSearchQuery('')
    setSearchFileResults([])
    setSearchFolderResults([])
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

  const jumpToFolderFromSearch = (folderId: number, folderName: string, parentPath: string | null | undefined) => {
    // 从搜索结果跳到文件夹：先加载完整路径（简化：直接进入该文件夹，面包屑只显示根+该文件夹）
    setSearchMode(false)
    setSearchQuery('')
    setSearchFileResults([])
    setSearchFolderResults([])
    setCurrentFolder(folderId)
    // 面包屑使用 folder_path
    const pathParts = parentPath ? parentPath.split('/') : []
    const crumb: { id: number | null; name: string }[] = [{ id: null, name: '全部文件' }]
    // 中间层级暂时只显示文字（不挂 id），最后一级挂真实 id
    for (let i = 0; i < pathParts.length; i++) {
      crumb.push({ id: null, name: pathParts[i] })
    }
    crumb.push({ id: folderId, name: folderName })
    setBreadcrumb(crumb)
    loadFolders(teamId, folderId)
    loadFiles(teamId, folderId)
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
  const displayFiles = searchMode ? searchFileResults : files
  const displayFolders = searchMode ? searchFolderResults : currentFolders

  return (
    <div className="space-y-4">
      {/* 页头 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold text-brand-ink">文件管理</h1>
        <div className="flex items-center gap-2 flex-wrap">
          {/* 搜索框 */}
          <div className="relative">
            <input
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); triggerSearch(e.target.value) }}
              placeholder="🔍 搜索文件 / 文件夹…"
              className="w-56 sm:w-64 md:w-72 h-9 text-sm border border-brand-line rounded-xl pl-3 pr-3 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
            {searchMode && (
              <button
                onClick={() => { setSearchQuery(''); setSearchMode(false); setSearchFileResults([]); setSearchFolderResults([]) }}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-sm"
                title="清除搜索"
              >
                ✕
              </button>
            )}
          </div>
          {/* 类型筛选 */}
          <select
            value={searchType}
            onChange={(e) => {
              const t = e.target.value as FileTypeFilter
              setSearchType(t)
              if (searchMode || t !== 'all' || searchQuery) {
                setSearchMode(true)
                triggerSearch(searchQuery)
              }
            }}
            aria-label="文件类型"
            className="h-9 text-xs border border-brand-line rounded-xl pr-2 pl-2 bg-white"
          >
            <option value="all">全部类型</option>
            <option value="document">文档</option>
            <option value="image">图片</option>
            <option value="video">视频</option>
            <option value="audio">音频</option>
            <option value="archive">压缩包</option>
            <option value="other">其他</option>
          </select>
          {/* 排序 */}
          <select
            value={searchSort}
            onChange={(e) => {
              const s = e.target.value as FileSortBy
              setSearchSort(s)
              if (searchMode) triggerSearch(searchQuery)
            }}
            aria-label="排序方式"
            className="h-9 text-xs border border-brand-line rounded-xl pr-2 pl-2 bg-white"
          >
            <option value="newest">最新上传</option>
            <option value="oldest">最早上传</option>
            <option value="name">按名称</option>
          </select>
          {/* 视图切换（非搜索模式才显示） */}
          {!searchMode && (
            <div className="flex rounded-lg overflow-hidden border border-brand-line text-xs">
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
          )}
          {/* 上传按钮 + 可见性选择 */}
          {canManage && (
            <div className="flex items-center gap-1">
              <select
                value={uploadVis}
                onChange={(e) => setUploadVis(e.target.value)}
                aria-label="上传可见性"
                className="h-9 text-xs border border-brand-line rounded-lg pr-2 pl-2 bg-white"
              >
                <option value="team">团队可见</option>
                <option value="teacher_only">仅导师</option>
                <option value="private">仅本人</option>
              </select>
              <input ref={fileInputRef} type="file" className="hidden" onChange={doUpload} />
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

      {/* 搜索模式：递归范围切换 + 结果统计 */}
      {searchMode && (
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={searchRecursive}
                onChange={(e) => setSearchRecursive(e.target.checked)}
                className="accent-blue-600"
              />
              包含子目录
            </label>
            <span className="text-slate-300">|</span>
            <span>
              找到 <span className="font-medium text-brand-ink">{searchTotal}</span> 个文件
              {searchFolderResults.length > 0 && `、${searchFolderResults.length} 个文件夹`}
            </span>
          </div>
          {searchLoading && <span>搜索中…</span>}
        </div>
      )}

      {/* 面包屑（搜索模式隐藏） */}
      {!searchMode && (
        <nav className="flex items-center gap-1 text-sm text-slate-500 flex-wrap">
          {breadcrumb.map((b, i) => (
            <React.Fragment key={i}>
              {i > 0 && <span>/</span>}
              <button
                onClick={() => b.id !== null ? openFolder(b.id, b.name) : openFolder(null, '全部文件')}
                className={`hover:text-blue-600 ${i === breadcrumb.length - 1 ? 'font-medium text-brand-ink' : ''}`}
              >
                {b.name}
              </button>
            </React.Fragment>
          ))}
        </nav>
      )}

      {/* 消息提示 */}
      {msg && <div className="bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 text-xs text-blue-700">{msg}</div>}

      {/* 子文件夹网格（搜索模式也显示匹配的文件夹） */}
      {displayFolders.length > 0 && (
        <div className="space-y-2">
          {searchMode && <p className="text-xs font-medium text-slate-500">匹配的文件夹</p>}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
            {displayFolders.map((f) => (
              <div key={f.id} className="relative group">
                <button
                  onClick={() => searchMode
                    ? jumpToFolderFromSearch(f.id, f.name, (f as FolderSearchItem).folder_path)
                    : openFolder(f.id, f.name)
                  }
                  className="w-full p-3 rounded-xl border border-brand-line bg-white hover:border-blue-300 hover:bg-blue-50/30 transition text-left"
                >
                  <span className="text-xl">📁</span>
                  <p className="mt-1 text-sm font-medium text-brand-ink truncate">{f.name}</p>
                  {(f as FolderSearchItem).folder_path && searchMode && (
                    <p className="text-[10px] text-slate-400 truncate">{(f as FolderSearchItem).folder_path}</p>
                  )}
                  <span className={`inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded ${VIS_COLORS[f.visibility] || VIS_COLORS.team}`}>
                    {VIS_LABELS[f.visibility] || f.visibility}
                  </span>
                </button>
                {canManage && !searchMode && (
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
        </div>
      )}

      {/* 文件网格 / 列表 */}
      {searchMode || view === 'grid' ? (
        <div className="space-y-2">
          {searchMode && <p className="text-xs font-medium text-slate-500">匹配的文件</p>}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
            {displayFiles.map((f) => (
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
                  {f.folder_path && searchMode && (
                    <p className="text-[10px] text-slate-400 truncate">📁 {f.folder_path}</p>
                  )}
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
              {displayFiles.map((f) => (
                <tr key={f.id} className="border-t border-brand-line hover:bg-slate-50/50">
                  <td className="px-3 py-2">
                    <button onClick={() => openPreview(f)} className="text-blue-600 hover:underline truncate max-w-40 block md:max-w-60">
                      {f.name}
                    </button>
                    {f.folder_path && searchMode && (
                      <p className="text-[10px] text-slate-400 truncate">📁 {f.folder_path}</p>
                    )}
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
          {displayFiles.length === 0 && <p className="text-center py-6 text-sm text-slate-400">{searchMode ? '未找到匹配的文件' : '暂无文件'}</p>}
        </div>
      )}

      {displayFiles.length === 0 && displayFolders.length === 0 && !searchMode && view === 'grid' && (
        <p className="text-center py-8 text-sm text-slate-400">当前目录为空，可以上传文件或新建文件夹</p>
      )}
      {searchMode && displayFiles.length === 0 && displayFolders.length === 0 && !searchLoading && (
        <p className="text-center py-8 text-sm text-slate-400">未找到匹配「{searchQuery}」的结果</p>
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
