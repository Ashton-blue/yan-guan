-- 研管系统数据库初始化脚本

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    must_change_password BOOLEAN DEFAULT TRUE,
    avatar_url VARCHAR(500),
    research_area VARCHAR(200),
    bio TEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 团队表
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- 团队成员表
CREATE TABLE IF NOT EXISTS team_members (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    role VARCHAR(50) NOT NULL,
    invited_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(team_id, user_id)
);

-- 审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id),
    operator_id INTEGER REFERENCES users(id),
    operator_name VARCHAR(100) NOT NULL,
    operator_role VARCHAR(50) NOT NULL,
    action_type VARCHAR(20) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id INTEGER NOT NULL,
    target_summary VARCHAR(500),
    detail JSONB,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    result VARCHAR(20) DEFAULT 'SUCCESS',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 政策文档表
CREATE TABLE IF NOT EXISTS policy_documents (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    issuing_authority VARCHAR(200) NOT NULL,
    publish_date DATE,
    effective_date DATE,
    expire_date DATE,
    category VARCHAR(100) NOT NULL,
    summary TEXT,
    key_requirements JSONB,
    key_requirements_desc TEXT,
    application_link VARCHAR(500),
    official_source_url VARCHAR(500),
    embedding_vector TEXT,
    ai_tagged_keywords JSONB,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    view_count INTEGER DEFAULT 0
);

-- AI模型密钥表
CREATE TABLE IF NOT EXISTS ai_model_keys (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
    service VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    api_key TEXT NOT NULL,
    base_url VARCHAR(500) DEFAULT 'https://api.deepseek.com',
    is_active BOOLEAN DEFAULT TRUE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(team_id, service, model)
);

