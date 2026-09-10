from fastapi import APIRouter
from app.api.policy_qa import router as policy_qa_router
from app.api.template_management import router as template_router
from app.api.application_forms import router as application_forms_router
from app.api.ai_generation import router as ai_generation_router
from app.api.applications_reminders import router as reminders_router

# 合并所有政策相关路由
policies_router = APIRouter()

policies_router.include_router(policy_qa_router)
policies_router.include_router(template_router)
policies_router.include_router(application_forms_router)
policies_router.include_router(ai_generation_router)
policies_router.include_router(reminders_router)

__all__ = ["policies_router"]
