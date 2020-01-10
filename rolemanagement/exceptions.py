from __future__ import annotations


class RoleManagementException(Exception):
    pass


class PermissionOrHierarchyException(Exception):
    pass


class MissingRequirementsException(RoleManagementException):
    def __init__(self, *, miss_any=None, miss_all=None):
        self.miss_all = miss_all or []
        self.miss_any = miss_any or []
        super().__init__()


class ConflictingRoleException(RoleManagementException):
    def __init__(self, *, conflicts=None):
        self.conflicts = conflicts or []
        super().__init__()
