# NSP REST Alarm Engine

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/postgresql-15%2B-336791?logo=postgresql&logoColor=white)
![Polling](https://img.shields.io/badge/mode-REST%20polling-orange)

REST-based alarm polling service for Nokia NSP that:
- authenticates with OAuth client credentials,
- polls active alarms on a fixed schedule,
- detects NEW vs CLEARED alarms,
- stores active/snapshot/history state in PostgreSQL.

This project is intended for always-on deployment (Docker or Linux service).

## How It Works

1. `main.py` waits for the next aligned polling boundary.
2. `rest_client.py` calls NSP alarms endpoint with a bearer token.
3. `alarm_lifecycle.py` filters noisy alarms and computes lifecycle transitions.
4. `db.py` updates `active_alarms`, writes `alarm_snapshots`, and archives cleared alarms to `alarm_history`.
5. Periodic cleanup removes old snapshot/history rows (default retention: 7 days).

## Project Structure

- `main.py` - scheduler loop, retry handling, snapshots, retention cleanup
- `config.py` - environment loading and endpoint construction
- `token_manager.py` - OAuth token fetch + refresh logic
- `rest_client.py` - NSP alarms API client
- `alarm_lifecycle.py` - exclusion/inclusion rules + new/clear detection
- `db.py` - PostgreSQL tables and persistence methods
- `Dockerfile` - container image build
- `docker-compose.yml` - local/VM deployment with PostgreSQL

## Requirements

- Python 3.11+
- PostgreSQL 15+ (or compatible)
- Network access to NSP REST gateway
- Valid NSP OAuth client credentials

## Environment Variables

Create a `.env` file in the repo root:

```env
NSP_HOST=192.168.42.7
NSP_PORT=8443
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
VERIFY_SSL=false

DATABASE_URL=postgresql://nspuser:nsppass@db:5432/alarms
WHATSAPP_URL=http://whatsapp:3000/send

POLL_INTERVAL=10
```

Notes:
- `VERIFY_SSL=true` is recommended in production with proper CA trust.
- `POLL_INTERVAL` is in seconds and should be a positive integer.
- `WHATSAPP_URL` is currently loaded from config but not used by the existing code path.

## Run Locally (Without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Run With Docker Compose

Build and start:

```bash
docker compose up -d --build
```

Check status:

```bash
docker compose ps
```

Follow logs:

```bash
docker compose logs -f engine
```

Stop:

```bash
docker compose down
```

## First-Run Verification Checklist

Use this checklist after first deployment:

- [ ] `docker compose ps` shows `db` as healthy and `engine` as running
- [ ] `docker compose logs -f engine` shows repeated `[POLL] Completed` lines
- [ ] no recurring `[ERROR]` or auth failures in engine logs
- [ ] `active_alarms` contains current active alarms
- [ ] `alarm_snapshots` receives rows at `:00` and `:30`
- [ ] cleared alarms are moved into `alarm_history` with `duration_seconds`

Quick DB checks (inside Postgres container):

```bash
docker compose exec db psql -U nspuser -d alarms -c "SELECT COUNT(*) FROM active_alarms;"
docker compose exec db psql -U nspuser -d alarms -c "SELECT COUNT(*) FROM alarm_snapshots;"
docker compose exec db psql -U nspuser -d alarms -c "SELECT COUNT(*) FROM alarm_history;"
```

## Database Schema

Tables are auto-created on startup:

- `active_alarms`
  - current alarms keyed by `id`
  - stores `severity`, `first_seen`, `last_seen`, full JSON payload
- `alarm_snapshots`
  - periodic snapshots of active alarms
  - written at minute `00` and `30`
- `alarm_history`
  - cleared alarms with duration from `first_seen` to `cleared_at`

Indexes are created for key query columns (`last_seen`, `snapshot_time`, `alarm_id`, `cleared_at`).

## Alarm Filtering Logic

In `alarm_lifecycle.py`:
- Always include alarms containing:
  - `postFEC BER`
  - `Optical Lane High`
  - `Optical Lane Low`
- Exclude alarms containing:
  - `Threshold Crossing`
  - `Quality Threshold`
  - `Pluggable Module missing`

You can tune these keyword lists for your environment.

## Scheduling Behavior

- Polling aligns to interval boundaries using local timezone (`Asia/Dhaka`).
- A small jitter is added to reduce synchronized bursts.
- Duplicate triggers for the same slot are skipped.
- On NSP HTTP 500 responses, polling retries with exponential backoff.
- Graceful shutdown is handled for `SIGINT` and `SIGTERM`.

## Common Troubleshooting

- Auth failures (`401`):
  - verify `CLIENT_ID`/`CLIENT_SECRET`
  - verify NSP auth URL reachability
- TLS/SSL issues:
  - use `VERIFY_SSL=false` for testing only
  - enable cert validation for production
- DB connection errors:
  - confirm `DATABASE_URL`
  - ensure PostgreSQL is reachable from engine container/host
- Docker container naming conflicts:
  - fixed names were removed from compose; recreate stack with latest file

## Security Notes

- Do not commit `.env` with real credentials.
- Rotate NSP client secret regularly.
- Prefer private networking and firewall rules between engine and NSP/DB.

## License

Internal/private use unless your organization defines otherwise.
