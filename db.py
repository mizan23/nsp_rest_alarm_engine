import psycopg2
import time
import sys
from datetime import datetime, timezone
from config import DATABASE_URL
from psycopg2.extras import Json


# ✅ Always store in UTC (industry best practice)
def now_utc():
    return datetime.now(timezone.utc)


class AlarmDB:
    def __init__(self):
        self.conn = self._connect_with_retry()
        self._create_tables()

    # ---------------- DB CONNECTION ----------------

    def _connect_with_retry(self, retries=10, delay=5):
        for attempt in range(retries):
            try:
                print(f"[DB] Connecting attempt {attempt+1}...")
                conn = psycopg2.connect(DATABASE_URL)
                print("[DB] Connected successfully.")
                return conn
            except psycopg2.OperationalError as e:
                print(f"[DB] Connection failed: {e}")
                time.sleep(delay)

        print("[DB] Could not connect after retries. Exiting.")
        sys.exit(1)

    # ---------------- TABLE SETUP ----------------

    def _create_tables(self):
        with self.conn.cursor() as cur:

            # Active alarms
            cur.execute("""
                CREATE TABLE IF NOT EXISTS active_alarms (
                    id BIGINT PRIMARY KEY,
                    severity TEXT,
                    first_seen TIMESTAMPTZ,
                    last_seen TIMESTAMPTZ,
                    payload JSONB
                )
            """)

            # Snapshot table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS alarm_snapshots (
                    snapshot_time TIMESTAMPTZ,
                    alarm_id BIGINT,
                    severity TEXT,
                    payload JSONB
                )
            """)

            # History table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS alarm_history (
                    alarm_id BIGINT,
                    severity TEXT,
                    first_seen TIMESTAMPTZ,
                    cleared_at TIMESTAMPTZ,
                    duration_seconds BIGINT,
                    payload JSONB
                )
            """)

            # Indexes
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_active_last_seen
                ON active_alarms (last_seen)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshot_time
                ON alarm_snapshots (snapshot_time)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_alarm_id
                ON alarm_history (alarm_id)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_cleared_at
                ON alarm_history (cleared_at)
            """)

            self.conn.commit()

    # ---------------- ACTIVE ALARMS ----------------

    def get_active_ids(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM active_alarms")
            return {row[0] for row in cur.fetchall()}

    def get_alarm_record(self, alarm_id):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT severity, first_seen, payload
                FROM active_alarms
                WHERE id = %s
            """, (alarm_id,))
            row = cur.fetchone()
            if row:
                return {
                    "severity": row[0],
                    "first_seen": row[1],   # already timezone-aware (UTC)
                    "payload": row[2]
                }
        return None

    def upsert_alarm(self, alarm):
        alarm_id = alarm["id"]
        severity = alarm.get("severity", "unknown")
        now = now_utc()

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO active_alarms
                (id, severity, first_seen, last_seen, payload)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id)
                DO UPDATE SET
                    last_seen = EXCLUDED.last_seen,
                    severity = EXCLUDED.severity,
                    payload = EXCLUDED.payload
            """, (
                alarm_id,
                severity,
                now,
                now,
                Json(alarm)
            ))

            self.conn.commit()

    def clear_alarm(self, alarm_id):
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM active_alarms WHERE id = %s", (alarm_id,))
            self.conn.commit()

    # ---------------- SNAPSHOTS ----------------

    def insert_snapshot(self, snapshot_time, alarms):
        with self.conn.cursor() as cur:
            for alarm in alarms:
                cur.execute("""
                    INSERT INTO alarm_snapshots
                    (snapshot_time, alarm_id, severity, payload)
                    VALUES (%s, %s, %s, %s)
                """, (
                    snapshot_time,
                    alarm["id"],
                    alarm.get("severity", "unknown"),
                    Json(alarm)
                ))

            self.conn.commit()

    # ---------------- HISTORY ----------------

    def move_to_history(self, alarm_id, severity, first_seen, cleared_at, payload):

        # Both are timezone-aware UTC → safe subtraction
        duration = int((cleared_at - first_seen).total_seconds())

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO alarm_history
                (alarm_id, severity, first_seen, cleared_at, duration_seconds, payload)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                alarm_id,
                severity,
                first_seen,
                cleared_at,
                duration,
                Json(payload)
            ))

            self.conn.commit()

    # ---------------- RETENTION ----------------

    def cleanup_old_data(self, days=7):
        with self.conn.cursor() as cur:

            cur.execute("""
                DELETE FROM alarm_history
                WHERE cleared_at < NOW() - (%s * INTERVAL '1 day')
            """, (days,))

            cur.execute("""
                DELETE FROM alarm_snapshots
                WHERE snapshot_time < NOW() - (%s * INTERVAL '1 day')
            """, (days,))

            self.conn.commit()