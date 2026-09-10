-- ============================================================
-- 研管 P0 批次 A 迁移脚本（PostgreSQL）
-- 用途：在「已部署」环境上升级数据库结构（账户管理 + 会议管理）
-- 说明：全新部署请直接运行根目录 init.sql（已包含本脚本全部 DDL + 种子数据）
-- 幂等：使用 IF NOT EXISTS / ADD COLUMN IF NOT EXISTS，可重复执行
-- ============================================================

-- 1) users 扩展个人资料字段（账户管理）
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS research_area VARCHAR(200);
ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';

-- 2) 团队邀请码（账户管理 · 团队与成员）
CREATE TABLE IF NOT EXISTS team_invites (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
    code VARCHAR(64) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'student',
    invited_by INTEGER REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active/used/expired
    used_by INTEGER REFERENCES users(id),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_team_invites_team ON team_invites(team_id);
CREATE INDEX IF NOT EXISTS idx_team_invites_code ON team_invites(code);

-- 3) 组会（会议管理）
CREATE TABLE IF NOT EXISTS meetings (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    meeting_type VARCHAR(20) NOT NULL,              -- journal/progress/defense
    start_at TIMESTAMP NOT NULL,
    end_at TIMESTAMP,
    location VARCHAR(200),
    presenter_id INTEGER REFERENCES users(id),
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'upcoming',  -- upcoming/finished/cancelled
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_meetings_team ON meetings(team_id);
CREATE INDEX IF NOT EXISTS idx_meetings_type ON meetings(team_id, meeting_type);
CREATE INDEX IF NOT EXISTS idx_meetings_start ON meetings(start_at);

-- 4) 组会议程（有序）
CREATE TABLE IF NOT EXISTS meeting_agenda_items (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER REFERENCES meetings(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL DEFAULT 0,
    time_slot VARCHAR(50),
    content VARCHAR(300) NOT NULL,
    presenter_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_meeting_agenda_meeting ON meeting_agenda_items(meeting_id);

-- 5) 组会行动项
CREATE TABLE IF NOT EXISTS meeting_actions (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER REFERENCES meetings(id) ON DELETE CASCADE,
    content VARCHAR(300) NOT NULL,
    owner_id INTEGER REFERENCES users(id),
    due_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'open',     -- open/done/cancelled
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_meeting_actions_meeting ON meeting_actions(meeting_id);
CREATE INDEX IF NOT EXISTS idx_meeting_actions_owner ON meeting_actions(owner_id);
