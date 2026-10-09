# ParallaxLane admin dashboard

Vue 3 + Vite + Tailwind CSS. One login for every administrator. The panel that
opens is chosen from `GET /api/accounts/me/`, and every action is authorised
again by the backend.

## Screens

| Area | Routes | Backend |
|---|---|---|
| Sign in, create account, reset password | `/login`, `/register`, `/reset-password` | `login/`, `accounts/send-otp/`, `accounts/verify-otp-*` |
| Organisation application | `/apply`, `/application` | `organisations/create/`, `organisations/applications/*` |
| Super admin | `/platform`, `/platform/organisations[/:id]`, `/platform/audit` | `master-admin/*` |
| Organisation admin | `/org/:slug` and `exams`, `members`, `invitations`, `devices`, `settings`, `audit` | `organisations/<slug>/*`, `admin/*` |

## Code layout

```
src/api/client.js      axios instance: token header, one shared refresh, error normalising
src/api/endpoints.js   every backend call, grouped by area
src/stores/session.js  signed in account (from /accounts/me/) and where to send it
src/stores/toast.js    notifications
src/router/index.js    routes and guards (also switches the backend's current organisation)
src/components/        layout, tables, dialogs, badges shared by all pages
src/views/             one file per page
```

## Configuration

`VITE_API_BASE_URL` is the backend URL, ending with `/api/`:
- **Same domain** (nginx in `Dockerfile` proxies `/api/`): `/api/`.
- **Separate API domain:** `https://api.example.com/api/`. Also add the dashboard origin to the backend's `CORS_ALLOWED_ORIGINS`, and add the API origin to the `connect-src` line in `nginx.conf`.

It is baked in at build time and is not a secret.

## Sessions

Access and refresh tokens are kept in `sessionStorage`. They survive a reload, are gone when the tab closes, and are never sent anywhere except the API.

When the access token expires, one refresh runs and every waiting request retries with the new token. If the refresh fails, the user is returned to the sign in page.

## Commands

```bash
npm ci
npm run dev       # dev server with /api proxy to 127.0.0.1:8000
npm run build     # production bundle in dist/
npm test          # unit tests
```
