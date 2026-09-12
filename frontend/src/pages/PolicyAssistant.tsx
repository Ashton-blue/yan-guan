import React, { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

interface Policy {
  id: number
  title: string
  issuing_authority: string
  category: string
  summary: string
  is_active: boolean
  publish_date: string
}

interface Template {
  id: number
  name: string
  template_type: string
  status: string
  fields_schema: any[]
  ai_prompt_template: string
}

interface Application {
  id: number
  title: string
  applicant_name: string
  status: string
  submission_deadline: string
  content: any
  ai_generated_hint: string
}

const PolicyAssistant: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'library' | 'ask' | 'forms' | 'templates'>('library')
  const [teamId] = useState(1) // 实际应从上下文获取
  
  // 政策库状态
  const [policies, setPolicies] = useState<Policy[]>([])
  const [searchKeyword, setSearchKeyword] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  
  // 问答状态
  const [messages, setMessages] = useState<{role: 'user' | 'ai', content: string, sources?: any[]}[]>([])
  const [questionInput, setQuestionInput] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  
  // 模板状态
  const [templates, setTemplates] = useState<Template[]>([])
  const [showTemplateForm, setShowTemplateForm] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null)
  const [templateForm, setTemplateForm] = useState({ name: '', template_type: 'application', fields_schema: '', ai_prompt_template: '' })
  
  // 申报表状态
  const [applications, setApplications] = useState<Application[]>([])
  const [showFormEditor, setShowFormEditor] = useState(false)
  const [editingApplication, setEditingApplication] = useState<Application | null>(null)
  const [formData, setFormData] = useState({ title: '', applicant_id: 1, content: {} })
  
  // 时间线提醒
  const [reminders, setReminders] = useState<any[]>([])

  // 加载政策列表
  useEffect(() => {
    loadPolicies()
    loadTemplates()
    loadApplications()
    loadReminders()
  }, [])

  const loadPolicies = async () => {
    try {
      const res = await axios.get(`${API_BASE}/policies`, { params: { team_id: teamId, keyword: searchKeyword, category: filterCategory || undefined } })
      setPolicies(res.data.items || [])
    } catch (e) {
      console.error('加载政策失败', e)
    }
  }

  const loadTemplates = async () => {
    try {
      const res = await axios.get(`${API_BASE}/policies/templates`, { params: { team_id: teamId } })
      setTemplates(res.data || [])
    } catch (e) {
      console.error('加载模板失败', e)
    }
  }

  const loadApplications = async () => {
    try {
      const res = await axios.get(`${API_BASE}/policies/applications`, { params: { team_id: teamId } })
      setApplications(res.data.items || [])
    } catch (e) {
      console.error('加载申报失败', e)
    }
  }

  const loadReminders = async () => {
    try {
      const res = await axios.get(`${API_BASE}/policies/applications/reminders`, { params: { team_id: teamId } })
      setReminders(res.data.upcoming || [])
    } catch (e) {
      console.error('加载提醒失败', e)
    }
  }

  // 发送问答
  const handleAsk = async () => {
    if (!questionInput.trim()) return
    
    const question = questionInput.trim()
    setQuestionInput('')
    setMessages(prev => [...prev, { role: 'user', content: question }])
    setIsGenerating(true)
    
    try {
      const res = await axios.post(`${API_BASE}/policies/qa`, { question }, { params: { team_id: teamId } })
      setMessages(prev => [...prev, { 
        role: 'ai', 
        content: res.data.answer,
        sources: res.data.sources
      }])
    } catch (e: any) {
      setMessages(prev => [...prev, { 
        role: 'ai', 
        content: `请求失败: ${e.response?.data?.detail || e.message}` 
      }])
    } finally {
      setIsGenerating(false)
    }
  }

  // 创建/更新模板
  const handleSaveTemplate = async () => {
    try {
      const payload = {
        ...templateForm,
        fields_schema: templateForm.fields_schema ? JSON.parse(templateForm.fields_schema) : null,
        ai_prompt_template: templateForm.ai_prompt_template || null
      }
      
      if (editingTemplate) {
        await axios.put(`${API_BASE}/policies/templates/${editingTemplate.id}`, payload, { params: { team_id: teamId } })
      } else {
        await axios.post(`${API_BASE}/policies/templates`, payload, { params: { team_id: teamId } })
      }
      
      setShowTemplateForm(false)
      setEditingTemplate(null)
      setTemplateForm({ name: '', template_type: 'application', fields_schema: '', ai_prompt_template: '' })
      loadTemplates()
    } catch (e: any) {
      alert(e.response?.data?.detail || '保存失败')
    }
  }

  // 创建申报表
  const handleCreateApplication = async () => {
    try {
      const payload = {
        ...formData,
        content: formData.content || {}
      }
      await axios.post(`${API_BASE}/policies/applications`, payload, { params: { team_id: teamId } })
      setShowFormEditor(false)
      setFormData({ title: '', applicant_id: 1, content: {} })
      loadApplications()
    } catch (e: any) {
      alert(e.response?.data?.detail || '创建失败')
    }
  }

  // AI生成草稿
  const handleGenerateDraft = async (formId: number) => {
    try {
      await axios.post(`${API_BASE}/policies/applications/${formId}/generate`, {
        fields: ['abstract', 'research_content']
      }, { params: { team_id: teamId } })
      loadApplications()
      alert('AI草稿已生成')
    } catch (e: any) {
      if (e.response?.status === 403) {
        alert('您没有权限使用AI生成功能')
      } else {
        alert(e.response?.data?.detail || '生成失败')
      }
    }
  }

  // 快捷问题
  const quickQuestions = [
    '帮我生成国自然青年申请摘要',
    '社科基金限项规定是什么？',
    '青年项目申报年龄要求？',
    '教育部人文社科申请条件？'
  ]

  return (
    <div className="max-w-6xl mx-auto">
      {/* 页面标题栏 */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-2">
        <div>
          <h1 className="text-xl font-bold text-brand-ink">📜 政策助手</h1>
          <p className="text-sm text-brand-muted mt-1">科研政策智能问答 · 申报材料辅助生成</p>
        </div>
        {reminders.length > 0 && (
          <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 text-amber-700 px-3 py-1.5 rounded-lg text-sm">
            <span className="pulse-dot inline-block w-2 h-2 bg-amber-500 rounded-full"></span>
            {reminders.length} 个申报即将到期
          </div>
        )}
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-6 border-b border-brand-line mb-6 overflow-x-auto">
        <button 
          onClick={() => setActiveTab('library')}
          className={`tab-btn pb-2 px-1 text-sm whitespace-nowrap ${activeTab === 'library' ? 'tab-active' : 'text-brand-muted hover:text-brand-primary'}`}
        >
          📚 政策库
        </button>
        <button 
          onClick={() => setActiveTab('ask')}
          className={`tab-btn pb-2 px-1 text-sm whitespace-nowrap ${activeTab === 'ask' ? 'tab-active' : 'text-brand-muted hover:text-brand-primary'}`}
        >
          💬 智能问答
        </button>
        <button 
          onClick={() => setActiveTab('forms')}
          className={`tab-btn pb-2 px-1 text-sm whitespace-nowrap ${activeTab === 'forms' ? 'tab-active' : 'text-brand-muted hover:text-brand-primary'}`}
        >
          📝 申报辅助
        </button>
        <button 
          onClick={() => setActiveTab('templates')}
          className={`tab-btn pb-2 px-1 text-sm whitespace-nowrap ${activeTab === 'templates' ? 'tab-active' : 'text-brand-muted hover:text-brand-primary'}`}
        >
          📋 模板管理
        </button>
      </div>

      {/* ====== Tab 1: 政策库 ====== */}
      {activeTab === 'library' && (
        <div className="fade-in">
          <div className="bg-white rounded-xl border border-brand-line p-5 mb-4">
            <div className="flex flex-col md:flex-row gap-3">
              <div className="flex-1 relative">
                <input 
                  type="text" 
                  placeholder="搜索政策名称、发文单位、关键词..." 
                  className="w-full pl-10 pr-4 py-2 border border-brand-line rounded-lg text-sm focus:outline-none focus:border-brand-primary bg-brand-bg-warm/50"
                  value={searchKeyword}
                  onChange={(e) => setSearchKeyword(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && loadPolicies()}
                />
                <svg className="absolute left-3 top-2.5 w-4 h-4 text-brand-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
              </div>
              <select 
                className="border border-brand-line rounded-lg px-3 py-2 text-sm text-brand-muted focus:outline-none focus:border-brand-primary bg-white"
                value={filterCategory}
                onChange={(e) => setFilterCategory(e.target.value)}
              >
                <option value="">全部分类</option>
                <option value="国自然">国自然</option>
                <option value="社科基金">社科基金</option>
                <option value="省部级">省部级</option>
                <option value="校级">校级</option>
              </select>
              <button onClick={loadPolicies} className="bg-brand-primary text-white px-4 py-2 rounded-lg text-sm hover:bg-brand-primary-light transition">搜索</button>
            </div>
          </div>

          <div className="space-y-3">
            {policies.map(policy => (
              <div key={policy.id} className="policy-card bg-white rounded-xl border border-brand-line p-5 transition-all hover:shadow-md cursor-pointer">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="bg-red-100 text-brand-primary text-xs px-2 py-0.5 rounded-full font-medium">{policy.category}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${policy.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {policy.is_active ? '🟢 生效中' : '⚪ 已截止'}
                      </span>
                      <span className="text-brand-muted text-xs">发布于 {new Date(policy.publish_date).toLocaleDateString()}</span>
                    </div>
                    <h3 className="font-medium text-brand-ink text-base mb-2">{policy.title}</h3>
                    <p className="text-sm text-brand-muted mb-3">{policy.summary}</p>
                    <div className="flex items-center gap-4 text-xs text-brand-muted flex-wrap">
                      <span>📌 发文单位：{policy.issuing_authority}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {policies.length === 0 && (
              <div className="text-center py-12 text-brand-muted">
                <div className="text-4xl mb-2">📭</div>
                <p>暂无政策文档</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ====== Tab 2: 智能问答 ====== */}
      {activeTab === 'ask' && (
        <div className="fade-in">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" style={{ height: 'calc(100vh - 240px)' }}>
            <div className="lg:col-span-2 bg-white rounded-xl border border-brand-line flex flex-col" style={{ height: '100%' }}>
              <div className="px-4 py-3 border-b border-brand-line flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-lg">🤖</span>
                  <span className="font-medium text-brand-ink">政策问答助手</span>
                  <span className="text-xs text-brand-muted bg-gray-100 px-2 py-0.5 rounded-full">基于政策库检索 + DeepSeek生成</span>
                </div>
              </div>
              
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 && (
                  <div className="text-center text-brand-muted py-8">
                    <div className="text-4xl mb-2">💬</div>
                    <p>输入您的政策问题，我将为您检索政策库并生成回答</p>
                  </div>
                )}
                
                {messages.map((msg, idx) => (
                  <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                    {msg.role === 'ai' && (
                      <div className="w-8 h-8 bg-brand-primary rounded-full flex items-center justify-center text-white text-sm flex-shrink-0">🤖</div>
                    )}
                    <div className={msg.role === 'user' ? 'chat-bubble-user p-3 text-sm text-brand-ink max-w-[85%]' : 'chat-bubble-ai p-4 text-sm text-brand-muted max-w-[90%]'}>
                      {msg.content}
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="border-t border-brand-line pt-3 mt-3">
                          <p className="font-medium text-brand-ink mb-2">📎 来源政策：</p>
                          <div className="space-y-1">
                            {msg.sources.map((s: any, i: number) => (
                              <a key={i} href={s.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-brand-primary text-sm hover:underline">
                                <span>📄</span> {s.title} — {s.authority}
                              </a>
                            ))}
                          </div>
                        </div>
                      )}
                      {msg.role === 'ai' && (
                        <p className="text-xs text-brand-muted mt-3">⚠️ AI辅助生成，仅供参考</p>
                      )}
                    </div>
                    {msg.role === 'user' && (
                      <div className="w-8 h-8 bg-brand-primary-light rounded-full flex items-center justify-center text-white text-sm flex-shrink-0">我</div>
                    )}
                  </div>
                ))}
                
                {isGenerating && (
                  <div className="flex gap-3">
                    <div className="w-8 h-8 bg-brand-primary rounded-full flex items-center justify-center text-white text-sm flex-shrink-0">🤖</div>
                    <div className="chat-bubble-ai p-3 text-sm">
                      <div className="flex gap-1 items-center">
                        <span className="typing-dot w-2 h-2 bg-gray-400 rounded-full inline-block"></span>
                        <span className="typing-dot w-2 h-2 bg-gray-400 rounded-full inline-block"></span>
                        <span className="typing-dot w-2 h-2 bg-gray-400 rounded-full inline-block"></span>
                        <span className="text-brand-muted ml-2 text-xs">正在检索政策库并生成回答...</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              
              <div className="px-4 py-2 border-t border-brand-line bg-gray-50">
                <div className="flex flex-wrap gap-2">
                  <span className="text-xs text-brand-muted">快捷问题：</span>
                  {quickQuestions.slice(0, 4).map((q, i) => (
                    <button 
                      key={i} 
                      onClick={() => { setQuestionInput(q); handleAsk(); }}
                      className="text-xs bg-white border border-brand-line text-brand-muted px-2.5 py-1 rounded-full hover:border-brand-primary hover:text-brand-primary transition"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
              
              <div className="px-4 py-3 border-t border-brand-line">
                <div className="flex gap-2">
                  <input 
                    type="text" 
                    value={questionInput}
                    onChange={(e) => setQuestionInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
                    placeholder="输入您的政策问题..." 
                    className="flex-1 px-4 py-2.5 border border-brand-line rounded-lg text-sm focus:outline-none focus:border-brand-primary bg-brand-bg-warm/50"
                  />
                  <button 
                    onClick={handleAsk}
                    disabled={isGenerating}
                    className="bg-brand-primary text-white px-4 py-2.5 rounded-lg text-sm hover:bg-brand-primary-light transition font-medium disabled:opacity-50"
                  >
                    发送
                  </button>
                </div>
                <p className="text-xs text-brand-muted mt-1">AI生成内容仅供参考，请以官方政策文件为准。</p>
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="bg-white rounded-xl border border-brand-line p-4">
                <h4 className="font-medium text-brand-ink text-sm mb-3">💡 您可能还想了解</h4>
                <div className="space-y-2">
                  {['青年项目申请书撰写要点', '各类项目限项规则详解', '2026年主要项目申报时间节点'].map((q, i) => (
                    <button key={i} onClick={() => { setQuestionInput(q); handleAsk(); }} className="block w-full text-left p-2 rounded hover:bg-brand-bg-warm transition text-sm text-brand-muted hover:text-brand-primary">
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ====== Tab 3: 申报辅助 ====== */}
      {activeTab === 'forms' && (
        <div className="fade-in">
          {/* 时间线提醒 */}
          {reminders.length > 0 && (
            <div className="mt-4 bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4">
              <div className="flex items-start gap-3">
                <span className="text-2xl">⏰</span>
                <div className="flex-1">
                  <h4 className="font-medium text-amber-800 text-sm">即将到期的申报</h4>
                  <div className="mt-2 space-y-2">
                    {reminders.filter(r => r.days_left <= 3).map((r: any) => (
                      <div key={r.form_id} className="flex items-center justify-between bg-white rounded-lg px-3 py-2 gap-2 flex-wrap">
                        <div>
                          <span className="text-sm text-brand-ink font-medium">{r.title}</span>
                          <span className="text-xs text-red-500 ml-2">⚠️ 还剩 {r.days_left} 天</span>
                        </div>
                        <button className="text-xs bg-brand-primary text-white px-2 py-1 rounded-lg hover:bg-brand-primary-light transition">去完善</button>
                      </div>
                    ))}
                    {reminders.filter(r => r.days_left > 3 && r.days_left <= 7).map((r: any) => (
                      <div key={r.form_id} className="flex items-center justify-between bg-white rounded-lg px-3 py-2 gap-2 flex-wrap">
                        <div>
                          <span className="text-sm text-brand-ink font-medium">{r.title}</span>
                          <span className="text-xs text-amber-500 ml-2">还剩 {r.days_left} 天</span>
                        </div>
                        <button className="text-xs border border-amber-300 text-amber-700 px-2 py-1 rounded-lg hover:bg-amber-50 transition">去完善</button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <select className="border border-brand-line rounded-lg px-3 py-1.5 text-sm text-brand-muted focus:outline-none focus:border-brand-primary bg-white">
                <option>全部状态</option>
                <option>草稿</option>
                <option>已提交</option>
                <option>已立项</option>
                <option>未立项</option>
              </select>
            </div>
            <button 
              onClick={() => setShowFormEditor(true)}
              className="bg-brand-primary text-white px-4 py-1.5 rounded-lg text-sm hover:bg-brand-primary-light transition flex items-center gap-2"
            >
              <span>+</span> 新建申报表
            </button>
          </div>

          <div className="bg-white rounded-xl border border-brand-line overflow-hidden">
            <table className="w-full text-sm min-w-[720px]">
              <thead>
                <tr className="border-b border-brand-line">
                  <th className="text-left px-4 py-3 text-brand-muted font-medium">项目名称</th>
                  <th className="text-left px-4 py-3 text-brand-muted font-medium">申请人</th>
                  <th className="text-left px-4 py-3 text-brand-muted font-medium">状态</th>
                  <th className="text-left px-4 py-3 text-brand-muted font-medium">截止申报</th>
                  <th className="text-left px-4 py-3 text-brand-muted font-medium">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-line">
                {applications.map(app => (
                  <tr key={app.id} className="hover:bg-brand-bg-warm transition">
                    <td className="px-4 py-3">
                      <div className="font-medium text-brand-ink">{app.title}</div>
                      <div className="text-xs text-brand-muted mt-0.5">ID: {app.id}</div>
                    </td>
                    <td className="px-4 py-3 text-brand-muted">{app.applicant_name || '未知'}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        app.status === 'draft' ? 'bg-amber-100 text-amber-700' :
                        app.status === 'submitted' ? 'bg-green-100 text-green-700' :
                        'bg-gray-100 text-gray-500'
                      }`}>
                        {app.status === 'draft' ? '草稿' : app.status === 'submitted' ? '已提交' : app.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-brand-muted">
                      {app.submission_deadline ? new Date(app.submission_deadline).toLocaleDateString() : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button 
                          onClick={() => { setEditingApplication(app); setShowFormEditor(true); }}
                          className="text-brand-primary text-xs hover:underline"
                        >
                          编辑
                        </button>
                        {app.status === 'draft' && (
                          <button 
                            onClick={() => handleGenerateDraft(app.id)}
                            className="text-green-600 text-xs hover:underline"
                          >
                            AI生成
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {applications.length === 0 && (
                  <tr>
                    <td colSpan={5} className="text-center py-8 text-brand-muted">
                      暂无申报表，点击「新建申报表」开始创建
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* 新建/编辑申报表弹窗 */}
          {showFormEditor && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
              <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                <div className="p-5 border-b border-brand-line flex items-center justify-between">
                  <h2 className="font-medium text-brand-ink">{editingApplication ? '编辑申报表' : '新建申报表'}</h2>
                  <button onClick={() => { setShowFormEditor(false); setEditingApplication(null); }} className="text-brand-muted hover:text-brand-ink">✕</button>
                </div>
                <div className="p-5 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-brand-ink mb-1">项目名称 <span className="text-red-500">*</span></label>
                    <input 
                      type="text" 
                      value={formData.title}
                      onChange={(e) => setFormData({...formData, title: e.target.value})}
                      className="w-full px-4 py-2.5 border border-brand-line rounded-lg text-sm focus:outline-none focus:border-brand-primary"
                      placeholder="请输入项目名称"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-brand-ink mb-1">模板选择</label>
                    <select className="w-full px-4 py-2.5 border border-brand-line rounded-lg text-sm focus:outline-none focus:border-brand-primary bg-white">
                      <option value="">请选择模板</option>
                      {templates.map(t => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-brand-ink mb-1">截止时间</label>
                    <input 
                      type="datetime-local" 
                      className="w-full px-4 py-2.5 border border-brand-line rounded-lg text-sm focus:outline-none focus:border-brand-primary"
                    />
                  </div>
                </div>
                <div className="p-5 border-t border-brand-line flex justify-end gap-3">
                  <button 
                    onClick={() => { setShowFormEditor(false); setEditingApplication(null); }}
                    className="px-4 py-2 text-sm text-brand-muted hover:text-brand-ink transition"
                  >
                    取消
                  </button>
                  <button 
                    onClick={handleCreateApplication}
                    className="bg-brand-primary text-white px-4 py-2 rounded-lg text-sm hover:bg-brand-primary-light transition"
                  >
                    保存
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ====== Tab 4: 模板管理 ====== */}
      {activeTab === 'templates' && (
        <div className="fade-in">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <p className="text-sm text-brand-muted">管理申报材料模板，支持AI辅助生成</p>
            <button 
              onClick={() => { setEditingTemplate(null); setShowTemplateForm(true); }}
              className="bg-brand-primary text-white px-4 py-1.5 rounded-lg text-sm hover:bg-brand-primary-light transition flex items-center gap-2"
            >
              <span>+</span> 新增模板
            </button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map(template => (
              <div key={template.id} className="bg-white rounded-xl border border-brand-line p-5 hover:shadow-md transition cursor-pointer">
                <div className="flex items-start justify-between mb-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    template.template_type === 'application' ? 'bg-red-100 text-brand-primary' :
                    template.template_type === 'progress' ? 'bg-orange-100 text-orange-700' :
                    'bg-purple-100 text-purple-700'
                  }`}>
                    {template.template_type === 'application' ? '申请书' : template.template_type === 'progress' ? '进度报告' : '结题报告'}
                  </span>
                  <span className="text-xs text-brand-muted">v1.0</span>
                </div>
                <h3 className="font-medium text-brand-ink mb-1">{template.name}</h3>
                <p className="text-xs text-brand-muted mb-4">
                  {template.fields_schema ? `${template.fields_schema.length} 个字段` : '无字段定义'}
                </p>
                <div className="flex items-center justify-between">
                  <span className={`text-xs ${template.status === 'active' ? 'text-green-600' : 'text-brand-muted'}`}>
                    {template.status === 'active' ? '✅ 启用中' : '⏸ 未启用'}
                  </span>
                  <div className="flex gap-2">
                    <button 
                      onClick={() => { setEditingTemplate(template); setShowTemplateForm(true); }}
                      className="text-xs text-brand-primary hover:underline"
                    >
                      编辑
                    </button>
                    <button className="text-xs text-brand-muted hover:text-brand-ink">更多</button>
                  </div>
                </div>
              </div>
            ))}
            {templates.length === 0 && (
              <div className="col-span-full text-center py-12 text-brand-muted">
                <div className="text-4xl mb-2">📋</div>
                <p>暂无模板，点击「新增模板」开始创建</p>
              </div>
            )}
          </div>

          {/* 新建/编辑模板弹窗 */}
          {showTemplateForm && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
              <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                <div className="p-5 border-b border-brand-line flex items-center justify-between">
                  <h2 className="font-medium text-brand-ink">{editingTemplate ? '编辑模板' : '新增模板'}</h2>
                  <button onClick={() => setShowTemplateForm(false)} className="text-brand-muted hover:text-brand-ink">✕</button>
                </div>
                <div className="p-5 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-brand-ink mb-1">模板名称 <span className="text-red-500">*</span></label>
                    <input 
                      type="text" 
                      value={templateForm.name}
                      onChange={(e) => setTemplateForm({...templateForm, name: e.target.value})}
                      className="w-full px-4 py-2.5 border border-brand-line rounded-lg text-sm focus:outline-none focus:border-brand-primary"
                      placeholder="如：国自然青年项目申请书"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-brand-ink mb-1">模板类型</label>
                    <select 
                      value={templateForm.template_type}
                      onChange={(e) => setTemplateForm({...templateForm, template_type: e.target.value})}
                      className="w-full px-4 py-2.5 border border-brand-line rounded-lg text-sm focus:outline-none focus:border-brand-primary bg-white"
                    >
                      <option value="application">申请书</option>
                      <option value="progress">进度报告</option>
                      <option value="final_report">结题报告</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-brand-ink mb-1">字段定义 (JSON)</label>
                    <textarea 
                      value={templateForm.fields_schema}
                      onChange={(e) => setTemplateForm({...templateForm, fields_schema: e.target.value})}
                      className="w-full px-4 py-2.5 border border-brand-line rounded-lg text-sm focus:outline-none focus:border-brand-primary font-mono text-xs"
                      rows={4}
                      placeholder='[{"key": "project_title", "label": "项目名称", "type": "text", "required": true}]'
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-brand-ink mb-1">AI提示词模板</label>
                    <textarea 
                      value={templateForm.ai_prompt_template}
                      onChange={(e) => setTemplateForm({...templateForm, ai_prompt_template: e.target.value})}
                      className="w-full px-4 py-2.5 border border-brand-line rounded-lg text-sm focus:outline-none focus:border-brand-primary font-mono text-xs"
                      rows={4}
                      placeholder="请根据以下信息生成{field}的内容..."
                    />
                  </div>
                </div>
                <div className="p-5 border-t border-brand-line flex justify-end gap-3">
                  <button 
                    onClick={() => setShowTemplateForm(false)}
                    className="px-4 py-2 text-sm text-brand-muted hover:text-brand-ink transition"
                  >
                    取消
                  </button>
                  <button 
                    onClick={handleSaveTemplate}
                    className="bg-brand-primary text-white px-4 py-2 rounded-lg text-sm hover:bg-brand-primary-light transition"
                  >
                    保存
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default PolicyAssistant
