"""实现四维数据权限校验规则。"""

from collections.abc import Iterable, Sequence

from kb_manage_platform.domain.models import PermissionGrant, PermissionScope, UserContext


class PermissionValidationError(ValueError):
    """权限配置不合法。"""


# 作用：生成用于 FAQ 聚类分组的稳定权限签名。
def permission_signature(grants: Iterable[PermissionGrant]) -> str:
    """有任一全局授权即视为 global，否则返回受限权限类型摘要。"""
    normalized = tuple(grants)
    if any(grant.scope is PermissionScope.GLOBAL for grant in normalized):
        return "global"
    if not normalized:
        return "restricted"
    scopes = sorted({grant.scope.value for grant in normalized})
    return "restricted:" + ",".join(scopes)


class PermissionPolicy:
    """全局、部门、角色和个人权限的纯领域规则。"""

    # 作用：校验并规范化权限规则，去除重复项。
    def normalize(self, grants: Iterable[PermissionGrant]) -> tuple[PermissionGrant, ...]:
        """返回去重且稳定的权限规则。"""
        normalized: list[PermissionGrant] = []
        seen: set[tuple[PermissionScope, str, bool]] = set()
        for grant in grants:
            if not grant.subject_id and grant.scope is not PermissionScope.GLOBAL:
                raise PermissionValidationError("permission subject_id must not be empty")
            key = (grant.scope, grant.subject_id, grant.include_descendants)
            if key in seen:
                continue
            seen.add(key)
            normalized.append(grant)
        return tuple(normalized)

    # 作用：判断用户是否满足至少一条四维权限规则。
    def matches(self, user: UserContext, grants: Sequence[PermissionGrant]) -> bool:
        """按 OR 规则执行授权。"""
        if not user.is_active:
            return False
        for grant in grants:
            if self._matches_grant(user, grant):
                return True
        return False

    # 作用：判断单条权限规则是否命中。
    def _matches_grant(self, user: UserContext, grant: PermissionGrant) -> bool:
        """执行单条权限规则匹配。"""
        if grant.scope is PermissionScope.GLOBAL:
            return True
        if grant.scope is PermissionScope.USER:
            return grant.subject_id == user.user_id
        if grant.scope is PermissionScope.ROLE:
            return grant.subject_id in user.role_ids
        if grant.scope is PermissionScope.DEPARTMENT:
            if grant.subject_id == user.department_id:
                return True
            return grant.include_descendants and grant.subject_id in user.department_path
        return False