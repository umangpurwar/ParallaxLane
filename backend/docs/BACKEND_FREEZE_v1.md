# Backend Freeze v1

Branch `backend-freeze-v1`. This pass fixes every Critical, High and Medium finding from the security audit and adds the server side of the Android hardening plan. App-facing behaviour is specified in `ANDROID_API_CONTRACT_v1.md`.

**Test suite:** `python manage.py test tests` gives **45 tests, all passing**, on Postgres 16 and Redis 7 with Django 5.2.17. The two rate-limit/outage claims were also negative-controlled: the tests fail when the fix is reverted.

## What changed (by audit ID)

| ID | Fix | Where |
|---|---|---|
| C-1 | Questions only during the caller's own active attempt, on the bound device; shuffled per attempt | `exams/views.py` `ExamDetailView` |
| C-2 | `@ratelimit` moved under `@api_view` (per-user buckets) | `admin_panel/views.py`, monitoring now uses class views |
| C-3 | `ssl_cert_reqs` only for `rediss://` (default `required`); `RATELIMIT_FAIL_OPEN=True` | `core/settings.py` |
| H-1 | Login keyed by email (10/min) plus a generous IP limit (100/min); configurable proxy IP trust | `accounts/views.py`, `core/ratelimit.py` |
| H-2 | `finalize_attempt()` grades every exit path; 10s submit grace; deadline expiry = `completed` + `deadline_expired` | `exams/services.py` |
| H-3 | Questions locked once any attempt exists; `Answer.question` → RESTRICT; `AttemptEvent.question` → SET_NULL | `exams/serializers.py`, migrations |
| H-4 | `Ratelimited` → 429 `rate_limited`; machine-readable `code` on exam, monitoring and device errors | `core/exceptions.py` |
| H-5 | Device registration (TOFU + admin approval), Keystore-signed start challenge, Play Integrity at start and via heartbeat, server-side heartbeat gap detection, min-app-version gate | `core/devices.py`, `core/integrity.py`, `accounts/device_views.py`, `organisations/device_admin_views.py`, `core/middleware.py` |
| M-1 | 256 KB body cap, metadata whitelist, 5000-char answers; live monitor reads heartbeat state | settings, `monitoring/services.py` |
| M-2 | CSV formula injection neutralised | `admin_panel/report_export.py` |
| M-3 | `User.email_verified`; deactivated accounts can't re-register via OTP | `accounts` |
| M-4 | Existing users get a pending invite (inbox + accept), no force-add; invites rate-limited 30/h, default 7-day expiry; org names restricted (no dots/URLs) | `organisations` |
| M-5 | Exam-row lock removed from start and submit; gunicorn gthread (3×4) | views, `dockerfile`, compose |
| M-6 | Django 5.2 LTS; every dependency pinned | `requirements.txt` |
| M-7 | Postgres and Redis ports unpublished; no source bind-mount; nginx forwards the original scheme | `docker-compose.yml`, `frontend/nginx.conf` |
| L-1 | No user enumeration in OTP verification or inactive-account login | `accounts` |
| L-3 | Production refuses `EMAIL_PROVIDER=console` | settings |
| L-4 | Invite default expiry 7 days | `organisations/views.py` |
| L-5 | Exam/question validation (time window, violation limit 1–100, MCQ/TF correctness, point caps) | `exams/serializers.py` |
| L-6 | Start requires `is_published` | `exams/views.py` |
| L-7 | `violations_cleared` audit event with the admin's id and previous counts | `admin_panel/views.py` |
| L-9 | Org slug race retried | `organisations/views.py` |
| (new) | `IntegrityError` inside start's atomic block poisoned the transaction; now isolated in a savepoint | `exams/views.py` |

## Migrations (apply in order, all additive)

- `accounts.0010` adds `email_verified` and `UserDevice`.
- `accounts.0011` backfills `email_verified=True` for active users.
- `exams.0012` adds `device`, `last_client_state` and `end_reason` to the attempt, and makes `Answer.question` RESTRICT.
- `attempt_events.0003` adds the new event type and makes the question FK SET_NULL.

## New environment variables

| Var | Default | Production value |
|---|---|---|
| `DEVICE_REQUIRED_FOR_EXAMS` | `True` | `True` (set `False` only to keep the old web candidate flow) |
| `INTEGRITY_REQUIRED` | `False` | `True` once the app is on a Play track and the two settings below are set |
| `PLAY_INTEGRITY_PACKAGE` | `""` | your applicationId |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | `""` | path to the service-account JSON (Play Integrity API enabled, linked in Play Console) |
| `MIN_ANDROID_APP_VERSION` | `1` | bump to force updates |
| `TRUST_PROXY_IP_HEADER` | `False` | `True` only if Django is reachable *only* through your proxy |
| `RATELIMIT_FAIL_OPEN` | `True` | keep |
| `HEARTBEAT_GAP_SECONDS` / `SUBMIT_GRACE_SECONDS` / `START_CHALLENGE_TTL_SECONDS` | 25 / 10 / 120 | keep |
| `REDIS_SSL_CERT_REQS` | `required` | keep (`none` only if your provider forces it) |

## Behaviour changes to know

- **The Vue candidate exam flow stops working** while `DEVICE_REQUIRED_FOR_EXAMS=True`: it can't send a device key. Admin, invigilator and org pages still work. This is intentional; candidates use the app.
- Vue's violation types `no_face` and `suspicious_movement` are still rejected, as before.
- Admin exam creation now rejects invalid exams (see L-5). Existing rows are untouched.
- The invite response for existing users is now `"invite created"`, not `"user added directly"`.
- A deadline auto-submit is reported as `Completed` (with `end_reason`), no longer `Terminated`.

## Not verified / not done (honest list)

- **Play Integrity against real Google.** The verdict evaluation and failure paths are unit-tested with mocked payloads in Google's documented format. Test a real token from your internal-testing track before setting `INTEGRITY_REQUIRED=True`.
- **Load behaviour (M-5).** The lock removal and worker change are reasoned, not measured. Run `loadtests/locustfile.py` against a staging box before the first real exam.
- **Deployment TLS chain.** The nginx scheme passthrough is correct by construction, but I haven't seen your host. Confirm there's no redirect loop on first deploy.
- **Accepted limits:**
  - Device re-keying on the same `device_id` is automatic, so someone who can read the app's traffic (root plus TLS-pinning bypass) could re-key. `INTEGRITY_REQUIRED=True` is the control for that.
  - The OTP lockout is per email, so it can be used to lock a specific student out of OTP login for 15 minutes. Password login still works.
  - `/admin/` (Django admin) should be IP-restricted at your proxy.
- **Repo hygiene:** the root `requirements.txt` is an unrelated UTF-16 pip freeze (jupyter, lightgbm, Django 6). Delete it, or make sure no deploy uses it.
