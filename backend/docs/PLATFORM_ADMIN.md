# Platform administration: roles, approval and admin APIs

## Roles (enforced on the server)

| Role | How it is identified | Can do |
|---|---|---|
| Super admin | Django `is_superuser`, created only by `python manage.py create_superadmin` | Review, approve, reject, suspend and reactivate organisations; platform stats; audit log; open or close applications |
| Organisation owner / admin | Active `OrganisationMember` with role `owner`/`admin` in an **approved** organisation | Overview, profile, invites, members, join code, devices, exams, results, organisation audit log |
| Member (candidate, invigilator) | Active membership in an approved organisation | Android app exam flow (contract v1), invigilators: live monitor |

The super admin and Django staff accounts can never own or join an organisation.
Roles are never read from request bodies or token claims; every check loads the
account, membership and organisation status from the database.

## Organisation lifecycle

```
apply (create/) ──> pending ──approve──> approved ──suspend──> suspended
                       │                     ^                     │
                       └──reject──> rejected └─────reactivate──────┘
                                       │
                         owner edits + resubmit ──> pending
```

- `Organisation.is_active` is derived from `status == approved` in `save()`. Every
  member and admin endpoint filters on it, so pending, rejected and suspended
  organisations cannot invite, join, create exams or run exams.
- One pending application per owner (database constraint) and one live
  organisation per case-insensitive name (database constraint).
- A rejected applicant cannot open a new application; they edit and resubmit the
  same record, which goes back to the super admin.
- Suspension ends running exam attempts immediately (saved answers are graded,
  `end_reason = organisation_suspended`) and blocks tokens issued earlier,
  because access is checked on every request.
- Reject and suspend require a reason; it is shown to the owner.

## Endpoints added

Super admin (`/api/master-admin/`): `stats/`, `organisations/?status=&search=&ordering=&page=`,
`organisations/<id>/`, `organisations/<id>/<approve|reject|suspend|reactivate>/` (body `{note}`),
`audit-logs/?organisation=&action=&search=&page=`, `settings/organisation-creation/`.

Applicant: `POST organisations/create/` (now creates a pending application, 201),
`GET organisations/applications/mine/`, `PATCH organisations/applications/<id>/`,
`POST organisations/applications/<id>/resubmit/`.

Organisation admin (`/api/organisations/<slug>/`): `overview/`, `profile/` (PATCH, name
locked after approval), `invites/?status=&search=&page=`, `invites/<id>/revoke/`,
`members/<id>/<activate|deactivate>/`, `audit-logs/`. Existing: `invite/`, `members/`,
`members/<id>/toggle-exam-access/`, `join-code/`, `devices/`, and the exam endpoints
under `/api/admin/`.

Any signed-in user: `GET accounts/me/`, `POST organisations/invites/decline/` (body `{code}`).

## Android compatibility

No Android endpoint, payload or response changed. Members of an organisation
that is not approved now receive `403 {"code": "organisation_unavailable"}` on
exam endpoints; the student app already shows the server message for 403s.

## Provisioning the super admin

```
SUPERADMIN_EMAIL=you@yourdomain SUPERADMIN_PASSWORD='<long random>' python manage.py create_superadmin
```

Idempotent. It refuses to promote an existing ordinary account unless run with
`--promote-existing`, and refuses accounts that belong to an organisation.
`--reset-password` changes the password of the existing super admin.
