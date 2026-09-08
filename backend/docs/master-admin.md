# Master Admin boundary

Master Admin is a deployment-wide role backed by `User.is_superuser`. Django
`is_staff` alone is not sufficient. Organisation owners, admins, invigilators,
and candidates remain organisation-scoped roles.

Global endpoints use `/api/master-admin/` and require `IsMasterAdmin`.
Organisation administration remains under `/api/admin/` and uses the current
organisation membership permissions.

Master Admin endpoints:

- `GET /api/master-admin/status/` — safe deployment status.
- `GET /api/master-admin/organisations/` — global organisation summaries.
- `GET /api/master-admin/organisations/<id>/` — one organisation summary.
- `GET/PATCH /api/master-admin/settings/organisation-creation/` — read or change
  whether new organisations may be created.

`ORGANISATION_CREATION_ENABLED=True` is the deployment default. A Master Admin
change is stored in the database and is authoritative over that default until
changed again. Disabling creation affects only new organisation creation; it
does not affect existing memberships, organisation administration, switching,
or joining existing organisations by invitation or join code.
