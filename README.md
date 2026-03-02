# NSP REST Alarm Engine

Production-ready REST-based alarm polling engine for Nokia NSP.

This system polls NSP northbound REST API (`/oms1350/data/npr/alarms`),
detects new and cleared alarms, stores state in PostgreSQL,
and sends notifications (e.g., WhatsApp).

---

## 🏗 Architecture

NSP REST API  
        ↓  
REST Poller  
        ↓  
Alarm Lifecycle Engine  
        ↓  
PostgreSQL (active_alarms table)  
        ↓  
Notifier (WhatsApp or custom endpoint)

This replaces Kafka-based subscription with REST polling.

---

## 📁 Project Structure


nsp_rest_alarm_engine/
├── main.py # Daemon loop
├── rest_client.py # NSP REST client
├── token_manager.py # OAuth token manager
├── alarm_lifecycle.py # Alarm state engine
├── db.py # PostgreSQL integration
├── notifier.py # Notification sender
├── config.py # Environment config
├── requirements.txt
├── Dockerfile
└── .env.example



---

## 🔐 Features

- OAuth token auto-refresh
- Snapshot-based alarm detection
- New alarm detection
- Clear detection
- PostgreSQL-backed state
- WhatsApp notification integration
- Dockerized deployment
- Graceful shutdown
- Production polling loop

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and edit:


NSP_HOST=192.168.42.7
NSP_PORT=8443
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
VERIFY_SSL=false

DATABASE_URL=postgresql://user:pass@db:5432/alarms
WHATSAPP_URL=http://whatsapp:3000/send

POLL_INTERVAL=10


### Variable Description

| Variable | Description |
|----------|-------------|
| NSP_HOST | NSP IP/hostname |
| NSP_PORT | NSP HTTPS port |
| CLIENT_ID | OAuth client ID |
| CLIENT_SECRET | OAuth client secret |
| VERIFY_SSL | Enable SSL verification (true/false) |
| DATABASE_URL | PostgreSQL connection string |
| WHATSAPP_URL | Notification endpoint |
| POLL_INTERVAL | Polling interval in seconds |

---

## 🗄 Database Schema

The engine automatically creates:

```sql
CREATE TABLE active_alarms (
    id BIGINT PRIMARY KEY,
    severity TEXT,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP
);

Behavior:

If alarm ID appears for first time → NEW

If alarm ID missing in next poll → CLEARED

If alarm persists → updated last_seen

🚀 Running Locally
1️⃣ Install dependencies
pip install -r requirements.txt
2️⃣ Configure environment
cp .env.example .env

Edit .env

3️⃣ Run

python main.py
🐳 Running with Docker
Build image
docker build -t nsp-rest-engine .
Run container
docker run --env-file .env nsp-rest-engine
🐳 Example docker-compose (Optional)
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: alarms
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports:
      - "5432:5432"

  engine:
    build: .
    env_file: .env
    depends_on:
      - db

Run:

docker-compose up --build
🔁 Alarm Detection Logic

Each polling cycle:

Fetch current alarm list from NSP

Extract alarm IDs

Compare with database state

Detect:

NEW alarms

CLEARED alarms

Update database

Send notifications

⚠️ Production Recommendations

For production environments:

Enable SSL verification (VERIFY_SSL=true)

Use proper CA certificates

Use connection pooling (psycopg2 pool or SQLAlchemy)

Add structured logging (logging module)

Add log rotation

Add health endpoint

Add severity filtering

Add pagination if alarm list grows large

📊 Optional Improvements

Prometheus metrics endpoint

Severity threshold filtering

Alarm history table

Correlation logic

High-availability deployment

Kubernetes deployment

Retry/backoff logic

Alarm debounce logic

🧠 REST vs Kafka

This engine uses REST polling.

Advantages:

Works when Kafka not exposed

Simpler deployment

Fewer infrastructure dependencies

Trade-offs:

Not real-time

Slightly higher API load

Snapshot-based detection

🛑 Graceful Shutdown

The engine handles:

SIGINT

SIGTERM

Safe for:

Docker stop

systemd stop

Kubernetes termination

📜 License

Internal / Private Project

👨‍💻 Maintainer

Developed for production NSP alarm monitoring via REST interface.


---

Now your project looks clean, structured, and enterprise-ready.

If you want, I can next:

- Add structured logging (production-grade)
- Add alarm history table
- Add HA-ready version
- Convert to async high-performance version
- Or generate a proper GitHub-ready version with badges and versioning

You’re officially building real infrastructure now. 🔥