from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# 创建会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# 基础模型类
Base = declarative_base()

# 依赖项：获取数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# 初始化数据库表
async def init_db():
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 幂等自修复：create_all 既不会给「已存在」的表补新列，也不会改旧列名。
        # Zeabur 线上是 Batch-1 遗留表（users 0 行），启动时把 users 对齐到当前模型，
        # 保证新环境/旧环境都能一次启动即可用（可重复执行，无副作用）。
        await conn.execute(text("""
            DO $$
            BEGIN
                -- 旧列名对齐：password_hash -> hashed_password
                IF EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='users' AND column_name='password_hash')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='users' AND column_name='hashed_password') THEN
                    ALTER TABLE users RENAME COLUMN password_hash TO hashed_password;
                END IF;
                -- 旧列名对齐：display_name -> name
                IF EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='users' AND column_name='display_name')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='users' AND column_name='name') THEN
                    ALTER TABLE users RENAME COLUMN display_name TO name;
                END IF;
                -- Batch-1 遗留的 NOT NULL 列会挡住 INSERT，放宽为可空
                IF EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='users' AND column_name='username'
                             AND is_nullable='NO') THEN
                    ALTER TABLE users ALTER COLUMN username DROP NOT NULL;
                END IF;
            END $$;
        """))
        # 补 P0 批次 A 新增列 + email 唯一索引
        ensure_stmts = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS research_area VARCHAR(200)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active'",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email)",
        ]
        for stmt in ensure_stmts:
            await conn.execute(text(stmt))
