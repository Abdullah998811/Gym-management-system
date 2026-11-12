# Titan Fitness & Gym Management System (GMS)

A production-grade, enterprise-ready **Gym Management System (GMS)** built with **Python 3.12**, **Flask 3**, **SQLAlchemy 2 ORM**, **Flask-Login**, **Flask-WTF (CSRF)**, **Flask-Limiter**, **ReportLab (PDF)**, **Chart.js**, and **Bootstrap 5**.

---

## 🚀 Key Features & Enterprise Hardening

- **Multi-Role Access Control (RBAC):** Admin, Manager, Trainer, Receptionist, and Member roles with dedicated sidebars and custom role dashboards.
- **73 Relational Models:** Comprehensive architecture spanning Members, Memberships, Staff, Classes, Workouts, Nutrition, Equipment Assets, Financial Invoices, Desk Check-In, Lockers, and Notifications.
- **IDOR Protection & Scoped Access:** Strict authorization helpers (`get_current_member()`, `ensure_member_access()`) guarantee members can only view and mutate their own data (cards, invoices, measurements, goals, complaints, and bookings), while staff retain branch-wide access.
- **Soft Delete & Audit Trail:** Every model implements `BaseModel` with `id`, `created_at`, `created_by`, `updated_at`, `updated_by`, `status`, `is_deleted`, and `deleted_by`. Full audit logging of all CRUD actions with JSON diffs, timestamps, and IP tracking. Soft-deleted emails and CNICs are cleanly partitioned via partial unique indexes.
- **Accurate Financial Decimals:** All financial transactions, prices, salaries, and invoice calculations strictly use `Decimal` (`Numeric(12, 2)`), preventing floating-point inaccuracies. Overpayments are rejected, and payment recording uses atomic row locking (`with_for_update`).
- **Interactive Analytics:** Real-time Chart.js dashboards showing monthly revenue trends, expense breakdowns, plan distribution, and daily attendance flow. Built with portable SQL (`extract('year'/'month')`) for dual SQLite and PostgreSQL compatibility.
- **Front Desk Operations:** Member check-in with membership verification, duplicate check-in detection, inactive membership blocking with audited staff override, and one-click check-out.
- **Class Scheduling & Waitlisting:** Capacity enforcement inside atomic transactions with row locks, per-date waitlisting, automatic queue promotion on cancellation, and unique confirmed booking constraints.
- **Official PDF & CSV Exports:** ReportLab PDF generation for Membership Cards, Invoice Receipts, and Monthly Financial Revenue Reports (filtered by month and year with XML text escaping). Unbounded lists are exported via streamed CSV responses.
- **Security & Session Hardening:** Werkzeug password hashing, rate limiting on login (5/min per IP via Flask-Limiter), POST-only logout with CSRF tokens, `session.clear()` before login, 15-minute lockout after 5 consecutive failed attempts, 30-minute inactivity timeout, and secure HTTP response headers (`X-Frame-Options`, `X-Content-Type-Options`, `Content-Security-Policy`).

---

## 📂 Project Structure

```
gym_management_system/
├── app/
│   ├── __init__.py          # Flask Application Factory, Security Headers & CLI Commands
│   ├── config.py            # SQLite/PostgreSQL & Environment Config
│   ├── extensions.py        # SQLAlchemy, Migrate, LoginManager, CSRF, Limiter
│   ├── models/              # 73 Relational Database Models
│   │   ├── __init__.py      # Re-exports all 73 models
│   │   ├── base.py          # BaseModel mixin with soft delete & audit
│   │   ├── access.py        # Role, Permission, User, LoginLog
│   │   ├── gym.py           # Branch, Department, Facility, Area, Hours, Holiday
│   │   ├── member.py        # Member, Profile, Contact, Measurements, Goals, Notes
│   │   ├── plan.py          # MembershipPlan, Features, Membership, Freeze, Renew
│   │   ├── staff.py         # Trainer, Certifications, Staff, Shifts, Payroll
│   │   ├── training.py      # GymClass, Schedules, Bookings, Waitlist, PT, Workouts
│   │   ├── nutrition.py     # Meals, DietPlans, Supplements, Sales
│   │   ├── equipment.py     # Equipment, Maintenance, Issues, PurchaseOrders
│   │   ├── finance.py       # Invoices, Items, Payments, Expenses, Discounts
│   │   └── operations.py    # Attendance, Lockers, Visitors, Feedback, Complaints, Audit
│   ├── forms/               # WTForms with server-side validation (CNIC, phone, BMI)
│   ├── routes/              # 12 Modular Blueprints
│   ├── utils/               # PDF Generation (ReportLab), Audit Logger, Decorators, CSV
│   ├── static/              # CSS (Gym Theme) & JS (Theme toggle & notifications)
│   └── templates/           # Jinja2 Templates (with base.html & reusable macros)
├── migrations/              # Alembic Database Migrations (Full 73 tables schema)
├── tests/                   # Pytest test suite (65 passing tests)
├── docker-compose.yml       # Docker Compose setup for PostgreSQL & Web
├── Dockerfile               # Container build instructions
├── run.py                   # WSGI Application Entry Point
├── seed.py                  # Database Seeding Script (Idempotent + --reset flag)
├── requirements.txt         # Pinned production dependencies
├── pytest.ini               # Pytest configuration
├── .env.example             # Template for environment variables
└── README.md                # Documentation & Deploy Guide
```

