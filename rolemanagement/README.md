# RoleManagement

This is not a complete reference of the cog at this time.

## FAQ

### Why are exclusive roles not allowing users to switch roles?

At the current time, rolemanagement does *exactly* what you tell it to do.

If a user can't remove a role under settings from roleset, it will not let them
switch roles to remove a role.

### Does rolemanagement work with other cogs?

It doesn't break other cogs. This distinction is a little important. Rolemanagement
will not take actions based on anything it does not own. The means if another cog
violates the settings in rolemanagement, rolemanagement won't do anything about it.

This is intentional to prevent API loops with multiple cogs fighting eachother.
