import React, { useCallback, useEffect, useState } from 'react'
import { teamApi, Team } from '../api/teams'
import { accountApi, MemberRow } from '../api/account'
import {
  Message, MessageTab,
  messagesApi,
} from '../api/messages'

const TYPE_LABELS: Record<string, string> = {
  system: '系统',
  mention: '@提醒',
  action_item: '行动项',
  file_upload: '文件上传',
  meeting_reminder: '会议提醒',
  direct: '私信',
}
const TYPE_ICONS: Record<string, string> = {
  system: '⚙️',
  mention: '💬',
  action_item: '✅',
  file_upload: '📎',
  meeting_reminder: '📅',
  direct: '✉️',
}
const TABS: { key: MessageTab; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'notifications', label: '通知' },
  { key: 'at_me', label: '@我' },
]

const fmt = (iso: string | null) => {
  if (!iso) return ''
  const d = new Date(iso)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

const Messages: React.FC = () => {
  const [team, setTeam] = useState<Team | null>(null)
  const [members, setMembers] = useState<MemberRow[]>([])
  const [forbidden, setForbidden] = useState(false)
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState('')

  const [tab, setTab] = useState<MessageTab>('all')
  const [messages, setMessages] = useState<Message[]>([])
  const [total, setTotal] = useState(0)
  const [unreadCount, setUnreadCount] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)

  const [detail, setDetail] = useState<Message | null>(null)

  const [showDM, setShowDM] = useState(false)
  const [dmRecipient, setDmRecipient] = useState('')
  const [dmTitle, setDmTitle] = useState('')
  const [dmContent, setDmContent] = useState('')
  const [sending, setSending] = useState(false)

  const teamId = team?.id

  const flash = (t: string) => { setMsg(t); setTimeout(() => setMsg(''), 3000) }

  const loadMessages = useCallback(async (t: MessageTab, p: number) => {
    if (!teamId) return
    try {
      const r = await messagesApi.list(teamId, t, p, pageSize)
      setMessages(r?.items || [])
      setTotal(r?.total || 0)
      setUnreadCount(r?.unread_count || 0)
    } catch (e: any) {
      if (e?.response?.status === 403) setForbidden(true)
      else console.error(e)
    }
  }, [teamId, pageSize])

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
          await loadMessages(tab, 1)
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

  const changeTab = (t: MessageTab) => {
    setTab(t)
    setPage(1)
    loadMessages(t, 1)
  }

  const changePage = (p: number) => {
    setPage(p)
    loadMessages(tab, p)
  }

  const openDetail = async (m: Message) => {
    setDetail(m)
    if (!m.is_read && teamId) {
      try {
        const r = await messagesApi.markRead(teamId, m.id)
        setUnreadCount((r as any)?.total_unread ?? unreadCount - 1)
        await loadMessages(tab, page)
      } catch { /* ignore */ }
    }
  }

  const doMarkAll = async () => {
    if (!teamId) return
    try {
      await messagesApi.markAllRead(teamId)
      setUnreadCount(0)
      flash('全部标记为已读')
      await loadMessages(tab, page)
    } catch (e: any) {
      flash(e?.response?.data?.detail || '操作失败')
    }
  }

  const sendDM = async () => {
    if (!teamId || !dmRecipient || !dmTitle.trim()) { flash('请填写收件人和标题'); return }
    setSending(true)
    try {
      await messagesApi.send(teamId, {
        recipient_id: Number(dmRecipient),
        title: dmTitle.trim(),
        content: dmContent.trim() || null,
      })
      flash('私信已发送')
      setShowDM(false)
      setDmTitle('')
      setDmContent('')
      setDmRecipient('')
      await loadMessages(tab, page)
    } catch (e: any) {
      flash(e?.response?.data?.detail || '发送失败')
    } finally {
      setSending(false)
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

  const totalPages = Math.ceil(total / pageSize)
  const otherMembers = members.filter((m) => m.user_id !== teamId).slice(0, 50)

  return (
    <div className="space-y-4">
      {/* 页头 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-brand-ink">讯息中心</h1>
          {unreadCount > 0 && (
            <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
              {unreadCount} 未读
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={doMarkAll}
            disabled={unreadCount === 0}
            className="text-sm text-slate-500 hover:text-blue-600 disabled:opacity-40 transition"
          >
            全部已读
          </button>
          <button
            onClick={() => setShowDM(true)}
            className="bg-blue-600 text-white text-sm px-4 py-2 rounded-xl hover:bg-blue-700 transition"
          >
            ✉️ 发私信
          </button>
        </div>
      </div>

      {msg && <div className="bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 text-xs text-blue-700">{msg}</div>}

      {/* 页签 */}
      <div className="flex gap-1 border-b border-brand-line">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => changeTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition ${
              tab === t.key
                ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/50'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {t.label}
            {t.key === 'all' && unreadCount > 0 && (
              <span className="ml-1.5 bg-red-500 text-white text-[10px] px-1.5 py-0.5 rounded-full">{unreadCount}</span>
            )}
          </button>
        ))}
      </div>

      {/* 消息列表 */}
      <div className="space-y-1">
        {messages.map((m) => (
          <button
            key={m.id}
            onClick={() => openDetail(m)}
            className={`w-full text-left p-3 rounded-xl border transition hover:shadow-sm ${
              m.is_read ? 'border-brand-line bg-white' : 'border-blue-200 bg-blue-50/40'
            }`}
          >
            <div className="flex items-start gap-3">
              <span className="text-lg flex-shrink-0 mt-0.5">{TYPE_ICONS[m.msg_type] || '📩'}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  {!m.is_read && <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />}
                  <span className={`text-sm font-medium ${m.is_read ? 'text-slate-600' : 'text-brand-ink'}`}>
                    {m.title}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
                    {TYPE_LABELS[m.msg_type] || m.msg_type}
                  </span>
                </div>
                {m.content && <p className="text-xs text-slate-500 mt-0.5 truncate">{m.content}</p>}
                <p className="text-[10px] text-slate-400 mt-1">
                  {m.sender_name ? `${m.sender_name} · ` : ''}{fmt(m.created_at)}
                </p>
              </div>
            </div>
          </button>
        ))}
        {messages.length === 0 && (
          <p className="text-center py-10 text-sm text-slate-400">暂无消息</p>
        )}
      </div>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 text-sm">
          <button
            onClick={() => changePage(page - 1)}
            disabled={page <= 1}
            className="px-3 py-1 rounded-lg border border-brand-line disabled:opacity-40 text-slate-500"
          >
            上一页
          </button>
          <span className="text-slate-500">{page} / {totalPages}</span>
          <button
            onClick={() => changePage(page + 1)}
            disabled={page >= totalPages}
            className="px-3 py-1 rounded-lg border border-brand-line disabled:opacity-40 text-slate-500"
          >
            下一页
          </button>
        </div>
      )}

      {/* 详情抽屉 */}
      {detail && (
        <div className="fixed inset-0 bg-black/30 z-50 flex items-end sm:items-center justify-center sm:p-4" onClick={() => setDetail(null)}>
          <div
            className="bg-white rounded-t-2xl sm:rounded-xl w-full max-w-md p-5 shadow-xl max-h-[70vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-brand-ink">{detail.title}</h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  {TYPE_LABELS[detail.msg_type] || detail.msg_type}
                  {detail.sender_name ? ` · 来自 ${detail.sender_name}` : ''}
                  {' · '}{fmt(detail.created_at)}
                </p>
              </div>
              <button onClick={() => setDetail(null)} className="text-slate-400 hover:text-slate-600 text-lg ml-2">✕</button>
            </div>
            {detail.content && (
              <p className="text-sm text-slate-600 whitespace-pre-wrap mb-3">{detail.content}</p>
            )}
            {detail.reference_type && (
              <div className="bg-slate-50 rounded-lg p-3 text-xs text-slate-500">
                关联：<span className="text-blue-600">{detail.reference_type}</span>
                {detail.reference_id ? ` #${detail.reference_id}` : ''}
              </div>
            )}
            {!detail.is_read && (
              <p className="text-[11px] text-green-600 mt-3">✓ 已标记为已读</p>
            )}
          </div>
        </div>
      )}

      {/* 发私信弹窗 */}
      {showDM && (
        <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4" onClick={() => setShowDM(false)}>
          <div className="bg-white rounded-xl p-5 w-full max-w-sm shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-bold text-brand-ink mb-3">发私信</h3>
            <label className="text-xs text-slate-500 block mb-1">收件人</label>
            <select
              value={dmRecipient}
              onChange={(e) => setDmRecipient(e.target.value)}
              className="w-full border border-brand-line rounded-lg px-3 py-2 text-sm mb-3 bg-white"
            >
              <option value="">请选择成员</option>
              {otherMembers.map((m) => (
                <option key={m.user_id} value={m.user_id}>{m.name}（{m.role}）</option>
              ))}
            </select>
            <label className="text-xs text-slate-500 block mb-1">标题</label>
            <input
              value={dmTitle}
              onChange={(e) => setDmTitle(e.target.value)}
              placeholder="私信标题"
              className="w-full border border-brand-line rounded-lg px-3 py-2 text-sm mb-3"
            />
            <label className="text-xs text-slate-500 block mb-1">内容</label>
            <textarea
              value={dmContent}
              onChange={(e) => setDmContent(e.target.value)}
              placeholder="（可选）详细内容"
              rows={3}
              className="w-full border border-brand-line rounded-lg px-3 py-2 text-sm mb-4 resize-none"
            />
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowDM(false)} className="text-sm text-slate-500 px-3 py-1.5">取消</button>
              <button
                onClick={sendDM}
                disabled={sending}
                className="text-sm text-white bg-blue-600 px-4 py-1.5 rounded-lg disabled:opacity-50"
              >
                {sending ? '发送中…' : '发送'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Messages