---

## 🛠️ Local Setup & Installation

### 1. Prerequisites
- Python 3.12 (or 3.10+)
- Git

### 2. Clone & Setup Virtual Environment
```bash
git clone <repository_url>
cd gym_management_system

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Ensure `.env` contains:
```ini
FLASK_APP=run.py
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=<generate_a_random_secure_secret_key>
DATABASE_URL=sqlite:///gym_management.db
```

### 5. Apply Migrations & Seed the Database
```bash
# Apply migrations for all 73 tables
flask db upgrade

# Seed realistic Pakistani gym demo data (idempotent, skips if already seeded)
flask seed
```

### 6. Run the Application
```bash
python run.py
```
Open your browser at `http://127.0.0.1:5000`.

---

## ⚙️ Flask CLI Commands

The application provides dedicated CLI management commands:

| Command | Description |
|---|---|
| `flask seed` | Seeds initial branches, roles, plans, demo users and operational data (idempotent; skips existing). |
| `flask seed --reset` | Clears all data and re-seeds from scratch (local development only). |
| `flask create-admin` | Interactively creates a new administrative user with custom credentials. |
| `flask expire-memberships` | Unified maintenance job: expires past memberships, restores finished freezes, marks overdue invoices, and releases expired lockers. |
| `flask expire-freezes` | Automated background/cron job that restores expired membership freezes back to Active. |
| `flask update-overdue` | Automated background/cron job that updates Unpaid/Partial invoices past their due date to Overdue. |

---

## 🔑 Demo User Credentials

The seed script creates demo users for each system role (all configured with a unified password):

| Role | Username | Password | Access Level |
|---|---|---|---|
| **Admin** | `admin` | `Admin@12345` | Full unrestricted access to all modules, audit trail, reports |
| **Manager** | `manager` | `Admin@12345` | Branch management, members, plans, finance, staff, equipment |
| **Trainer** | `trainer` | `Admin@12345` | Classes, PT sessions, workout routines, assigned members |
| **Receptionist** | `receptionist` | `Admin@12345` | Front desk check-in, bookings, lockers, member registration |
| **Member** | `member` | `Admin@12345` | Member portal, active plan, BMI chart, bookings, attendance |

---

## 🧪 Running Automated Tests

Run the complete test suite with **pytest**:
```bash
python -m pytest -v
```

### Test Suite Coverage (78 Passed Tests):
1. **Authorization & IDOR Protection (`test_idor.py` - 14 tests):**
   - Member A cannot view Member B's profile, measurements, goals, or notes.
   - Member A cannot download Member B's card PDF or invoice receipt PDF.
   - Member A cannot access Member B's measurement analytics.
   - Member A cannot cancel or book classes on behalf of Member B.
   - Member only sees their own complaints; staff has full visibility.
   - Member cannot access staff export routes or sales.
2. **Role-Based Access Control (`test_rbac.py` - 14 tests):**
   - 403 Forbidden enforcement on Member role accessing staff endpoints: class schedules, workouts, PT scheduling, lockers, equipment maintenance & issues, nutrition diet plans, supplements, and sales.
   - Administrative protection on monthly revenue analytics API.
   - Staff notes and sensitive medical conditions hidden from other members.
