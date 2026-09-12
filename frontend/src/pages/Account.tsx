import React, { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { teamApi, Team } from '../api/teams'
import { accountApi, MemberRow, TeamInvite } from '../api/account'

const ROLE_LABELS: Record<string, string> = {
  owner: '所有者',
  supervisor: '研究主管',
  co_manager: '协管',
  student: '学生',
  collaborator: '合作者',
  temp_student: '临时学生',
}
const MANAGER_ROLES = ['owner', 'supervisor', 'co_manager']

const Account: React.FC = () => {
  const { user } = useAuth()
  const [team, setTeam] = useState<Team | null>(null)
  const [myRole, setMyRole] = useState<string>('student')
  const [members, setMembers] = useState<MemberRow[]>([])
  const [invites, setInvites] = useState<TeamInvite[]>([])
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState('')

  // 个人资料表单
  const [name, setName] = useState(user?.name || '')
  const [avatarUrl, setAvatarUrl] = useState(user?.avatar_url || '')
  const [researchArea, setResearchArea] = useState(user?.research_area || '')
  const [bio, setBio] = useState(user?.bio || '')

  const canManage = MANAGER_ROLES.includes(myRole)
  const isOwner = myRole === 'owner'

  const load = async (teamId?: number) => {
    try {
      const tid = teamId
      if (tid) {
        const [m, i] = await Promise.all([
          accountApi.listMembers(tid),
          accountApi.listInvites(tid),
        ])
        setMembers(m.data || [])
        setInvites(i.data || [])
      }
      setLoading(false)
    } catch (e) {
      console.error(e)
      setLoading(false)
    }
  }

  useEffect(() => {
    const run = async () => {
      try {
        const teamsRes = await teamApi.listTeams()
        const teams = teamsRes.data || []
        // 优先选「研究室」团队，否则取第一个
        const lab = teams.find((t) => t.name.includes('研究室')) || teams[0] || null
        setTeam(lab)
        if (lab) {
          setMyRole(lab.role || 'student')
          await load(lab.id)
        }
      } catch (e) {
        console.error(e)
        setLoading(false)
      }
    }
    run()
  }, [])

  const refresh = () => { if (team) load(team.id) }

  const flash = (text: string) => { setMsg(text); setTimeout(() => setMsg(''), 3000) }

  const saveProfile = async () => {
    try {
      await accountApi.updateMe({
        name: name.trim() || undefined,
        avatar_url: avatarUrl.trim() || undefined,
        research_area: researchArea.trim() || undefined,
        bio: bio.trim() || undefined,
      })
      flash('个人资料已保存')
    } catch (e: any) {
      flash(e?.response?.data?.detail || '保存失败')
    }
  }

  const doCreateInvite = async (role: string, validDays: number) => {
    if (!team) return
    try {
      await accountApi.createInvite(team.id, { role, valid_days: validDays })
      flash('已生成邀请码')
      refresh()
    } catch (e: any) {
      flash(e?.response?.data?.detail || '生成失败')
    }
  }

  const doRevoke = async (inviteId: number) => {
    if (!team) return
    try {
      await accountApi.revokeInvite(team.id, inviteId)
      flash('邀请码已作废')
      refresh()
    } catch (e: any) {
      flash(e?.response?.data?.detail || '作废失败')
    }
  }

  const doJoin = async () => {
    const code = prompt('请输入邀请码：')
    if (!code) return
    try {
      await accountApi.joinTeam(code.trim())
      flash('加入团队成功')
    } catch (e: any) {
      flash(e?.response?.data?.detail || '加入失败')
    }
  }

  const doPatchRole = async (m: MemberRow, role: string) => {
    if (!team) return
    try {
      await accountApi.patchMember(team.id, m.user_id, { role })
      flash(`${m.name} 角色已调整为 ${ROLE_LABELS[role] || role}`)
      refresh()
    } catch (e: any) {
      flash(e?.response?.data?.detail || '调整失败')
    }
  }

  const doToggleActive = async (m: MemberRow) => {
    if (!team) return
    try {
      await accountApi.patchMember(team.id, m.user_id, { is_active: false })
      flash(`已禁用 ${m.name}`)
      refresh()
    } catch (e: any) {
      flash(e?.response?.data?.detail || '操作失败')
    }
  }

  const doRemove = async (m: MemberRow) => {
    if (!team) return
    if (!window.confirm(`确认移除成员 ${m.name}？`)) return
    try {
      await accountApi.removeMember(team.id, m.user_id)
      flash(`已移除 ${m.name}`)
      refresh()
    } catch (e: any) {
      flash(e?.response?.data?.detail || '移除失败')
    }
  }

  const doResetPwd = async (m: MemberRow) => {
    const pwd = prompt(`为 ${m.name} 重置密码（至少 6 位）：`)
    if (!pwd) return
    try {
      await accountApi.resetMemberPassword(m.user_id, pwd)
      flash(`已为 ${m.name} 重置密码（对方下次登录须改密）`)
    } catch (e: any) {
      flash(e?.response?.data?.detail || '重置失败')
    }
  }

  const doForgot = async () => {
    const email = prompt('输入需要找回密码的成员邮箱：')
    if (!email) return
    try {
      const r = await accountApi.forgotPassword(email.trim())
      flash(r.message || '已提交')
    } catch (e: any) {
      flash(e?.response?.data?.detail || '该邮箱未找到或无权限')
    }
  }

  return (
    <div className="max-w-6xl mx-auto fade-in">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-bold text-brand-ink">👤 账户管理</h1>
          <p className="text-sm text-brand-muted mt-1">
            个人资料 · 团队与成员生命周期 · 密码找回
            {team && <span className="ml-2 text-brand-primary">| {team.name}</span>}
          </p>
        </div>
        <button onClick={doJoin} className="bg-white border border-brand-line text-brand-ink text-sm px-3 py-1.5 rounded-lg hover:bg-brand-soft transition">
          邀请码加入
        </button>
      </div>

      {msg && (
        <div className="mb-4 text-sm bg-brand-soft-blue text-brand-active border border-brand-line rounded-lg px-3 py-2">{msg}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* 个人资料 */}
        <section className="card p-5 lg:col-span-1">
          <h2 className="font-semibold text-brand-ink mb-4">个人资料</h2>
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 rounded-full overflow-hidden bg-brand-soft-blue flex items-center justify-center text-2xl font-bold text-brand-active flex-shrink-0">
              {user?.avatar_url ? <img src={user.avatar_url} className="w-16 h-16 object-cover" alt="" /> : (user?.name?.[0] || 'U')}
            </div>
            <div className="text-xs text-brand-muted">
              <p>状态：<span className="text-brand-success">{user?.status || 'active'}</span></p>
              <p>邮箱：{user?.email}</p>
            </div>
          </div>
          <label className="block text-xs text-brand-muted mb-1">头像 URL</label>
          <input value={avatarUrl} onChange={(e) => setAvatarUrl(e.target.value)}
            placeholder="https://…/avatar.png"
            className="w-full text-sm border border-brand-line rounded-lg px-3 py-2 mb-3 focus:outline-none focus:ring-1 focus:ring-brand-primary" />
          <label className="block text-xs text-brand-muted mb-1">昵称</label>
          <input value={name} onChange={(e) => setName(e.target.value)}
            className="w-full text-sm border border-brand-line rounded-lg px-3 py-2 mb-3 focus:outline-none focus:ring-1 focus:ring-brand-primary" />
          <label className="block text-xs text-brand-muted mb-1">研究方向</label>
          <input value={researchArea} onChange={(e) => setResearchArea(e.target.value)}
            className="w-full text-sm border border-brand-line rounded-lg px-3 py-2 mb-3 focus:outline-none focus:ring-1 focus:ring-brand-primary" />
          <label className="block text-xs text-brand-muted mb-1">简介</label>
          <textarea value={bio} onChange={(e) => setBio(e.target.value)} rows={3}
            className="w-full text-sm border border-brand-line rounded-lg px-3 py-2 mb-3 focus:outline-none focus:ring-1 focus:ring-brand-primary resize-none" />
          <button onClick={saveProfile} className="bg-brand-primary text-white text-sm px-4 py-2 rounded-lg hover:bg-brand-active transition">保存资料</button>
        </section>

        {/* 密码找回 */}
        <section className="card p-5 lg:col-span-1">
          <h2 className="font-semibold text-brand-ink mb-4">密码找回</h2>
          <p className="text-sm text-brand-muted leading-6 mb-4">
            系统暂未接入邮件服务，密码找回落地为「管理员重置」：由 owner / supervisor 为团队成员重置密码，被重置成员下次登录须立即改密。
          </p>
          <button onClick={doForgot} className="bg-white border border-brand-line text-brand-ink text-sm px-3 py-2 rounded-lg hover:bg-brand-soft transition">
            按邮箱查找可重置成员
          </button>
          {isOwner && (
            <p className="mt-3 text-xs text-brand-muted">你是所有者，可在下方成员列表直接为成员重置密码。</p>
          )}
        </section>

        {/* 邀请码 */}
        <section className="card p-5 lg:col-span-1">
          <h2 className="font-semibold text-brand-ink mb-4">团队邀请码</h2>
          {canManage ? (
            <div className="flex gap-2 mb-3">
              <select id="inv-role" defaultValue="student"
                className="text-sm border border-brand-line rounded-lg px-2 py-2 bg-white">
                <option value="student">学生</option>
                <option value="collaborator">合作者</option>
                <option value="temp_student">临时学生</option>
              </select>
              <button onClick={() => {
                const r = (document.getElementById('inv-role') as HTMLSelectElement)?.value || 'student'
                doCreateInvite(r, 7)
              }} className="bg-brand-primary text-white text-sm px-3 py-2 rounded-lg hover:bg-brand-active transition">
                生成
              </button>
            </div>
          ) : (
            <p className="text-xs text-brand-muted mb-3">当前角色可查看邀请码；仅教师角色可生成 / 作废。</p>
          )}
          {invites.length === 0 ? (
            <p className="text-sm text-brand-muted">暂无邀请码。</p>
          ) : (
            <ul className="space-y-2">
              {invites.map((inv) => (
                <li key={inv.id} className="flex items-center justify-between gap-2 text-sm">
                  <div className="min-w-0">
                    <code className="text-brand-ink font-mono">{inv.code}</code>
                    <span className="ml-2 text-xs text-brand-muted">{ROLE_LABELS[inv.role] || inv.role}</span>
                    {inv.status !== 'active' && <span className="ml-1 text-xs text-brand-warning">{inv.status === 'used' ? '已使用' : '已过期'}</span>}
                  </div>
                  {canManage && inv.status === 'active' && (
                    <button onClick={() => doRevoke(inv.id)} className="text-xs text-brand-danger hover:underline flex-shrink-0">作废</button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* 团队成员生命周期 */}
        <section className="card p-5 lg:col-span-3">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-brand-ink">团队成员</h2>
            <span className="text-xs text-brand-muted">我的角色：{ROLE_LABELS[myRole] || myRole}</span>
          </div>
          {loading ? (
            <p className="text-sm text-brand-muted">加载中…</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[640px]">
                <thead>
                  <tr className="border-b border-brand-line text-brand-muted">
                    <th className="text-left py-2 font-medium">成员</th>
                    <th className="text-left py-2 font-medium">邮箱</th>
                    <th className="text-left py-2 font-medium">角色</th>
                    {isOwner && <th className="text-left py-2 font-medium">操作</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-line">
                  {members.map((m) => (
                    <tr key={m.user_id} className="hover:bg-brand-soft transition">
                      <td className="py-2.5 font-medium text-brand-ink">{m.name}</td>
                      <td className="py-2.5 text-brand-muted">{m.email}</td>
                      <td className="py-2.5">
                        {canManage ? (
                          <select
                            value={m.role}
                            onChange={(e) => doPatchRole(m, e.target.value)}
                            className="text-xs border border-brand-line rounded-lg px-2 py-1 bg-white">
                            {['owner', 'supervisor', 'co_manager', 'student', 'collaborator', 'temp_student'].map((r) => (
                              <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                            ))}
                          </select>
                        ) : (
                          <span className="text-xs bg-brand-soft text-brand-ink px-2 py-0.5 rounded-full">{ROLE_LABELS[m.role] || m.role}</span>
                        )}
                      </td>
                      {isOwner && (
                        <td className="py-2.5 space-x-3 text-xs">
                          <button onClick={() => doResetPwd(m)} className="text-brand-primary hover:underline">重置密码</button>
                          <button onClick={() => doToggleActive(m)} className="text-brand-warning hover:underline">禁用</button>
                          <button onClick={() => doRemove(m)} className="text-brand-danger hover:underline">移除</button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="mt-3 text-xs text-brand-muted">
            说明：邀请码加入、成员启用/禁用/移除、角色调整均以后端查库校验为准（越权 403），前端按角色显隐；全部操作写入审计日志（仅追加）。
          </p>
        </section>
      </div>
    </div>
  )
}

export default Account
