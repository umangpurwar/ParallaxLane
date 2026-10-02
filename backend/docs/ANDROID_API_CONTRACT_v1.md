# ParallaxLane — Android API Contract v1 (frozen)

Base URL: `https://<your-api-host>/api/`. All bodies are JSON. Times are ISO-8601 UTC.

This contract is frozen. Backend changes after this point may **add** optional fields or endpoints. They must not rename or remove anything listed here or change its meaning. A breaking change requires a v2 document plus a `MIN_ANDROID_APP_VERSION` bump.

---

## 1. Headers on every request

| Header | Value | Notes |
|---|---|---|
| `Authorization` | `Bearer <access>` | Every endpoint except the auth endpoints in §3. |
| `X-Client` | `android` | Enables the version gate. |
| `X-App-Version` | integer `versionCode` | Below the server minimum, every call returns **426** `{"code":"app_update_required","min_version":N}`. Show a blocking "Update the app" screen. |
| `X-Device-Id` | 64-char lowercase hex | `SHA-256(ANDROID_ID)`, computed on the phone. The raw ANDROID_ID is never sent. Required on every **exam** and **monitoring** endpoint. |

## 2. Error handling rules

Exam, monitoring and device endpoints return:
```json
{"error": "human readable", "code": "machine_code", ...extra}
```
- Branch on `code`, never on the HTTP status alone. A 403 can mean `access_disabled`, `device_not_approved`, `exam_disabled` and more.
- **429** `rate_limited` comes with `Retry-After: 60`. Back off and retry. **It never means termination.**
- Termination is only `code` = `attempt_terminated`, or `state` = `terminated` in a response.
- Auth and organisation endpoints mostly return `{"error": "..."}` without a code, or DRF field errors (`{"field": ["msg"]}` / `{"non_field_errors": [...]}`). Show the message.

| code | Meaning | App action |
|---|---|---|
| `rate_limited` | Too many requests | Wait `Retry-After`, retry |
| `device_not_approved` | Header missing, unknown device, or pending device | Go to device registration / waiting screen |
| `device_mismatch` | Attempt started on another device | Show error; the admin must handle it |
| `device_change_during_exam` | Device change refused during an active attempt | Finish the exam first |
| `access_disabled` | Admin disabled exam access for this member | Show message |
| `exam_not_found` / `exam_disabled` / `exam_not_started` / `exam_window_closed` | Exam state | Show message (`exam_not_started` includes `start_time` and `server_time`) |
| `already_attempted` | One attempt per exam | Go to results |
| `challenge_invalid` | Nonce missing, expired or reused | Request a new challenge |
| `signature_invalid` | Keystore signature failed | Re-register the device key |
| `integrity_failed` | Play Integrity verdict failed (`reason` included) | Show "device not supported" |
| `integrity_unavailable` | Google unreachable (503) | Retry with backoff |
| `attempt_not_found` | Bad or foreign attempt id | Reset local state |
| `attempt_ended` | Attempt already finished (deadline auto-submit or submitted) | Go to results |
| `attempt_terminated` | Ended by violations or by an admin | Go to results |
| `invalid_question` / `invalid_answer` / `invalid_request` | Client bug or bad input | Log it; show message |
| `invalid_violation_type` | Unknown violation type | Client bug |
| `app_update_required` | 426 | Force update |

---

## 3. Auth (no `Authorization` header)

| Method / path | Body | Success |
|---|---|---|
| `POST login/` | `{email, password}` | `{access, refresh, email, display_name, org_slug, org_name, org_plan, org_role}` (org fields may be null) |
| `POST token/refresh/` | `{refresh}` | `{access, refresh}`: **the refresh token rotates and the old one is blacklisted** |
| `POST accounts/send-otp/` | `{email, mode: "login"\|"register"\|"forgot"}` | `{status: "If eligible, an OTP was sent"}`, always the same text |
| `POST accounts/verify-otp/` | `{email, otp}` | Same shape as login |
| `POST accounts/verify-otp-register/` | `{email, otp, name, password}` | Same shape as login, plus `message` |
| `POST accounts/verify-otp-forgot/` | `{email, otp, password}` | `{message}`; all refresh tokens are revoked |
| `POST accounts/logout/` (auth) | `{refresh}` | `{status: "logged out"}` |

