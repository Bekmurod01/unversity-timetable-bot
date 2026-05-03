# University Timetable Assistant

Scalable Telegram bot + admin backend for personalized university timetables, teacher schedules, targeted updates, exams/deadlines, and room lookup.

## Stack
- Bot: `aiogram` (Python)
- Admin backend: `FastAPI`
- DB: `PostgreSQL` + `SQLAlchemy`
- Scheduler: `APScheduler`
- Import formats: JSON + Excel

Recommended runtime: Python 3.12 or 3.13 (best binary package compatibility).

## Architecture
- `app/bot`: Telegram UX and user/admin bot commands
- `app/api`: secure admin API and web admin page (`/admin-panel`)
- `app/services`: timetable logic, notification service, change detector, EduPage adapter boundary
- `app/scheduler`: periodic polling + diff + targeted group notifications
- `mock_data`: current mock snapshot source until EduPage integration

## Core User Features
- Guided `/start` registration with confirmation
- Main menu:
  - `📅 My Timetable` (today/tomorrow/weekly/custom day)
  - `👨‍🏫 Teacher Timetable` (search/browse/favorites)
  - `🔔 Notifications` (toggle, changes-only, daily reminder, exam alerts)
  - `📊 Exams / Deadlines`
  - `🏫 Room Finder`
  - `⚙️ Settings`

## Core Admin Features
- Access control:
  - Bot admins by Telegram ID (`ADMIN_TELEGRAM_IDS`)
  - API admins by secret key header `X-Admin-Key`
- Dashboard (`/admin/dashboard`): users, active users, groups, last updates
- Timetable management:
  - JSON upload (`/admin/timetable/upload-json`)
  - Excel upload (`/admin/timetable/upload-excel`)
  - manual lesson insert (`/admin/timetable/manual`)
- Teacher CRUD (`/admin/teachers`)
- Broadcast system (`/admin/broadcast`) for all/group/year
- Exams/deadlines management (`/admin/exams`)
- Logs (`/admin/logs`)

## Group-Based Update Logic
1. Scheduler fetches fresh snapshot (`EduPageAdapter`) on interval.
2. `detect_timetable_changes` compares old DB lessons vs new snapshot.
3. Every change is logged in `updates_log`.
4. Only affected group users are notified.

## EduPage Future Integration
`app/services/edupage_adapter.py` is a boundary class.

Current behavior:
- Can read local JSON snapshot.
- Can fetch live `regulartt` payload and convert it to lesson rows automatically.

Env variables for live sync:
- `EDUPAGE_SYNC_ENABLED=true`
- `EDUPAGE_REGULARTT_URL=https://ciu.edupage.org/timetable/server/regulartt.js?__func=regularttGetData`
- `EDUPAGE_REGULARTT_TERM=13`
- `EDUPAGE_COOKIE=<your browser cookie header>`
- `EDUPAGE_EXTRA_HEADERS_JSON={}` (optional JSON object)

If live fetch fails, scheduler falls back to `SNAPSHOT_SOURCE`.

Manual all-groups import from downloaded regulartt payload:
- `python scripts/import_regulartt_to_db.py --all-groups --input mock_data/regulartt_live.json`

## Quick Start (Local)
1. Create `.env` from `.env.example`.
2. Install dependencies:
	- `pip install -r requirements.txt`
3. Run PostgreSQL (local or Docker).
4. Initialize DB tables:
	- `python -m app.init_db`
5. Seed optional mock metadata:
	- `python scripts/bootstrap_mock_data.py`
6. Run API:
	- `uvicorn app.api.main:app --reload`
7. Run bot:
	- `python -m app.bot.main`
8. Run scheduler:
	- `python -m app.scheduler.worker`

Open admin page:
- `http://localhost:8000/admin-panel`

## Docker Compose
1. Create `.env` from `.env.example` and set real bot token.
2. `docker compose up --build`

## Database Schema
See `migrations/schema.sql` for SQL migration-ready structure.

## Notes for Production Scale
- Replace scheduler with Celery + Redis for high throughput.
- Add Alembic migrations and CI checks.
- Add web admin auth with OAuth/JWT and role model.
- Add retry queue for failed Telegram sends.
- Add caching (Redis) for hot timetable queries.
