"""聚合 API 子路由。"""

from fastapi import APIRouter

from kb_manage_platform.api.routes.audit import router as audit_router
from kb_manage_platform.api.routes.auth import router as auth_router
from kb_manage_platform.api.routes.categories import router as categories_router
from kb_manage_platform.api.routes.configuration import router as configuration_router
from kb_manage_platform.api.routes.dashboard import router as dashboard_router
from kb_manage_platform.api.routes.departments import router as departments_router
from kb_manage_platform.api.routes.faq_gap import router as faq_gap_router
from kb_manage_platform.api.routes.health import router as health_router
from kb_manage_platform.api.routes.import_ import router as import_router
from kb_manage_platform.api.routes.knowledge import router as knowledge_router
from kb_manage_platform.api.routes.query import router as query_router
from kb_manage_platform.api.routes.roles import router as roles_router
from kb_manage_platform.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(audit_router)
api_router.include_router(departments_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(knowledge_router)
api_router.include_router(categories_router)
api_router.include_router(configuration_router)
api_router.include_router(query_router)
api_router.include_router(import_router)
api_router.include_router(faq_gap_router)
api_router.include_router(dashboard_router)