Rate limits (per email unless stated):
- login: 10/min, plus 100/min per IP;
- send-otp: 3/min;
- verify: 5/min;
- 5 wrong OTPs lock that email's OTP flows for 15 minutes.

**Token refresh rule (important):** access tokens live 30 minutes and refresh tokens rotate. Refresh **single-flight**: one synchronized OkHttp `Authenticator`, so two parallel 401s don't both refresh. A second refresh with an already-used token fails and logs the student out mid-exam. Refresh proactively before calling the start challenge.

## 4. Organisations (auth)

| Method / path | Body | Success |
|---|---|---|
| `GET organisations/my/` | | `{count, organisations: [{name, slug, role, plan, ...}]}` |
| `POST organisations/<slug>/switch/` | | `{status: "switched", slug, ...}`. The current org is stored server-side and **shared with the web session**. |
| `POST organisations/join-by-code/` | `{code}` | `{organisation_id, organisation_name}` |
| `GET organisations/invites/` | | `[{token, org_name, org_slug, role, expires_at}]`: invites waiting for acceptance |
| `POST organisations/join/` | `{code: <invite token>}` | `{status: "joined", org_slug, org_name, org_plan, org_role}` |

Invites sent to an existing account are **not** auto-accepted. Show the `invites/` inbox and let the user accept.

## 5. Device registration (auth)

| Method / path | Body | Success |
|---|---|---|
| `POST accounts/devices/register/` | `{device_id, public_key, model_name}` | Device object |
| `GET accounts/devices/me/` | | `[Device]` (revoked devices omitted) |

`Device = {id, device_id, model_name, status: "approved"|"pending", pending_reason: ""|"device_change"|"shared_device", created_at, approved_at, last_seen}`

- `device_id` is `SHA-256(ANDROID_ID)` as hex.
- `public_key` is `Base64(KeyPair.getPublic().getEncoded())` of an **EC P-256** key generated in the Android Keystore with `PURPOSE_SIGN`.
- **Rules:**
  - The first device on an account is approved automatically.
  - Reinstalling on the same phone (same `device_id`, new key) re-keys automatically and stays approved.
  - A new phone, or a phone already approved for another account, stays `pending` until an org admin approves it.
  - Nothing can change while the user has an active attempt (`device_change_during_exam`).
- Register on every app start after login. It's idempotent and repairs the key after a reinstall.
- **Admin side** (web, org owner/admin): `GET organisations/<slug>/devices/?status=pending`, `POST organisations/<slug>/devices/<id>/approve/` or `.../revoke/`. Approving revokes the user's previous approved device.

## 6. Exams (auth + `X-Device-Id` where marked ●)

### `GET exams/`
Paginated: `{count, next, previous, results: [{id, title, description, duration, start_time, end_time, is_active}]}`.

### ● `GET exams/<id>/`
Metadata always. Questions **only** during your own active attempt on this device:
```json
{"id":1,"title":"...","description":"...","duration":30,"start_time":"...","end_time":"...",
 "is_active":true,"server_time":"...","questions":null}
```
During an attempt it also includes `attempt_id`, `deadline`, and
`questions: [{id, text, question_type, points, order, image, options:[{id,text}]}]`.
Order is shuffled per attempt but stable across calls. Correct answers are never included.

### ● `POST exams/<id>/challenge/` → start step 1
```json
{"nonce":"...","sign_payload":"parallaxlane-start:<exam_id>:<nonce>",
 "integrity_request_hash":"<sha256 hex of nonce>","expires_in":120,"integrity_required":false}
```

### ● `POST exams/<id>/start/` → start step 2 (also used to resume)
Body:
```json
{"nonce":"<from challenge>",
 "signature":"<Base64 DER SHA256withECDSA over UTF-8 sign_payload>",
 "integrity_token":"<only if integrity_required>"}
```
- The integrity token comes from `StandardIntegrityTokenProvider.request(...)` with `requestHash = integrity_request_hash`.
- Success: `{attempt_id, exam_id, resumed, deadline, server_time, state: "active"}`.
- **Timer:** remaining time = `deadline - server_time`. Anchor it to `SystemClock.elapsedRealtime()` when the response arrives. Never use the phone's wall clock.
- Nonces are single use and expire after 120s. On any challenge or signature error, fetch a new challenge.

