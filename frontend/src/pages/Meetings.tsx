import React, { useEffect, useState } from 'react'
import { teamApi, Team } from '../api/teams'
import { accountApi, MemberRow } from '../api/account'
import {
  meetingsApi, Meeting, MeetingDetail, MeetingType,
  MEETING_TYPE_LABELS, MEETING_STATUS_LABELS,
} from '../api/meetings'

const MANAGER_ROLES = ['owner', 'supervisor', 'co_manager']
const TABS = [
  { key: 'overview', label: '概览' },
  { key: 'agenda', label: '议程' },
  { key: 'materials', label: '资料' },
  { key: 'actions', label: '行动项' },
] as const
type TabKey = (typeof TABS)[number]['key']

const fmt = (iso: string | null) => {
  if (!iso) return ''
  const d = new Date(iso)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

const Meetings: React.FC = () => {
  const [team, setTeam] = useState<Team | null>(null)
  const [members, setMembers] = useState<MemberRow[]>([])
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [filter, setFilter] = useState<'all' | MeetingType>('all')
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState('')
  const [forbidden, setForbidden] = useState(false)

  // 详情抽屉
  const [detail, setDetail] = useState<MeetingDetail | null>(null)
  const [tab, setTab] = useState<TabKey>('overview')

  // 新建弹窗
  const [showCreate, setShowCreate] = useState(false)
  const [cTitle, setCTitle] = useState('')
  const [cType, setCType] = useState<MeetingType>('journal')
  const [cDate, setCDate] = useState('')
  const [cTime, setCTime] = useState('')
  const [cEnd, setCEnd] = useState('')
  const [cLoc, setCLoc] = useState('')
  const [cPresenter, setCPresenter] = useState('')
  const [cDesc, setCDesc] = useState('')

  // 详情内新增表单
  const [agTime, setAgTime] = useState('')
  const [agContent, setAgContent] = useState('')
  const [actContent, setActContent] = useState('')
  const [actOwner, setActOwner] = useState('')
  const [actDue, setActDue] = useState('')

  const teamId = team?.id
  const canManage = MANAGER_ROLES.includes(team?.role || '')

  const flash = (t: string) => { setMsg(t); setTimeout(() => setMsg(''), 3000) }

  const loadMeetings = async (f: 'all' | MeetingType) => {
    if (!teamId) return
    try {
      const r = await meetingsApi.list(teamId, f === 'all' ? undefined : f)
      setMeetings(r.data || [])
    } catch (e: any) {
      if (e?.response?.status === 403) setForbidden(true)
      else console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const run = async () => {
      try {
        const teamsRes = await teamApi.listTeams()
        const teams = teamsRes.data || []
        const lab = teams.find((t) => t.name.includes('研究室')) || teams[0] || null
        setTeam(lab)
        if (lab) {
          const m = await accountApi.listMembers(lab.id)
          setMembers(m.data || [])
          await loadMeetings(filter)
        } else {
          setLoading(false)
        }
      } catch (e: any) {
        if (e?.response?.status === 403) setForbidden(true)
        else console.error(e)
        setLoading(false)
      }
    }
    run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const changeFilter = (f: 'all' | MeetingType) => {
    setFilter(f)
    loadMeetings(f)
  }

  const openDetail = async (id: number) => {
    if (!teamId) return
    try {
      const r = await meetingsApi.detail(teamId, id)
      setDetail(r.data)
      setTab('overview')
    } catch (e: any) {
      flash(e?.response?.data?.detail || '加载详情失败')
    }
  }

  const reloadDetail = async () => {
    if (!teamId || !detail) return
    const r = await meetingsApi.detail(teamId, detail.id)
    setDetail(r.data)
  }

  const submitCreate = async () => {
    if (!teamId || !cTitle.trim() || !cDate) { flash('请填写标题与日期'); return }
    const start_at = `${cDate}T${cTime || '09:00'}:00`
    const end_at = cEnd ? `${cDate}T${cEnd}:00` : undefined
    try {
      await meetingsApi.create(teamId, {
        title: cTitle.trim(),
        meeting_type: cType,
        start_at,
        end_at,
        location: cLoc.trim() || undefined,
        presenter_id: cPresenter ? Number(cPresenter) : undefined,
        description: cDesc.trim() || undefined,
      })
      flash('组会已创建')
      setShowCreate(false)
      setCTitle(''); setCDate(''); setCTime(''); setCEnd(''); setCLoc(''); setCPresenter(''); setCDesc('')
      loadMeetings(filter)
    } catch (e: any) {
      flash(e?.response?.data?.detail || '创建失败')
    }
  }

  const removeMeeting = async (id: number, title: string) => {
    if (!teamId || !window.confirm(`确认删除组会「${title}」？`)) return
    try {
      await meetingsApi.remove(teamId, id)
      flash('已删除')
      setDetail(null)
      loadMeetings(filter)
    } catch (e: any) {
      flash(e?.response?.data?.detail || '删除失败')
    }
  }

  const addAgenda = async () => {
    if (!teamId || !detail || !agContent.trim()) return
    try {
      await meetingsApi.addAgenda(teamId, detail.id, {
        time_slot: agTime.trim() || undefined,
        content: agContent.trim(),
      })
      setAgTime(''); setAgContent('')
      reloadDetail()
    } catch (e: any) { flash(e?.response?.data?.detail || '添加议程失败') }
  }

  const delAgenda = async (itemId: number) => {
    if (!teamId || !detail) return
    try {
      await meetingsApi.deleteAgenda(teamId, detail.id, itemId)
      reloadDetail()
    } catch (e: any) { flash(e?.response?.data?.detail || '删除失败') }
  }

  const addAction = async () => {
    if (!teamId || !detail || !actContent.trim()) return
    try {
      await meetingsApi.addAction(teamId, detail.id, {
        content: actContent.trim(),
        owner_id: actOwner ? Number(actOwner) : undefined,
        due_date: actDue || undefined,
      })
      setActContent(''); setActOwner(''); setActDue('')
      reloadDetail()
    } catch (e: any) { flash(e?.response?.data?.detail || '添加行动项失败') }
  }

  const toggleAction = async (actionId: number, status: 'done' | 'open') => {
    if (!teamId || !detail) return
    try {
      await meetingsApi.updateAction(teamId, detail.id, actionId, { status })
      reloadDetail()
    } catch (e: any) { flash(e?.response?.data?.detail || '更新失败') }
  }

  const memberName = (id: number | null) =>
    id ? members.find((m) => m.user_id === id)?.name || '' : ''

  const actionStats = detail
    ? { done: detail.actions.filter((a) => a.status === 'done').length, total: detail.actions.length }
    : { done: 0, total: 0 }

  return (
    <div className="max-w-6xl mx-auto fade-in">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div>
          <h1 className="text-xl font-bold text-brand-ink">📅 组会管理</h1>
          <p className="text-sm text-brand-muted mt-1">
            文献报告 / 进展汇报 / 答辩预演
            {team && <span className="ml-2 text-brand-primary">| {team.name}</span>}
          </p>
        </div>
        {canManage && !forbidden && (
          <button onClick={() => setShowCreate(true)} className="bg-brand-primary text-white text-sm px-4 py-2 rounded-lg hover:bg-brand-active transition">
            + 新建组会
          </button>
        )}
      </div>

      {forbidden && (
        <div className="mb-5 text-sm bg-amber-50 border border-amber-200 text-amber-800 rounded-lg px-4 py-3">
          ⚠️ 您没有访问该团队的权限。请联系团队管理员添加您为成员，或切换到您所属的团队。
        </div>
      )}

      {msg && <div className="mb-4 text-sm bg-brand-soft-blue text-brand-active border border-brand-line rounded-lg px-3 py-2">{msg}</div>}

      {/* 类型筛选 */}
      <div className="flex flex-wrap gap-2 mb-5">
        {(['all', 'journal', 'progress', 'defense'] as const).map((f) => (
          <button key={f} onClick={() => changeFilter(f)}
            className={`text-sm px-3 py-1.5 rounded-full border transition ${
              filter === f ? 'bg-brand-primary text-white border-brand-primary' : 'bg-white text-brand-ink border-brand-line hover:bg-brand-soft'
            }`}>
            {f === 'all' ? '全部' : MEETING_TYPE_LABELS[f as MeetingType]}
          </button>
        ))}
      </div>

      {/* 卡片列表 */}
      {loading ? (
        <p className="text-sm text-brand-muted">加载中…</p>
      ) : meetings.length === 0 ? (
        <div className="card p-10 text-center text-brand-muted text-sm">暂无组会。</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {meetings.map((m) => (
            <button key={m.id} onClick={() => openDetail(m.id)}
              className="card p-4 text-left hover:shadow-md hover:border-brand-primary transition">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs bg-brand-soft-blue text-brand-active px-2 py-0.5 rounded-full">
                  {MEETING_TYPE_LABELS[m.meeting_type] || m.meeting_type}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  m.status === 'upcoming' ? 'bg-brand-soft text-brand-ink' : 'bg-emerald-50 text-emerald-600'
                }`}>
                  {MEETING_STATUS_LABELS[m.status] || m.status}
                </span>
              </div>
              <h3 className="font-semibold text-brand-ink mb-1 leading-6">{m.title}</h3>
              <p className="text-xs text-brand-muted">{fmt(m.start_at)}{m.end_at ? ` – ${fmt(m.end_at)}` : ''}</p>
              <p className="text-xs text-brand-muted mt-1">
                {m.location ? `📍 ${m.location}` : '线上 / 地点待定'}
                {m.presenter_name ? ` · 主讲 ${m.presenter_name}` : ''}
              </p>
            </button>
          ))}
        </div>
      )}

      {/* 新建组会弹窗 */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40" onClick={() => setShowCreate(false)} />
          <div className="relative bg-white rounded-xl w-full max-w-lg shadow-xl fade-in p-5">
            <h3 className="font-bold text-brand-ink mb-4">新建组会</h3>
            <label className="block text-xs text-brand-muted mb-1">标题</label>
            <input value={cTitle} onChange={(e) => setCTitle(e.target.value)}
              placeholder="如：第19次文献报告会"
              className="w-full text-sm border border-brand-line rounded-lg px-3 py-2 mb-3 focus:outline-none focus:ring-1 focus:ring-brand-primary" />
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <label className="block text-xs text-brand-muted mb-1">类型</label>
                <select value={cType} onChange={(e) => setCType(e.target.value as MeetingType)}
                  className="w-full text-sm border border-brand-line rounded-lg px-2 py-2 bg-white">
                  <option value="journal">文献报告</option>
                  <option value="progress">进展汇报</option>
                  <option value="defense">答辩预演</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-brand-muted mb-1">主讲人</label>
                <select value={cPresenter} onChange={(e) => setCPresenter(e.target.value)}
                  className="w-full text-sm border border-brand-line rounded-lg px-2 py-2 bg-white">
                  <option value="">未指定</option>
                  {members.map((m) => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3 mb-3">
              <div>
                <label className="block text-xs text-brand-muted mb-1">开始日期</label>
                <input type="date" value={cDate} onChange={(e) => setCDate(e.target.value)}
                  className="w-full text-sm border border-brand-line rounded-lg px-2 py-2 bg-white" />
              </div>
              <div>
                <label className="block text-xs text-brand-muted mb-1">开始时间</label>
                <input type="time" value={cTime} onChange={(e) => setCTime(e.target.value)}
                  className="w-full text-sm border border-brand-line rounded-lg px-2 py-2 bg-white" />
              </div>
              <div>
                <label className="block text-xs text-brand-muted mb-1">结束时间</label>
                <input type="time" value={cEnd} onChange={(e) => setCEnd(e.target.value)}
                  className="w-full text-sm border border-brand-line rounded-lg px-2 py-2 bg-white" />
              </div>
            </div>
            <label className="block text-xs text-brand-muted mb-1">地点</label>
            <input value={cLoc} onChange={(e) => setCLoc(e.target.value)} placeholder="如：管理学院B302 / 线上"
              className="w-full text-sm border border-brand-line rounded-lg px-3 py-2 mb-3 focus:outline-none focus:ring-1 focus:ring-brand-primary" />
            <label className="block text-xs text-brand-muted mb-1">简介</label>
            <textarea value={cDesc} onChange={(e) => setCDesc(e.target.value)} rows={2}
              className="w-full text-sm border border-brand-line rounded-lg px-3 py-2 mb-4 resize-none focus:outline-none focus:ring-1 focus:ring-brand-primary" />
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowCreate(false)} className="text-sm text-brand-muted px-4 py-2 rounded-lg hover:bg-brand-soft">取消</button>
              <button onClick={submitCreate} className="bg-brand-primary text-white text-sm px-4 py-2 rounded-lg hover:bg-brand-active transition">创建</button>
            </div>
          </div>
        </div>
      )}

      {/* 详情抽屉 */}
      {detail && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/40" onClick={() => setDetail(null)} />
          <div className="relative bg-white w-full max-w-md h-full overflow-y-auto shadow-xl slide-in">
            <div className="sticky top-0 bg-white border-b border-brand-line p-4 z-10">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-xs bg-brand-soft-blue text-brand-active px-2 py-0.5 rounded-full">
                    {MEETING_TYPE_LABELS[detail.meeting_type]}
                  </span>
                  <h2 className="font-bold text-brand-ink mt-2">{detail.title}</h2>
                </div>
                <button onClick={() => setDetail(null)} className="text-brand-muted text-lg leading-none">✕</button>
              </div>
              <div className="flex gap-1 mt-3">
                {TABS.map((t) => (
                  <button key={t.key} onClick={() => setTab(t.key)}
                    className={`text-xs px-3 py-1.5 rounded-full transition ${
                      tab === t.key ? 'bg-brand-primary text-white' : 'bg-brand-soft text-brand-ink'
                    }`}>
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="p-4">
              {tab === 'overview' && (
                <div className="space-y-3 text-sm">
                  <Row label="状态">{MEETING_STATUS_LABELS[detail.status] || detail.status}</Row>
                  <Row label="时间">{fmt(detail.start_at)}{detail.end_at ? ` – ${fmt(detail.end_at)}` : ''}</Row>
                  <Row label="地点">{detail.location || '线上 / 待定'}</Row>
                  <Row label="主讲">{detail.presenter_name || memberName(detail.presenter_id) || '未指定'}</Row>
                  <Row label="进度">议程 {detail.agenda.length} 项 · 行动项 {actionStats.done}/{actionStats.total} 完成</Row>
                  {detail.description && <Row label="简介">{detail.description}</Row>}
                  {canManage && (
                    <button onClick={() => removeMeeting(detail.id, detail.title)}
                      className="text-xs text-brand-danger hover:underline">删除该组会</button>
                  )}
                </div>
              )}

              {tab === 'agenda' && (
                <div>
                  {detail.agenda.length === 0 ? (
                    <p className="text-sm text-brand-muted mb-3">暂无议程。</p>
                  ) : (
                    <ol className="space-y-2">
                      {detail.agenda.map((a) => (
                        <li key={a.id} className="flex items-start gap-2 text-sm border border-brand-line rounded-lg p-2.5">
                          <span className="text-xs text-brand-muted w-16 flex-shrink-0">{a.time_slot || `#${a.seq}`}</span>
                          <span className="flex-1 text-brand-ink">{a.content}{a.presenter_name ? <span className="text-brand-muted"> · {a.presenter_name}</span> : ''}</span>
                          {canManage && <button onClick={() => delAgenda(a.id)} className="text-xs text-brand-danger flex-shrink-0">删</button>}
                        </li>
                      ))}
                    </ol>
                  )}
                  {canManage && (
                    <div className="mt-3 space-y-2">
                      <div className="flex gap-2">
                        <input value={agTime} onChange={(e) => setAgTime(e.target.value)} placeholder="时间段"
                          className="w-24 text-xs border border-brand-line rounded-lg px-2 py-1.5" />
                        <input value={agContent} onChange={(e) => setAgContent(e.target.value)} placeholder="议程内容"
                          className="flex-1 text-xs border border-brand-line rounded-lg px-2 py-1.5" />
                      </div>
                      <button onClick={addAgenda} className="text-xs text-brand-primary hover:underline">+ 添加议程</button>
                    </div>
                  )}
                </div>
              )}

              {tab === 'materials' && (
                <div className="text-center py-10">
                  <div className="text-3xl mb-3">📁</div>
                  <p className="text-sm text-brand-ink">资料功能将在后续批次开放</p>
                  <p className="text-xs text-brand-muted mt-1">会议附件、纪要归档与共享资料库（P0 批次 B）。</p>
                </div>
              )}

              {tab === 'actions' && (
                <div>
                  {detail.actions.length === 0 ? (
                    <p className="text-sm text-brand-muted mb-3">暂无行动项。</p>
                  ) : (
                    <ul className="space-y-2">
                      {detail.actions.map((a) => (
                        <li key={a.id} className="flex items-start gap-2 text-sm border border-brand-line rounded-lg p-2.5">
                          <input type="checkbox" checked={a.status === 'done'}
                            onChange={() => toggleAction(a.id, a.status === 'done' ? 'open' : 'done')}
                            className="mt-0.5 accent-[#3B82F6]" />
                          <div className="flex-1">
                            <p className={`text-brand-ink ${a.status === 'done' ? 'line-through text-brand-muted' : ''}`}>{a.content}</p>
                            <p className="text-xs text-brand-muted mt-0.5">
                              {a.owner_name || '未指派'}{a.due_date ? ` · 截止 ${a.due_date}` : ''}
                            </p>
                          </div>
                          {a.status === 'done' && a.completed_at && (
                            <span className="text-xs text-brand-success flex-shrink-0">✓ {fmt(a.completed_at).slice(5)}</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                  <div className="mt-3 space-y-2">
                    <input value={actContent} onChange={(e) => setActContent(e.target.value)} placeholder="行动项内容"
                      className="w-full text-xs border border-brand-line rounded-lg px-2 py-1.5" />
                    <div className="flex gap-2">
                      <select value={actOwner} onChange={(e) => setActOwner(e.target.value)}
                        className="flex-1 text-xs border border-brand-line rounded-lg px-2 py-1.5 bg-white">
                        <option value="">未指派</option>
                        {members.map((m) => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}
                      </select>
                      <input type="date" value={actDue} onChange={(e) => setActDue(e.target.value)}
                        className="w-32 text-xs border border-brand-line rounded-lg px-2 py-1.5 bg-white" />
                    </div>
                    <button onClick={addAction} className="text-xs text-brand-primary hover:underline">+ 添加行动项</button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// 概览行组件
const Row: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div className="flex items-start gap-3">
    <span className="text-brand-muted w-14 flex-shrink-0">{label}</span>
    <span className="flex-1 text-brand-ink">{children}</span>
  </div>
)

export default Meetings
