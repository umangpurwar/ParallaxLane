# Deploying ParallaxLane

The simplest reliable setup is **one Linux VM** (2 vCPU, 4 GB RAM is enough for a few hundred candidates) running the Docker Compose file, behind **Caddy** for automatic HTTPS. A managed PostgreSQL database is optional but recommended.

```
Internet ── Caddy (HTTPS) ──┬── admin.example.com ──> frontend container (nginx, serves dashboard, proxies /api/)
                            └── api.example.com ────> web container (gunicorn, Django)
                                                        ├── db (PostgreSQL)
                                                        └── redis
```

The dashboard calls the API through its own nginx (`/api/`), so it needs no CORS. The Android app calls `https://api.example.com/api/` directly.

## 1. Server preparation

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 caddy git
git clone <your repository URL> parallaxlane && cd parallaxlane/backend
```

## 2. Backend environment

Create `backend/.env`. Never commit it.

```
SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(64))">
DEBUG=False
ALLOWED_HOSTS=api.example.com,admin.example.com
CSRF_TRUSTED_ORIGINS=https://admin.example.com

DB_NAME=parallaxlane
DB_USER=parallaxlane
DB_PASSWORD=<strong password>
DB_HOST=db
DB_PORT=5432

CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://admin.example.com

USE_REDIS_CACHE=True
REDIS_URL=redis://redis:6379/0
REDIS_REQUIRED=True

EMAIL_PROVIDER=brevo
BREVO_API_KEY=<from Brevo: SMTP and API, API keys>
DEFAULT_FROM_EMAIL=no-reply@example.com
EMAIL_FROM_NAME=ParallaxLane

DEVICE_REQUIRED_FOR_EXAMS=True
INTEGRITY_REQUIRED=False
TRUST_PROXY_IP_HEADER=True
MIN_ANDROID_APP_VERSION=1
ORGANISATION_CREATION_ENABLED=True
```

**Where the values come from:**
- `SECRET_KEY`: generate it with the command shown.
- `BREVO_API_KEY`: your Brevo account. Brevo also needs a verified sender for `DEFAULT_FROM_EMAIL`.
- **Database:** set `DB_*` to the database you create. For a managed database, set `DB_HOST` to its host and remove the `db` service from the compose file.

**`TRUST_PROXY_IP_HEADER=True` is only safe with this setup:** Caddy sets `X-Real-IP`, and port 8000 must not be reachable from the internet. The compose file already binds port 8000 to `127.0.0.1`; keep it that way.

The settings refuse to start in production with a missing or insecure value: a weak `SECRET_KEY`, wildcard hosts or CORS, or the console email provider. The startup error names the problem.

`CSRF_TRUSTED_ORIGINS` is only needed for the Django `/admin/` site; the API uses tokens, not cookies.

## 3. Start, migrate and create the super admin

```bash
cd backend
docker compose up -d --build              # web runs migrations on start
docker compose exec -e SUPERADMIN_EMAIL=you@example.com -e SUPERADMIN_PASSWORD='<long random>' web python manage.py create_superadmin
docker compose exec web python manage.py check --deploy
```

**Migrations on later deploys:** after `git pull`, run `docker compose up -d --build`. The web container runs `migrate` before starting gunicorn.

**The super admin command:**
- It is safe to run again: an existing super admin is left as it is.
- It refuses to turn an existing ordinary account into the super admin.
- To change the password, add `--reset-password`.
- Pass the password with `-e` as shown, and do not store it in `.env`.

## 4. HTTPS with Caddy

`/etc/caddy/Caddyfile`:

```
api.example.com {
    reverse_proxy 127.0.0.1:8000 {
        header_up X-Real-IP {remote_host}
    }
}

admin.example.com {
    reverse_proxy 127.0.0.1:5173
}

admin.example.com/admin/* {
    # Optional: restrict the Django admin site to your own IP.
    @blocked not remote_ip <your.ip.address>
    respond @blocked 403
    reverse_proxy 127.0.0.1:8000
}
```

`sudo systemctl reload caddy`. Caddy obtains and renews certificates by itself; DNS A records for both names must point at the VM.

## 5. Point the clients at the deployment

- **Dashboard:** it is built with `VITE_API_BASE_URL=/api/` (see the compose file), so it works on any domain without changes.
- **Android app:** set `SERVER_URL=https://api.example.com/api/` in `gradle.properties` and build a release.

## 6. Verify

```bash
curl https://api.example.com/api/health/              # {"status": "ok", "database": "ok"}
curl -I https://admin.example.com/login               # 200, with Content-Security-Policy header
```

Then in a browser:
1. Sign in at `https://admin.example.com` as the super admin and confirm the platform overview loads.
2. Create a test account, apply for an organisation, approve it, then sign in as that account and create an exam.
3. Open the API's `/api/master-admin/stats/` without a token: it must answer 401.

## 7. Backups and updates

- **Database backup:** `docker compose exec db pg_dump -U parallaxlane parallaxlane | gzip > backup-$(date +%F).sql.gz`. Schedule it with cron and copy the file off the server.
- **Updates:** `git pull && docker compose up -d --build`.
- **Logs:** `docker compose logs -f web`. Requests are logged without bodies or tokens.

## Separate hosting (optional)

The dashboard is a static site (`npm run build` produces `frontend/dist`). If you host it on a static host such as Netlify or Cloudflare Pages:
- **Build:** run it with `VITE_API_BASE_URL=https://api.example.com/api/`.
- **CORS:** add the site's origin to `CORS_ALLOWED_ORIGINS`.
- **Routing:** configure the host to serve `index.html` for unknown paths, because the dashboard uses browser history routing.