3. **Business Logic & Integrity (`test_business_logic.py` - 17 tests):**
   - Rejection of payments exceeding invoice balance due.
   - Overdue invoice status transition via CLI.
   - Membership freeze future date scheduling, overlapping freeze prevention, and automatic unfreezing via CLI.
   - Membership renewal auto-invoice and item generation with discount voucher rules.
   - Class booking capacity row locking, per-date waitlisting, and unique confirmed booking constraint.
   - Check-in blocked on expired/inactive membership, with audited staff override.
   - Soft-delete aware unique checks allowing re-registration after soft deletion, plus member restoration action.
   - Supplement inventory atomic stock deduction, price enforcement from DB, and expired supplement rejection.
   - Locker assignment validation: end date strictly after start date, row locking on occupied lockers, and release flow.
   - Exact Decimal currency math across all financial tables.
4. **Security, Headers & CLI (`test_security_and_cli.py` - 16 tests):**
   - Security headers verification (`X-Frame-Options`, `X-Content-Type-Options`, `Content-Security-Policy`).
   - Logout method enforcement: GET returns `405 Method Not Allowed`, POST clears session with CSRF protection.
   - Session clearing before user authentication prevents session fixation.
   - Login rate limiter: enforces 10 attempts/minute per IP, returns `429 Too Many Requests`.
   - Production SECRET_KEY validation: requires strong key, prevents defaults.
   - Custom HTTP error pages (400 CSRF, 403, 404, 413, 429, 500).
   - CSV formula injection mitigation (`=`, `+`, `-`, `@`, `\t`, `\r` prefixing) and filename quotation.
   - Jinja filter `localtime` converting UTC datetimes to `Asia/Karachi`.
   - Authenticated file upload serving route (`/uploads/...`) with magic bytes validation.
   - CLI command execution: idempotent seed, freeze expiry, overdue invoice processing, and unified membership expiry.
   - PDF generation engine with ReportLab and XML escaping.
5. **Authentication & Session Lifecycle (`test_auth.py` - 6 tests):**
   - Valid login, invalid password, forced password change on first login, 15-minute lockout after 5 failed attempts, open redirect validation (`is_safe_url`).
6. **CRUD & Streaming Exports (`test_crud.py` - 6 tests):**
   - Member, plan, and equipment lifecycle with soft delete verification and memory-safe streaming CSV exports.
7. **Smoke & URL Map Integrity (`test_smoke_endpoints.py` - 4 tests):**
   - Role dashboard rendering across all 5 roles.
   - Smoke test traversing all application GET routes with status `< 400`.
   - Static scan of all templates and Python files verifying 100% of `url_for('...')` endpoints exist.
   - Public health check endpoint.
8. **Models & Mixins (`test_models.py` - 2 tests):**
   - Soft delete helper `.active()` and BaseModel audit timestamp/user tracking across models.

---

## 🐳 Running with Docker & PostgreSQL

A multi-container setup with PostgreSQL 16 is provided via `docker-compose.yml`:

```bash
# Build and start PostgreSQL and Web services
docker-compose up --build -d

# View service logs
docker-compose logs -f web

# Run migrations and seed the database inside the container
docker-compose exec web flask db upgrade
docker-compose exec web flask seed

# Run test suite inside container against PostgreSQL
docker-compose exec web python -m pytest
```

---

## 🌐 Production Deployment (Render.com)

1. Create a **New PostgreSQL Database** on [Render.com](https://render.com).
2. Create a **New Web Service** connected to your Git repository.
3. Configure the following service settings:
   - **Environment:** `Python 3`
   - **Branch:** `main`
   - **Build Command:**
     ```bash
     pip install -r requirements.txt && flask db upgrade
     ```
   - **Start Command:**
     ```bash
     gunicorn run:app
     ```
4. Set the following **Environment Variables**:
   - `FLASK_ENV`: `production`
   - `SECRET_KEY`: `<Generate a random 64-char string>`
   - `DATABASE_URL`: `<Render PostgreSQL Internal Connection String>` (automatically converted from `postgres://` to `postgresql://`)
   - `SESSION_COOKIE_SECURE`: `True`
5. Seed initial data once via Render Shell:
   ```bash
   flask seed
   ```
6. Verify deployment:
   Navigate to `https://<your-app-name>.onrender.com/health` -> Returns `OK` with HTTP 200.

---

## 📄 License
Proprietary software developed for Titan Fitness & Gym Management System. All rights reserved.
