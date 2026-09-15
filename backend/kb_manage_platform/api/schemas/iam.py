"""组织、账号、角色和认证 API 模型。"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class CurrentUserResponse(BaseModel):
    """当前登录用户资料。"""

    user_id: str
    username: str
    department_id: str
    role_ids: list[str]
    status: str
    permission_codes: list[str]


class TokenResponse(BaseModel):
    """登录令牌响应。"""

    access_token: str
    token_type: str
    expires_in: int
    user: CurrentUserResponse


class ChangePasswordRequest(BaseModel):
    """修改密码请求。"""

    current_password: str
    new_password: str = Field(..., min_length=8)


class DepartmentCreateRequest(BaseModel):
    """创建部门请求。"""

    name: str
    parent_id: str = ""
    sort_order: int = 0


class DepartmentUpdateRequest(BaseModel):
    """更新部门请求。"""

    name: str = ""
    parent_id: str = ""
    sort_order: int = 0


class StatusRequest(BaseModel):
    """通用状态请求。"""

    status: str


class UserCreateRequest(BaseModel):
    """创建用户请求。"""

    username: str
    password: str = Field(..., min_length=8)
    department_id: str
    role_ids: list[str] = Field(default_factory=list)


class AssignRolesRequest(BaseModel):
    """分配角色请求。"""

    role_ids: list[str]


class ResetPasswordRequest(BaseModel):
    """管理员重置密码请求。"""

    new_password: str = Field(..., min_length=8)


class RoleCreateRequest(BaseModel):
    """创建角色请求。"""

    name: str
    permission_codes: list[str] = Field(default_factory=list)


class SetPermissionsRequest(BaseModel):
    """设置角色权限请求。"""

    permission_codes: list[str]
