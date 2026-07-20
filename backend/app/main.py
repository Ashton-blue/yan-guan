from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api import auth, teams, members, audit, dashboard

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="研究室/团队管理系统",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(members.router)
app.include_router(audit.router)
app.include_router(dashboard.router)


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": settings.app_version}
