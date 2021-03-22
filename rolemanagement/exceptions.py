#   Copyright 2017-present Michael Hall
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

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
