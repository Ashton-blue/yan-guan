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


async def _rebuild_incompatible_empty_tables(conn):
    """结构自愈：批次 A 之前的遗留表结构与当前模型不一致时，把「空表」直接重建。

    背景：create_all 只建缺失的表，既不会给已存在的表补列，也不会改旧列名；
    而遗留表上常带有 NOT NULL 的旧列（如 teams.owner_id、team_members.joined_at），
    会直接挡掉 INSERT。

    安全边界（重要）：
    - 只处理行数为 0 的表，绝不 drop 任何有数据的表；
    - users 表有存量数据，永不重建，只走下面的列对齐/补列分支；
    - 若某空表的外键指向即将重建的表，则它一并重建（否则外键约束会随 CASCADE 丢失）。
    返回被重建的表名列表。
    """
    from sqlalchemy import text

    rows = (await conn.execute(text(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = 'public'"
    ))).fetchall()
    existing = {}
    for table_name, column_name in rows:
        existing.setdefault(table_name, set()).add(column_name)

    meta_tables = {t.name: t for t in Base.metadata.sorted_tables}
    to_rebuild = set()
    changed = True
    while changed:
        changed = False
        for name, table in meta_tables.items():
            if name == "users" or name not in existing or name in to_rebuild:
                continue
            missing = {c.name for c in table.columns} - existing[name]
            fk_affected = any(fk.column.table.name in to_rebuild for fk in table.foreign_keys)
            if not (missing or fk_affected):
                continue
            count = await conn.scalar(text(f'SELECT count(*) FROM "{name}"'))
            if count == 0:
                to_rebuild.add(name)
                changed = True

    if not to_rebuild:
        return []

    for name in reversed([t.name for t in Base.metadata.sorted_tables]):
        if name in to_rebuild:
            await conn.execute(text(f'DROP TABLE IF EXISTS "{name}" CASCADE'))

    return sorted(to_rebuild)


# 初始化数据库表
async def init_db():
    import app.models  # noqa: F401  确保全部模型已注册到 Base.metadata
    from sqlalchemy import text

    async with engine.begin() as conn:
        # 1) 结构自愈：遗留空表重建（仅空表，见函数内安全边界）
        rebuilt = await _rebuild_incompatible_empty_tables(conn)
        if rebuilt:
            print(f"[init_db] 已重建结构与模型不符的空表：{', '.join(rebuilt)}")

        # 2) 建齐缺失的表（含索引）
        await conn.run_sync(Base.metadata.create_all)

        # 3) users 表列对齐（有存量数据，只改名/放宽约束，不重建）
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
                -- 遗留的 NOT NULL 列会挡住 INSERT，放宽为可空
                IF EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='users' AND column_name='username'
                             AND is_nullable='NO') THEN
                    ALTER TABLE users ALTER COLUMN username DROP NOT NULL;
                END IF;
            END $$;
        """))

        # 4) 补批次 A 新增列 + email 唯一索引
        ensure_stmts = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS research_area VARCHAR(200)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active'",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email)",
        ]
        for stmt in ensure_stmts:
            await conn.execute(text(stmt))
