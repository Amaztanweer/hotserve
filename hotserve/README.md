# 🔥 HotServe — Setup Guide

Hostel On-Demand Delivery Platform  
Django + PostgreSQL + Redis + Razorpay + Django Channels

---

## Prerequisites

Install these before starting:

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Git

---

## Step 1 — Clone & Virtual Environment

```bash
# Navigate to your project folder
cd hotserve/

# Create virtual environment
python -m venv venv

# Activate it
# macOS / Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

---

## Step 2 — Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 3 — Set Up PostgreSQL

```bash
# Open PostgreSQL shell
psql -U postgres

# Run these commands:
CREATE DATABASE hotserve_db;
CREATE USER hotserve_user WITH PASSWORD 'hotserve_pass';
GRANT ALL PRIVILEGES ON DATABASE hotserve_db TO hotserve_user;
\q
```

---

## Step 4 — Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your values
nano .env   # or open in any editor
```

**Key things to set in `.env`:**

| Variable | What to put |
|---|---|
| `SECRET_KEY` | Generate at: https://djecrety.ir |
| `DB_PASSWORD` | Your PostgreSQL password |
| `RAZORPAY_KEY_ID` | From https://dashboard.razorpay.com |
| `RAZORPAY_KEY_SECRET` | From Razorpay dashboard |
| `ALLOWED_COLLEGE_DOMAINS` | Your college's email domain |

---

## Step 5 — Start Redis

```bash
# macOS (with Homebrew):
brew services start redis

# Ubuntu/Debian:
sudo systemctl start redis-server

# Docker:
docker run -d -p 6379:6379 redis:7-alpine
```

---

## Step 6 — Run Migrations

```bash
python manage.py makemigrations accounts
python manage.py makemigrations tasks
python manage.py makemigrations payments
python manage.py makemigrations chat
python manage.py migrate
```

---

## Step 7 — Seed Initial Data

```bash
# Create superuser (admin account)
python manage.py createsuperuser
# Enter: email, full_name, password

# Load task categories
python manage.py shell
```

Then paste this into the shell to create task categories:

```python
from apps.tasks.models import TaskCategory

categories = [
    {"name": "Food & Drinks",    "icon": "🍔", "base_reward_min": 20, "base_reward_max": 80,  "min_trust_required": "new"},
    {"name": "Stationery",       "icon": "📚", "base_reward_min": 15, "base_reward_max": 50,  "min_trust_required": "new"},
    {"name": "Parcels & Docs",   "icon": "📦", "base_reward_min": 30, "base_reward_max": 100, "min_trust_required": "new"},
    {"name": "Heavy Parcels",    "icon": "🏋️", "base_reward_min": 50, "base_reward_max": 200, "min_trust_required": "trusted"},
    {"name": "Laundry",          "icon": "👕", "base_reward_min": 40, "base_reward_max": 120, "min_trust_required": "new"},
    {"name": "Pharmacy",         "icon": "💊", "base_reward_min": 25, "base_reward_max": 80,  "min_trust_required": "new"},
    {"name": "Pre-purchase",     "icon": "🛒", "base_reward_min": 30, "base_reward_max": 150, "min_trust_required": "trusted"},
    {"name": "Printing",         "icon": "🖨️", "base_reward_min": 20, "base_reward_max": 60,  "min_trust_required": "new"},
    {"name": "Other Errands",    "icon": "⚡", "base_reward_min": 20, "base_reward_max": 100, "min_trust_required": "new"},
]

for i, cat in enumerate(categories):
    TaskCategory.objects.get_or_create(name=cat["name"], defaults={**cat, "sort_order": i})

print(f"Created {TaskCategory.objects.count()} categories ✅")
exit()
```

---

## Step 8 — Collect Static Files

```bash
python manage.py collectstatic --noinput
```

---

## Step 9 — Run the Development Server

```bash
# Daphne (handles both HTTP and WebSockets)
daphne -p 8000 hotserve.asgi:application

# OR standard Django (HTTP only — no WebSocket/chat):
python manage.py runserver
```

Open: **http://localhost:8000**

---

## Step 10 — Admin Setup

1. Go to **http://localhost:8000/django-admin/**
2. Log in with your superuser credentials
3. Your superuser account will have access to **http://localhost:8000/admin-panel/**

---

## Project URL Map

| URL | What it does |
|---|---|
| `/` | Redirects to dashboard |
| `/accounts/register/` | New user signup |
| `/accounts/login/` | Login |
| `/dashboard/` | Main dashboard |
| `/dashboard/post/` | Post a task |
| `/dashboard/feed/` | Task feed (runner) |
| `/dashboard/<uuid>/` | Task detail |
| `/payments/wallet/` | Wallet & top-up |
| `/chat/<uuid>/` | Chat room |
| `/admin-panel/` | Admin dashboard |
| `/admin-panel/runners/` | Runner approvals |
| `/admin-panel/disputes/` | Dispute resolution |
| `/admin-panel/users/` | User management |
| `/django-admin/` | Django admin |
| `/api/v1/accounts/token/` | Get JWT token |
| `/api/v1/tasks/` | Tasks API |
| `/api/v1/payments/` | Payments API |

---

## Environment Architecture

```
Browser / App
     │
     ├── HTTP  → Daphne → Django Views → PostgreSQL
     └── WS    → Daphne → Channels Consumer → Redis → PostgreSQL
```

---

## Common Issues

**`django.db.utils.OperationalError`** — PostgreSQL not running or wrong credentials in `.env`

**`redis.exceptions.ConnectionError`** — Redis not running, start it with `redis-server`

**`ModuleNotFoundError: channels_redis`** — Run `pip install -r requirements.txt` again

**Razorpay payment not working** — Check your key/secret in `.env`, use test keys for development

**College email rejected** — Add your domain to `ALLOWED_COLLEGE_DOMAINS` in `.env`

---

## Production Checklist

- [ ] Set `DEBUG=False` in `.env`
- [ ] Use a real `SECRET_KEY` (50+ random chars)
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Switch to production Razorpay keys (`rzp_live_...`)
- [ ] Configure real SMTP email settings
- [ ] Set up Nginx + Daphne
- [ ] Configure Razorpay webhook URL in dashboard
- [ ] Enable HTTPS (Let's Encrypt)
- [ ] Set up daily DB backups

---

## What's Built

| Feature | Status |
|---|---|
| Custom User auth (college email) | ✅ |
| Requester / Runner dual roles | ✅ |
| Task posting with escrow lock | ✅ |
| Runner verification (3-step) | ✅ |
| Trust levels (New/Trusted/Elite) | ✅ |
| Real-time WebSocket chat | ✅ |
| 3-hour chat timer + auto-close | ✅ |
| Razorpay wallet top-up | ✅ |
| Escrow release on confirmation | ✅ |
| Dispute resolution (admin) | ✅ |
| Admin dashboard with live stats | ✅ |
| Runner auto-approve/ban system | ✅ |
| REST API + JWT auth | ✅ |
| Dark theme HotServe UI | ✅ |

---

Built with Django 4.2 · PostgreSQL · Redis · Django Channels · Razorpay
