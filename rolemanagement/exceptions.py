class PermissionOrHierarchyException(Exception):
    pass


class MissingRequirementsException(Exception):
    def __init__(self, *args, miss_any=None, miss_all=None):
        self.miss_all = miss_all or []
        self.miss_any = miss_any or []


class ConflictingRoleException(Exception):
    def __init__(self, *args, conflicts=None):
        self.conflicts = conflicts or []