### ● `POST exams/answers/save/`
- Body: `{attempt_id, question_id, answer}`.
  - MCQ / true-false: `answer` is the option `id`.
  - Short answer: `answer` is a string of at most 5000 characters.
- Success: `{status: "saved", attempt_id, question_id, answer_id, updated, server_time}`.
- **Save every answer immediately.** Queue unsent saves in Room and flush them on reconnect, because only saved answers count if the deadline passes. Limit: 120/min.

### ● `POST exams/<id>/submit/`
- Body: `{answers: {"<question_id>": <answer>, ...}}`, the full local state as a final safety net.
- Success: `{message, state: "completed", end_reason, points_scored, total_points, total_questions}`.
- `end_reason` is `"submitted"`, or `"deadline_expired"` if the submit arrived more than 10s after the deadline. In that case only previously saved answers count.
- Submit is **idempotent**: retrying after a success returns the same result.

### `GET exams/my-results/`
`[{attempt_id, exam_id, exam_title, points_scored, total_points, total_questions, violations, status, state, end_reason, date}]`

`end_reason` is one of `submitted`, `deadline_expired`, `violation_threshold` or `exam_disabled_by_admin`. Every path is graded from saved answers; none scores zero by default.

## 7. Monitoring (auth + ●)

### ● `POST monitoring/heartbeat/`: every 10s while the exam screen is open
```json
{"attempt_id": 12,
 "state": {"foreground": true, "lock_task": true, "multi_window": false, "overlay_suspect": false},
 "integrity_token": "<optional, see below>"}
```
- Response: `{status: "alive", state, end_reason, deadline, server_time, violations, risk, integrity_nonce}`.
- **The server detects silence.** More than 25s since the last heartbeat records a `heartbeat_gap` (soft) violation, whether you report it or not.
- If `state` isn't `active`, end the exam UI and go to results.
- **Periodic integrity:** every ~3 minutes, request a token with `requestHash = SHA-256 hex of the latest integrity_nonce` and send it on the next heartbeat. A failed verdict is a counted `integrity_failed` violation; a Google outage is ignored.
- Limit: 30/min per user.

### ● `POST monitoring/log/`: report a violation the moment it happens
- Body: `{attempt_id, type, metadata}`. Metadata keys allowed: `duration_ms`, `source`, `count`, `detail` (≤120 characters), `package`; anything else is dropped.
- Response: `{status: "logged", state, end_reason, deadline, server_time, violations, risk}`, plus `code: "attempt_terminated"` when this violation ended the attempt.

| type | severity | counts toward `violation_limit` |
|---|---|---|
| `app_backgrounded` | 3 | yes |
| `lock_task_exited` | 5 | yes |
| `multi_window` | 4 | yes |
| `overlay_detected` | 4 | yes |
| `screen_capture` | 4 | yes |
| `debugger_attached` | 5 | yes |
| `copy_paste` | 3 | yes |
| `tab_switch` (web) | 2 | yes |
| `accessibility_service` | 2 | no |
| `root_suspected` | 2 | no |
| `clock_tamper` | 2 | no |
| `window_blur` | 1 | no |

The server generates two more types itself: `heartbeat_gap` (1, does not count) and `integrity_failed` (5, counts). Clients cannot send these. "Does not count" types raise `risk` for invigilator review but never auto-terminate. Limit: 20/min.

### ● `POST monitoring/events/`: batched timeline telemetry (not violations)
- Body: `{attempt_id, events: [{type, question_id?, client_ts?, metadata?}]}`, at most 50 per batch.
- Types: `question_viewed`, `question_skipped`, `question_navigation`, `app_backgrounded`, `app_resumed`, `network_offline`, `network_restored`.
- Response: `{accepted, server_time}`. Limit: 30/min.

## 8. Exam screen sequence (reference)

1. Log in, then `devices/register/`. If the device is `pending`, show a waiting screen and poll `devices/me/`.
2. `exams/` → choose an exam → `exams/<id>/` (metadata).
3. `startLockTask()` and confirm it's pinned, then `challenge/` → sign (and get an integrity token if required) → `start/`.
4. `exams/<id>/` for the questions. Start the heartbeat (10s) and the violation detectors.
5. Each answer goes to `answers/save/` (queued offline). Navigation goes to `events/`.
6. When the timer reaches 0, or the user taps submit, call `submit/` with the full answers map and retry until you get 200 or `attempt_ended`.
7. Stop lock task and show the result.