-- 政策问答会话表
CREATE TABLE IF NOT EXISTS policy_qa_sessions (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    source_policies JSONB,
    confidence_score INTEGER,
    model_used VARCHAR(50),
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 申报材料模板表
CREATE TABLE IF NOT EXISTS application_templates (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    policy_id INTEGER REFERENCES policy_documents(id),
    template_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    structure JSONB,
    placeholder_text JSONB,
    fields_schema JSONB,
    ai_prompt_template TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 申报表表
CREATE TABLE IF NOT EXISTS application_forms (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
    template_id INTEGER REFERENCES application_templates(id),
    policy_id INTEGER REFERENCES policy_documents(id),
    title VARCHAR(500) NOT NULL,
    applicant_id INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'draft',
    submission_deadline TIMESTAMP,
    content JSONB,
    ai_generated_hint TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    submitted_at TIMESTAMP,
    awarded_at TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_teams_created_by ON teams(created_by);
CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_team ON audit_logs(team_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_time ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_policy_documents_team ON policy_documents(team_id);
CREATE INDEX IF NOT EXISTS idx_policy_documents_category ON policy_documents(category);
CREATE INDEX IF NOT EXISTS idx_policy_documents_active ON policy_documents(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_policy_qa_sessions_team ON policy_qa_sessions(team_id);
CREATE INDEX IF NOT EXISTS idx_policy_qa_sessions_user ON policy_qa_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_application_templates_team ON application_templates(team_id);
CREATE INDEX IF NOT EXISTS idx_application_forms_team ON application_forms(team_id);
CREATE INDEX IF NOT EXISTS idx_application_forms_applicant ON application_forms(applicant_id);
CREATE INDEX IF NOT EXISTS idx_application_forms_status ON application_forms(status);

-- 插入测试数据
INSERT INTO users (email, hashed_password, name, must_change_password) VALUES
('research_test_001@test.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36PQm3iV8jEGH3NmZtQfK2W', '墨蓝的京亚', FALSE);

-- 创建测试团队
INSERT INTO teams (name, description, created_by) VALUES
('测试科研团队', '用于测试研管系统的功能', 1) RETURNING id INTO :team_id;

-- 添加团队成员
INSERT INTO team_members (team_id, user_id, role, invited_by) VALUES
(:team_id, 1, 'owner', NULL);

-- 插入测试政策
INSERT INTO policy_documents (team_id, title, issuing_authority, category, summary, key_requirements_desc, is_active) VALUES
(:team_id, '2026年国家自然科学基金项目指南', '国家自然科学基金委员会', '国自然', '涵盖面上项目、青年科学基金项目、地区科学基金项目等各类项目的申报条件、限项规则及申请注意事项。', '男性年龄不超过35周岁，女性不超过40周岁，具有博士学位或副高级以上职称。', TRUE),
(:team_id, '2026年国家社会科学基金项目申报公告', '全国哲学社会科学工作办公室', '社科基金', '包括重点项目、一般项目、青年项目、西部项目等各类项目的申报条件与评审要点。', '申请人应具有副高级以上职称，正在承担国家社科基金项目的人员不得申请。', TRUE),
(:team_id, '教育部人文社会科学研究一般项目申报通知', '教育部科技司', '省部级', '适用于高校在职教师，负责人限报1项，重点支持教育学、心理学、管理学等学科方向。', '申报人应为高校在职教师，限报1项教育部人文社科一般投资项目。', TRUE);

-- 插入测试模板
INSERT INTO application_templates (team_id, name, template_type, status, fields_schema, ai_prompt_template) VALUES
(:team_id, '国自然青年项目申请书', 'application', 'active', 
 '[{"key": "project_title", "label": "项目名称", "type": "text", "required": true}, {"key": "abstract", "label": "摘要", "type": "textarea", "required": true, "max_length": 500}, {"key": "research_content", "label": "研究内容", "type": "textarea", "required": true}, {"key": "innovation", "label": "创新点", "type": "textarea", "required": false}]',
 '请根据以下信息生成【研究摘要】：\n项目名称：{project_title}\n要求：300字以内，包含研究背景、研究内容、创新点、预期成果'),
(:team_id, '社科基金青年项目申请书', 'application', 'active',
 '[{"key": "project_title", "label": "项目名称", "type": "text", "required": true}, {"key": "abstract", "label": "摘要", "type": "textarea", "required": true}]',
 '请根据以下信息生成【研究摘要】：\n项目名称：{project_title}');

-- 插入测试DeepSeek Key
INSERT INTO ai_model_keys (team_id, service, model, api_key, base_url) VALUES
(:team_id, 'deepseek', 'deepseek-chat', 'sk-IGk4ZN5RmTcaW3AFvdljYf1hYUmLB7XmSfd7ipWrlJqZ4DGe', 'https://api.deepseek.com');

-- 插入测试申报表
INSERT INTO application_forms (team_id, template_id, policy_id, title, applicant_id, status, content) VALUES
(:team_id, 1, 1, '多准则决策在旅游地评价中的应用研究', 1, 'draft', '{"project_title": "多准则决策在旅游地评价中的应用研究", "abstract": "", "research_content": "", "innovation": ""}');

-- ============================================================
-- P0 批次 A 种子：研究室团队 + 5 成员 + 6 场组会（议程/行动项）
-- 数据对齐 v11.0 原型「组会管理」（彦教授导师视角）
-- 注：成员初始密码沿用测试账号同一 hash（部署后请用 /auth/reset-password 重置）
-- ============================================================

-- 5 名成员
INSERT INTO users (email, hashed_password, name, must_change_password, status, research_area, bio)
VALUES ('yan.lab@test.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36PQm3iV8jEGH3NmZtQfK2W', '彦教授', FALSE, 'active',
        '多准则决策与论文写作', '高校管理学教师，研究方向多准则决策与论文写作，研究室主任')
RETURNING id INTO :u_yan;
INSERT INTO users (email, hashed_password, name, must_change_password, status, research_area, bio)
VALUES ('li.lab@test.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36PQm3iV8jEGH3NmZtQfK2W', '李四', FALSE, 'active',
        '多准则决策', '研究主管，硕士二年级')
RETURNING id INTO :u_li;
INSERT INTO users (email, hashed_password, name, must_change_password, status, research_area, bio)
VALUES ('wang.lab@test.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36PQm3iV8jEGH3NmZtQfK2W', '王五', FALSE, 'active',
        '多准则决策', '博士研究生三年级')
RETURNING id INTO :u_wang;
INSERT INTO users (email, hashed_password, name, must_change_password, status, research_area, bio)
VALUES ('zhao.lab@test.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36PQm3iV8jEGH3NmZtQfK2W', '赵六', FALSE, 'active',
        '多准则决策', '硕士研究生二年级')
RETURNING id INTO :u_zhao;
INSERT INTO users (email, hashed_password, name, must_change_password, status, research_area, bio)
VALUES ('qian.lab@test.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36PQm3iV8jEGH3NmZtQfK2W', '钱七', FALSE, 'active',
        '论文写作', '硕士研究生一年级，组会秘书')
RETURNING id INTO :u_qian;

-- 研究室团队（彦教授为 owner）
INSERT INTO teams (name, description, created_by)
VALUES ('多准则决策与论文写作研究室', '面向多准则决策（MCDM）与论文写作方向的研究室，组织文献报告会、进展汇报与答辩预演', :u_yan)
RETURNING id INTO :t_lab;

-- 团队成员
INSERT INTO team_members (team_id, user_id, role, invited_by) VALUES
  (:t_lab, :u_yan,  'owner',      NULL),
  (:t_lab, :u_li,   'supervisor', :u_yan),
  (:t_lab, :u_wang, 'co_manager', :u_yan),
  (:t_lab, :u_zhao, 'student',    :u_yan),
  (:t_lab, :u_qian, 'student',    :u_yan);

-- 组会 1（文献报告 · 已结束）
INSERT INTO meetings (team_id, title, meeting_type, start_at, end_at, location, presenter_id, description, status, created_by)
VALUES (:t_lab, '第18次文献报告会', 'journal', '2026-09-09 19:00:00', '2026-09-09 21:00:00',
        '线上 + 管理学院B302', :u_zhao, 'MCDM 与机器学习融合方法综述', 'finished', :u_yan)
RETURNING id INTO :m1;
INSERT INTO meeting_agenda_items (meeting_id, seq, time_slot, content, presenter_id) VALUES
  (:m1, 0, '19:00–19:10', '报告人介绍与上周纪要回顾', :u_zhao),
  (:m1, 1, '19:10–20:00', '文献报告：MCDM 与 ML 融合方法综述', :u_zhao),
  (:m1, 2, '20:00–20:30', '讨论可解释融合方法的适用性', NULL),
  (:m1, 3, '20:30–21:00', '下期安排与任务分工', :u_wang);
INSERT INTO meeting_actions (meeting_id, content, owner_id, due_date, status, completed_at) VALUES
  (:m1, '补充方法对比表格（MCDM×ML 分类）', :u_zhao, '2026-09-12', 'open', NULL),
  (:m1, '整理第18次组会纪要', :u_qian, '2026-09-10', 'done', '2026-09-10 21:30:00'),
  (:m1, '确认下期文献报告人与主题', :u_wang, '2026-09-09', 'open', NULL);

-- 组会 2（进展汇报 · 未开始）
INSERT INTO meetings (team_id, title, meeting_type, start_at, end_at, location, presenter_id, description, status, created_by)
VALUES (:t_lab, '硕士论文进展汇报', 'progress', '2026-09-11 14:00:00', '2026-09-11 16:00:00',
        '线下·管理学院B302', :u_li, '硕士论文阶段性进展汇报', 'upcoming', :u_yan)
RETURNING id INTO :m2;
INSERT INTO meeting_agenda_items (meeting_id, seq, time_slot, content, presenter_id) VALUES
  (:m2, 0, '14:00–15:00', '李四汇报硕士论文研究进展', :u_li),
  (:m2, 1, '15:00–15:30', '彦教授逐章指导与提问', :u_yan),
  (:m2, 2, '15:30–16:00', '确定下一步修改计划', :u_li);
INSERT INTO meeting_actions (meeting_id, content, owner_id, due_date, status, completed_at) VALUES
  (:m2, '更新案例编码规范 v2', :u_li, '2026-09-13', 'open', NULL),
  (:m2, '反馈论文提纲批注', :u_yan, '2026-09-12', 'open', NULL);

-- 组会 3（答辩预演 · 未开始）
INSERT INTO meetings (team_id, title, meeting_type, start_at, end_at, location, presenter_id, description, status, created_by)
VALUES (:t_lab, '博士开题答辩预演', 'defense', '2026-09-15 09:00:00', '2026-09-15 12:00:00',
        '线下·管理学院B302（模拟答辩委员会）', :u_wang, '模拟博士开题答辩', 'upcoming', :u_yan)
RETURNING id INTO :m3;
INSERT INTO meeting_agenda_items (meeting_id, seq, time_slot, content, presenter_id) VALUES
  (:m3, 0, '09:00–10:30', '王五开题报告陈述与答辩', :u_wang),
  (:m3, 1, '10:30–11:30', '模拟评审委员提问', NULL),
  (:m3, 2, '11:30–12:00', '评委点评与修改意见', :u_yan);
INSERT INTO meeting_actions (meeting_id, content, owner_id, due_date, status, completed_at) VALUES
  (:m3, '按修改清单更新开题报告', :u_wang, '2026-09-16', 'open', NULL),
  (:m3, '填写预演评分表', NULL, '2026-09-15', 'open', NULL),
  (:m3, '预演会议记录', :u_qian, '2026-09-15', 'open', NULL);

-- 组会 4（文献报告 · 已结束）
INSERT INTO meetings (team_id, title, meeting_type, start_at, end_at, location, presenter_id, description, status, created_by)
VALUES (:t_lab, '第17次文献报告会', 'journal', '2026-09-02 19:00:00', '2026-09-02 21:00:00',
        '线上 + 管理学院B302', :u_qian, '本期文献综述', 'finished', :u_yan)
RETURNING id INTO :m4;
INSERT INTO meeting_agenda_items (meeting_id, seq, time_slot, content, presenter_id) VALUES
  (:m4, 0, '19:00–19:10', '报告人介绍与上期纪要回顾', :u_qian),
  (:m4, 1, '19:10–20:10', '文献报告：本期文献综述', :u_qian),
  (:m4, 2, '20:10–21:00', '讨论与任务安排', :u_zhao);
INSERT INTO meeting_actions (meeting_id, content, owner_id, due_date, status, completed_at) VALUES
  (:m4, '上传报告材料至存档', :u_qian, '2026-09-03', 'done', '2026-09-03 20:00:00'),
  (:m4, '下期（第18次）材料确认', :u_zhao, '2026-09-05', 'done', '2026-09-05 18:00:00');

-- 组会 5（进展汇报 · 已结束）
INSERT INTO meetings (team_id, title, meeting_type, start_at, end_at, location, presenter_id, description, status, created_by)
VALUES (:t_lab, '新学期研究方向规划会', 'progress', '2026-09-01 15:00:00', '2026-09-01 17:00:00',
        '线下·管理学院B302', :u_yan, '统筹本学期研究方向与资源', 'finished', :u_yan)
RETURNING id INTO :m5;
INSERT INTO meeting_agenda_items (meeting_id, seq, time_slot, content, presenter_id) VALUES
  (:m5, 0, '15:00–16:00', '各成员汇报本学期研究方向', NULL),
  (:m5, 1, '16:00–16:30', '彦教授统筹研究方向与资源分配', :u_yan),
  (:m5, 2, '16:30–17:00', '确定本学期组会轮值表', :u_qian);
INSERT INTO meeting_actions (meeting_id, content, owner_id, due_date, status, completed_at) VALUES
  (:m5, '提交个人学期计划', NULL, '2026-09-04', 'done', '2026-09-04 12:00:00'),
  (:m5, '排定本学期组会轮值表', :u_qian, '2026-09-04', 'done', '2026-09-04 18:00:00');

-- 组会 6（文献报告 · 已结束）
INSERT INTO meetings (team_id, title, meeting_type, start_at, end_at, location, presenter_id, description, status, created_by)
VALUES (:t_lab, '第16次文献报告会', 'journal', '2026-08-26 19:00:00', '2026-08-26 21:00:00',
        '线上', :u_zhao, '本期文献综述', 'finished', :u_yan)
RETURNING id INTO :m6;
INSERT INTO meeting_agenda_items (meeting_id, seq, time_slot, content, presenter_id) VALUES
  (:m6, 0, '19:00–19:10', '报告人介绍与上期纪要回顾', :u_zhao),
  (:m6, 1, '19:10–20:10', '文献报告：本期文献综述', :u_zhao),
  (:m6, 2, '20:10–21:00', '讨论与任务安排', :u_li);
INSERT INTO meeting_actions (meeting_id, content, owner_id, due_date, status, completed_at) VALUES
  (:m6, '纪要归档', :u_zhao, '2026-08-28', 'done', '2026-08-28 20:00:00');
