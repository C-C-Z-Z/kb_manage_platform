"""统一提供 FastAPI 服务依赖。"""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from kb_manage_platform.bootstrap.container import Container
from kb_manage_platform.common.errors import AuthenticationError, AuthorizationError
from kb_manage_platform.domain.models import UserContext
from kb_manage_platform.services.account_service import AccountService
from kb_manage_platform.services.audit_service import AuditService
from kb_manage_platform.services.auth_service import AuthService
from kb_manage_platform.services.category_service import CategoryService
from kb_manage_platform.services.configuration_service import ConfigurationService
from kb_manage_platform.services.dashboard_service import DashboardService
from kb_manage_platform.services.faq_gap_service import FaqGapService
from kb_manage_platform.services.import_service import ImportService
from kb_manage_platform.services.knowledge_service import KnowledgeService
from kb_manage_platform.services.organization_service import OrganizationService
from kb_manage_platform.services.query_service import QueryService
from kb_manage_platform.services.role_service import RoleService


# 作用：从应用状态获取统一依赖容器。
def get_container(request: Request) -> Container:
    """返回应用组合根。"""
    return request.app.state.container


# 作用：注入知识服务。
def get_knowledge_service(container: Annotated[Container, Depends(get_container)]) -> KnowledgeService:
    """返回知识服务。"""
    return container.knowledge_service


# 作用：注入模型与系统配置服务。
def get_configuration_service(
    container: Annotated[Container, Depends(get_container)],
) -> ConfigurationService:
    """返回配置服务。"""
    return container.configuration_service


ConfigurationServiceDep = Annotated[ConfigurationService, Depends(get_configuration_service)]


# 作用：注入审计查询服务。
def get_audit_service(container: Annotated[Container, Depends(get_container)]) -> AuditService:
    """返回审计查询服务。"""
    return container.audit_service


AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]


# 作用：注入知识分类服务。
def get_category_service(container: Annotated[Container, Depends(get_container)]) -> CategoryService:
    """返回知识分类服务。"""
    return container.category_service


CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]


# 作用：注入问答服务。
def get_query_service(container: Annotated[Container, Depends(get_container)]) -> QueryService:
    """返回问答服务。"""
    return container.query_service


# 作用：注入入库服务。
def get_import_service(container: Annotated[Container, Depends(get_container)]) -> ImportService:
    """返回入库服务。"""
    return container.import_service


KnowledgeServiceDep = Annotated[KnowledgeService, Depends(get_knowledge_service)]
QueryServiceDep = Annotated[QueryService, Depends(get_query_service)]


def get_dashboard_service(
    container: Annotated[Container, Depends(get_container)],
) -> DashboardService:
    """返回看板服务。"""
    return container.dashboard_service


DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]
ImportServiceDep = Annotated[ImportService, Depends(get_import_service)]


# 作用：注入 FAQ/知识缺口服务。
def get_faq_gap_service(container: Annotated[Container, Depends(get_container)]) -> FaqGapService:
    """返回 FAQ/知识缺口服务。"""
    return container.faq_gap_service


FaqGapServiceDep = Annotated[FaqGapService, Depends(get_faq_gap_service)]

bearer_scheme = HTTPBearer(auto_error=False)


# 作用：注入认证服务。
def get_auth_service(container: Annotated[Container, Depends(get_container)]) -> AuthService:
    """返回认证服务。"""
    return container.auth_service


# 作用：解析 Bearer 令牌并加载当前用户权限上下文。
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserContext:
    """返回当前登录用户。"""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("bearer token required")
    return await service.authenticate(credentials.credentials)


# 作用：生成指定操作权限的 FastAPI 依赖。
def require_permission(permission_code: str):
    """返回权限校验依赖函数。"""

    # 作用：校验当前用户是否拥有目标操作权限。
    async def checker(user: Annotated[UserContext, Depends(get_current_user)]) -> UserContext:
        """返回有权限的用户。"""
        if permission_code not in user.permission_codes:
            raise AuthorizationError(f"permission required: {permission_code}")
        return user

    return checker


# 作用：注入组织服务。
def get_organization_service(container: Annotated[Container, Depends(get_container)]) -> OrganizationService:
    """返回组织服务。"""
    return container.organization_service


# 作用：注入账号服务。
def get_account_service(container: Annotated[Container, Depends(get_container)]) -> AccountService:
    """返回账号服务。"""
    return container.account_service


# 作用：注入角色服务。
def get_role_service(container: Annotated[Container, Depends(get_container)]) -> RoleService:
    """返回角色服务。"""
    return container.role_service


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CurrentUserDep = Annotated[UserContext, Depends(get_current_user)]
KnowledgeReadUserDep = Annotated[UserContext, Depends(require_permission("knowledge:read"))]
KnowledgeCreateUserDep = Annotated[UserContext, Depends(require_permission("knowledge:create"))]
KnowledgeUpdateUserDep = Annotated[UserContext, Depends(require_permission("knowledge:update"))]
KnowledgePublishUserDep = Annotated[UserContext, Depends(require_permission("knowledge:publish"))]
KnowledgeDisableUserDep = Annotated[UserContext, Depends(require_permission("knowledge:disable"))]
KnowledgePermissionUserDep = Annotated[UserContext, Depends(require_permission("knowledge:permission:manage"))]
KnowledgeDownloadUserDep = Annotated[UserContext, Depends(require_permission("knowledge:download"))]
ImportCreateUserDep = Annotated[UserContext, Depends(require_permission("import:create"))]
ImportReadUserDep = Annotated[UserContext, Depends(require_permission("import:read"))]
QueryUserDep = Annotated[UserContext, Depends(require_permission("qa:use"))]
SessionReadUserDep = Annotated[UserContext, Depends(require_permission("qa:session:read"))]
DashboardUserDep = Annotated[UserContext, Depends(require_permission("dashboard:read"))]
AuditReadUserDep = Annotated[UserContext, Depends(require_permission("audit:read"))]
AuditExportUserDep = Annotated[UserContext, Depends(require_permission("audit:export"))]
ModelManageUserDep = Annotated[UserContext, Depends(require_permission("model:manage"))]
SystemManageUserDep = Annotated[UserContext, Depends(require_permission("system:manage"))]
FaqManageUserDep = Annotated[UserContext, Depends(require_permission("faq:manage"))]
GapManageUserDep = Annotated[UserContext, Depends(require_permission("gap:manage"))]
OrganizationServiceDep = Annotated[OrganizationService, Depends(get_organization_service)]
AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]
RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]




