# ParallaxLane

Online exams on Android with a server that decides everything: who may take an
exam, when it ends, and the score.

| Part | Folder | Stack | Who uses it |
|---|---|---|---|
| Backend API | `backend/` | Django 5.2, Django REST Framework, PostgreSQL, Redis | The Android app and the dashboard |
| Admin dashboard | `frontend/` | Vue 3, Vite, Tailwind CSS, axios | Super admin and organisation admins |
| Android app | separate project | Java, Retrofit | Candidates (contract: `backend/docs/ANDROID_API_CONTRACT_v1.md`) |

## How the pieces fit

```
Android app ──┐                                   ┌── PostgreSQL
              ├── HTTPS ──> Django REST API ───────┤
Dashboard ────┘   (/api/)                          └── Redis (rate limits, OTP lockout)
```

**Roles, all enforced by the backend:**
- **Super admin:** created by a management command. Approves, rejects, suspends and reactivates organisations, sets plans, and reads the platform audit log.
- **Organisation owner or admin:** manages one approved organisation: exams, members, invitations, phone approvals, join code and audit log.
- **Member (candidate or invigilator):** takes exams in the Android app.

**How an organisation gets access:** an organisation applies, a super admin approves it, and only then can it invite people or run exams. Details are in `backend/docs/PLATFORM_ADMIN.md`.

## Run locally

Requirements: Python 3.12, PostgreSQL 16, Redis 7, Node.js 22.

1. **Start the backend:**
   ```bash
   cd backend
   cp .env.example .env            # edit DB_* if needed
   python -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   python manage.py migrate
   SUPERADMIN_EMAIL=you@example.com SUPERADMIN_PASSWORD='a-long-password' python manage.py create_superadmin
   python manage.py runserver 0.0.0.0:8000
   ```
2. **Start the dashboard** in a second terminal:
   ```bash
   cd frontend
   cp .env.example .env            # VITE_API_BASE_URL=/api/ uses the dev proxy
   npm ci
   npm run dev                     # http://localhost:5173
   ```
3. **Try the full flow:**
   - Sign in as the super admin.
   - In another browser, create an account under "Create an account". Locally the code is printed in the backend terminal.
   - Apply for an organisation with that account.
   - Approve it as the super admin.
   - Sign in again as the applicant: the organisation dashboard opens.

The whole stack also runs in Docker: `cd backend && docker compose up --build`. The API is on port 8000 and the dashboard on port 5173.

## Tests

```bash
cd backend && python manage.py test tests        # 75 API tests: security, isolation, exam flow
cd frontend && npm test                          # client and routing unit tests
# Live end to end check of the dashboard API layer against a running backend:
cd frontend && E2E_API_BASE=http://127.0.0.1:8000/api/ E2E_SUPERADMIN_EMAIL=... \
  E2E_SUPERADMIN_PASSWORD=... E2E_MAIL_LOG=/path/to/backend-stdout.log npx vitest run tests/e2e
```

## Deploy

See `docs/DEPLOYMENT.md`.

## Documentation

- `backend/docs/PLATFORM_ADMIN.md`: roles, organisation lifecycle, admin endpoints
- `backend/docs/ANDROID_API_CONTRACT_v1.md`: the frozen contract the Android app uses
- `backend/docs/BACKEND_FREEZE_v1.md`: security fixes and exam hardening
- `frontend/README.md`: dashboard structure
