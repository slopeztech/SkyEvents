# SkyEvents — Deployment Guide

Production deployment on Ubuntu 24.04 LTS with Nginx, Gunicorn, Celery, PostgreSQL, Redis, and GitHub Actions CI/CD.

---

## Table of Contents

- [SkyEvents — Deployment Guide](#skyevents--deployment-guide)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
  - [Server Initial Setup](#server-initial-setup)
  - [PostgreSQL](#postgresql)
  - [Redis](#redis)
  - [Application Setup](#application-setup)
  - [Environment Variables](#environment-variables)
  - [Database Migrations and Static Files](#database-migrations-and-static-files)
  - [Gunicorn](#gunicorn)
  - [Celery Worker and Beat](#celery-worker-and-beat)
  - [Nginx](#nginx)
  - [SSL — Let's Encrypt](#ssl--lets-encrypt)
  - [Continuous Integration and Deployment](#continuous-integration-and-deployment)
    - [GitHub Actions workflow](#github-actions-workflow)
    - [Required GitHub Secrets](#required-github-secrets)
    - [Generate and install the deploy SSH key](#generate-and-install-the-deploy-ssh-key)
    - [Allow `skyevents` user to reload services without a password](#allow-skyevents-user-to-reload-services-without-a-password)
  - [Post-deployment Checklist](#post-deployment-checklist)
  - [Common Operations](#common-operations)
    - [View live logs](#view-live-logs)
    - [Manual deployment (without CI/CD)](#manual-deployment-without-cicd)
    - [Django management shell](#django-management-shell)
    - [Database backup](#database-backup)
    - [Rotate logs](#rotate-logs)

---

## Prerequisites

- Ubuntu 24.04 LTS server with a public IP
- A domain name pointing to that IP (`skyevents.example.com`)
- SSH access as a non-root user with `sudo` privileges
- A GitHub repository with the project code
- (Optional) An S3-compatible bucket for media/static storage

---

## Server Initial Setup

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3.12 python3.12-venv python3.12-dev \
    build-essential libpq-dev git curl nginx certbot python3-certbot-nginx \
    supervisor

# Create a dedicated system user for the application
sudo useradd --system --shell /bin/bash --home /srv/skyevents --create-home skyevents
```

---

## PostgreSQL

```bash
# Install PostgreSQL 16
sudo apt install -y postgresql-16 postgresql-client-16

# Start and enable the service
sudo systemctl enable --now postgresql

# Create database and user
sudo -u postgres psql <<'EOF'
CREATE USER skyevents WITH PASSWORD 'change_this_strong_password';
CREATE DATABASE skyevents OWNER skyevents ENCODING 'UTF8' LC_COLLATE 'en_US.UTF-8' LC_CTYPE 'en_US.UTF-8' TEMPLATE template0;
GRANT ALL PRIVILEGES ON DATABASE skyevents TO skyevents;
-- Enable SSL connections
ALTER SYSTEM SET ssl = on;
EOF
```

> **Security:** Replace `change_this_strong_password` with a randomly generated password (e.g. `openssl rand -base64 32`). Store it in the `.env` file only, never in the repository.

---

## Redis

```bash
# Install Redis 7
sudo apt install -y redis-server

# Secure Redis — bind to localhost only and require a password
sudo sed -i 's/^bind .*/bind 127.0.0.1 ::1/' /etc/redis/redis.conf
sudo sed -i 's/^# requirepass .*/requirepass change_this_redis_password/' /etc/redis/redis.conf

sudo systemctl enable --now redis-server
```

---

## Application Setup

> **Note:** Run the following block from your **admin user** (e.g. `ubuntu`). If you are already logged in as `skyevents`, skip `sudo -u skyevents bash <<'EOF' ... EOF` and run the inner commands directly.

```bash
# Run as the application user via heredoc (from your admin/sudo user)
sudo -u skyevents bash <<'EOF'
git clone https://github.com/YOUR_USERNAME/skyevents.git /srv/skyevents/app
cd /srv/skyevents/app
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements/production.txt
EOF
```

---

## Environment Variables

Create `/srv/skyevents/app/.env` (owned by `skyevents`, readable only by that user):

```bash
sudo -u skyevents tee /srv/skyevents/app/.env > /dev/null <<'EOF'
# Django
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=replace_with_50+_random_chars
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=skyevents.example.com

# Database
DATABASE_URL=postgres://skyevents:change_this_strong_password@127.0.0.1:5432/skyevents

# Redis / Celery
REDIS_URL=redis://:change_this_redis_password@127.0.0.1:6379/0
CELERY_BROKER_URL=redis://:change_this_redis_password@127.0.0.1:6379/0

# Email
EMAIL_HOST=smtp.mailprovider.com
EMAIL_PORT=587
EMAIL_HOST_USER=no-reply@skyevents.example.com
EMAIL_HOST_PASSWORD=smtp_password
EMAIL_USE_TLS=True

# Storage (S3 / MinIO — remove if using local storage)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_STORAGE_BUCKET_NAME=skyevents-media
AWS_S3_REGION_NAME=eu-west-1
AWS_S3_ENDPOINT_URL=https://s3.example.com

# CORS
CORS_ALLOWED_ORIGINS=https://skyevents.example.com

# Security
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
EOF

chmod 600 /srv/skyevents/app/.env
```

Generate a strong secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

## Database Migrations and Static Files

> **Note:** Run the following block from your **admin user** (e.g. `ubuntu`). If you are already logged in as `skyevents`, skip the heredoc wrapper and run the inner commands directly.

```bash
# Run non-interactive steps as the app user (from your admin/sudo user)
sudo -u skyevents bash <<'EOF'
cd /srv/skyevents/app
source .venv/bin/activate
python manage.py migrate --settings=config.settings.production
python manage.py collectstatic --noinput --settings=config.settings.production
python manage.py compilemessages --settings=config.settings.production
EOF

# Create a superuser interactively (first deploy only)
sudo -u skyevents bash -c "
  cd /srv/skyevents/app && \
  source .venv/bin/activate && \
  python manage.py createsuperuser --settings=config.settings.production
"
```

---

## Gunicorn

Create the systemd service unit:

```bash
sudo tee /etc/systemd/system/skyevents-gunicorn.service > /dev/null <<'EOF'
[Unit]
Description=SkyEvents — Gunicorn WSGI server
After=network.target postgresql.service redis-server.service

[Service]
Type=notify
User=skyevents
Group=skyevents
WorkingDirectory=/srv/skyevents/app
EnvironmentFile=/srv/skyevents/app/.env
ExecStart=/srv/skyevents/app/.venv/bin/gunicorn \
    --workers 4 \
    --worker-class gthread \
    --threads 2 \
    --bind unix:/run/skyevents/gunicorn.sock \
    --timeout 60 \
    --access-logfile /var/log/skyevents/access.log \
    --error-logfile /var/log/skyevents/error.log \
    config.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
RuntimeDirectory=skyevents
RuntimeDirectoryMode=0755

[Install]
WantedBy=multi-user.target
EOF
```

Create the log directory and enable the service:

```bash
sudo mkdir -p /var/log/skyevents
sudo chown skyevents:skyevents /var/log/skyevents

sudo systemctl daemon-reload
sudo systemctl enable --now skyevents-gunicorn
sudo systemctl status skyevents-gunicorn
```

> **Workers:** A good starting value is `2 × CPU_cores + 1`. Adjust based on load.

---

## Celery Worker and Beat

```bash
# Celery worker
sudo tee /etc/systemd/system/skyevents-celery.service > /dev/null <<'EOF'
[Unit]
Description=SkyEvents — Celery worker
After=network.target redis-server.service postgresql.service

[Service]
Type=forking
User=skyevents
Group=skyevents
WorkingDirectory=/srv/skyevents/app
EnvironmentFile=/srv/skyevents/app/.env
ExecStart=/srv/skyevents/app/.venv/bin/celery \
    -A config.celery multi start worker \
    --concurrency=4 \
    --logfile=/var/log/skyevents/celery-worker.log \
    --loglevel=info \
    --pidfile=/run/skyevents/celery-worker.pid
ExecStop=/srv/skyevents/app/.venv/bin/celery \
    -A config.celery multi stopwait worker \
    --pidfile=/run/skyevents/celery-worker.pid
ExecReload=/srv/skyevents/app/.venv/bin/celery \
    -A config.celery multi restart worker \
    --pidfile=/run/skyevents/celery-worker.pid \
    --logfile=/var/log/skyevents/celery-worker.log \
    --loglevel=info
RuntimeDirectory=skyevents
RuntimeDirectoryMode=0755

[Install]
WantedBy=multi-user.target
EOF

# Celery beat (periodic tasks scheduler)
sudo tee /etc/systemd/system/skyevents-celerybeat.service > /dev/null <<'EOF'
[Unit]
Description=SkyEvents — Celery Beat scheduler
After=network.target redis-server.service postgresql.service

[Service]
Type=simple
User=skyevents
Group=skyevents
WorkingDirectory=/srv/skyevents/app
EnvironmentFile=/srv/skyevents/app/.env
ExecStart=/srv/skyevents/app/.venv/bin/celery \
    -A config.celery beat \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    --logfile=/var/log/skyevents/celery-beat.log \
    --loglevel=info \
    --pidfile=/run/skyevents/celery-beat.pid
RuntimeDirectory=skyevents
RuntimeDirectoryMode=0755

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now skyevents-celery skyevents-celerybeat
```

---

## Nginx

```bash
sudo tee /etc/nginx/sites-available/skyevents > /dev/null <<'EOF'
upstream skyevents_gunicorn {
    server unix:/run/skyevents/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name skyevents.example.com;

    # Redirect all HTTP to HTTPS (certbot will update this block)
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name skyevents.example.com;

    # --- SSL (managed by certbot) ---
    ssl_certificate     /etc/letsencrypt/live/skyevents.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/skyevents.example.com/privkey.pem;
    include             /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam         /etc/letsencrypt/ssl-dhparams.pem;

    # --- Security headers ---
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options    nosniff always;
    add_header X-Frame-Options           DENY always;
    add_header Referrer-Policy           "strict-origin-when-cross-origin" always;

    client_max_body_size 100M;

    # --- Static files (only if not using S3) ---
    location /static/ {
        alias /srv/skyevents/app/staticfiles/;
        expires 1y;
        access_log off;
        add_header Cache-Control "public, immutable";
    }

    # --- Media files (only if not using S3) ---
    location /media/ {
        alias /srv/skyevents/app/media/;
        expires 7d;
        access_log off;
    }

    # --- Application ---
    location / {
        proxy_pass         http://skyevents_gunicorn;
        proxy_set_header   Host              $http_host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_redirect     off;
        proxy_read_timeout 90;
    }
}
EOF

# Enable the site and test the configuration
sudo ln -sf /etc/nginx/sites-available/skyevents /etc/nginx/sites-enabled/skyevents
sudo nginx -t
sudo systemctl reload nginx
```

---

## SSL — Let's Encrypt

```bash
# Obtain a certificate (Nginx plugin handles configuration automatically)
sudo certbot --nginx -d skyevents.example.com --email admin@skyevents.example.com --agree-tos --no-eff-email

# Verify automatic renewal
sudo certbot renew --dry-run

# Certbot installs a systemd timer for auto-renewal; verify it is active
sudo systemctl status certbot.timer
```

---

## Continuous Integration and Deployment

### GitHub Actions workflow

Create `.github/workflows/ci-cd.yml` in the repository:

```yaml
name: CI / CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # -----------------------------------------------------------------------
  # CI — run on every push and pull request
  # -----------------------------------------------------------------------
  test:
    name: Test (Python ${{ matrix.python-version }})
    runs-on: ubuntu-24.04
    strategy:
      matrix:
        python-version: ["3.12"]

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: skyevents_test
          POSTGRES_USER: skyevents
          POSTGRES_PASSWORD: test_password
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U skyevents"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    env:
      DJANGO_SETTINGS_MODULE: config.settings.test
      DJANGO_SECRET_KEY: ci-secret-key-not-used-in-production
      DATABASE_URL: postgres://skyevents:test_password@localhost:5432/skyevents_test
      REDIS_URL: redis://localhost:6379/0
      CELERY_BROKER_URL: redis://localhost:6379/0

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements/test.txt

      - name: Run migrations
        run: python manage.py migrate --no-input

      - name: Run tests
        run: python -m pytest tests/ -q --tb=short

      - name: Check types (mypy)
        run: mypy .

  # -----------------------------------------------------------------------
  # CD — deploy to production only on push to main after tests pass
  # -----------------------------------------------------------------------
  deploy:
    name: Deploy to production
    runs-on: ubuntu-24.04
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'

    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          port: ${{ secrets.SERVER_PORT }}
          script: |
            set -e
            cd /srv/skyevents/app

            # Pull latest code
            git fetch origin main
            git reset --hard origin/main

            # Activate virtual environment
            source .venv/bin/activate

            # Install/update dependencies
            pip install -r requirements/production.txt

            # Apply migrations
            python manage.py migrate --noinput --settings=config.settings.production

            # Collect static files
            python manage.py collectstatic --noinput --settings=config.settings.production

            # Compile translations
            python manage.py compilemessages --settings=config.settings.production

            # Restart services (zero-downtime: reload Gunicorn, restart Celery)
            sudo systemctl reload skyevents-gunicorn
            sudo systemctl restart skyevents-celery skyevents-celerybeat
```

### Required GitHub Secrets

Go to **GitHub → Repository → Settings → Secrets and variables → Actions** and add:

| Secret | Description |
|---|---|
| `SERVER_HOST` | Server IP or hostname |
| `SERVER_USER` | SSH user (e.g. `skyevents` or a deploy user) |
| `SERVER_SSH_KEY` | Private SSH key for that user |
| `SERVER_PORT` | SSH port (default `22`) |

### Generate and install the deploy SSH key

```bash
# On your local machine — generate a dedicated deploy key
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/skyevents_deploy

# Copy the PUBLIC key to the server
ssh-copy-id -i ~/.ssh/skyevents_deploy.pub skyevents@your_server_ip

# Paste the PRIVATE key content into the SERVER_SSH_KEY GitHub secret
cat ~/.ssh/skyevents_deploy
```

### Allow `skyevents` user to reload services without a password

```bash
sudo tee /etc/sudoers.d/skyevents-services > /dev/null <<'EOF'
skyevents ALL=(ALL) NOPASSWD: \
    /bin/systemctl reload skyevents-gunicorn, \
    /bin/systemctl restart skyevents-celery, \
    /bin/systemctl restart skyevents-celerybeat
EOF
sudo chmod 440 /etc/sudoers.d/skyevents-services
```

---

## Post-deployment Checklist

- [ ] `sudo systemctl status skyevents-gunicorn` — active (running)
- [ ] `sudo systemctl status skyevents-celery` — active (running)
- [ ] `sudo systemctl status skyevents-celerybeat` — active (running)
- [ ] `sudo nginx -t` — configuration OK
- [ ] `https://skyevents.example.com` loads with a valid SSL certificate
- [ ] Django admin accessible at `https://skyevents.example.com/admin/`
- [ ] API root accessible at `https://skyevents.example.com/api/v1/`
- [ ] `python manage.py check --deploy --settings=config.settings.production` — no issues
- [ ] Log files being written to `/var/log/skyevents/`
- [ ] Certbot auto-renewal timer active: `sudo systemctl status certbot.timer`

---

## Common Operations

### View live logs

```bash
# Gunicorn
sudo journalctl -u skyevents-gunicorn -f

# Celery worker
tail -f /var/log/skyevents/celery-worker.log

# Nginx
sudo tail -f /var/log/nginx/error.log
```

### Manual deployment (without CI/CD)

```bash
sudo -u skyevents bash <<'EOF'
cd /srv/skyevents/app
source .venv/bin/activate
git pull origin main
pip install -r requirements/production.txt
python manage.py migrate --settings=config.settings.production
python manage.py collectstatic --noinput --settings=config.settings.production
EOF

sudo systemctl reload skyevents-gunicorn
sudo systemctl restart skyevents-celery skyevents-celerybeat
```

### Django management shell

```bash
sudo -u skyevents bash -c "
  cd /srv/skyevents/app && \
  source .venv/bin/activate && \
  python manage.py shell_plus --settings=config.settings.production
"
```

### Database backup

```bash
# Manual backup
sudo -u postgres pg_dump skyevents | gzip > /srv/skyevents/backups/skyevents_$(date +%Y%m%d_%H%M%S).sql.gz

# Schedule daily backups via cron (as root)
sudo crontab -e
# Add:
# 0 3 * * * sudo -u postgres pg_dump skyevents | gzip > /srv/skyevents/backups/skyevents_$(date +\%Y\%m\%d).sql.gz
```

### Rotate logs

The Gunicorn access/error logs can be rotated with logrotate:

```bash
sudo tee /etc/logrotate.d/skyevents > /dev/null <<'EOF'
/var/log/skyevents/*.log {
    weekly
    rotate 12
    compress
    delaycompress
    missingok
    notifempty
    sharedscripts
    postrotate
        systemctl reload skyevents-gunicorn > /dev/null 2>&1 || true
    endscript
}
EOF
```
