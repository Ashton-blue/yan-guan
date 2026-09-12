from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

# 导入路由
from app.api.auth import router as auth_router
from app.api.teams import router as teams_router
from app.api.members import router as members_router
from app.api.audit import router as audit_router
from app.api.dashboard import router as dashboard_router
from app.api.policies import policies_router
from app.api.users import router as users_router
from app.api.invites import router as invites_router
from app.api.meetings import router as meetings_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    from app.database import init_db
    await init_db()
    yield

app = FastAPI(
    title="研管系统 API",
    description="研究室管理系统 - Batch-1 + P1阶段1.3 + P0批次A(账户/会议管理)",
    version="1.4.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router, prefix="/api/v1", tags=["认证"])
app.include_router(teams_router, prefix="/api/v1", tags=["团队管理"])
app.include_router(members_router, prefix="/api/v1", tags=["成员管理"])
app.include_router(audit_router, prefix="/api/v1", tags=["审计日志"])
app.include_router(dashboard_router, prefix="/api/v1", tags=["仪表盘"])
app.include_router(policies_router, prefix="/api/v1", tags=["政策助手"])
# P0 批次 A：账户管理 / 团队邀请 / 组会管理
app.include_router(users_router, prefix="/api/v1", tags=["账户管理"])
app.include_router(invites_router, prefix="/api/v1", tags=["团队邀请"])
app.include_router(meetings_router, prefix="/api/v1", tags=["组会管理"])

@app.get("/")
async def root():
    return {"message": "研管系统 API v1.4.0", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
