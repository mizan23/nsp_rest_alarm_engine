import time
import signal
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from threading import Lock

from config import POLL_INTERVAL
from rest_client import RestClient
from db import AlarmDB
from alarm_lifecycle import AlarmLifecycle


LOCAL_TZ = ZoneInfo("Asia/Dhaka")

running = True
poll_lock = Lock()

last_run_slot = None


def shutdown(sig, frame):
    global running
    print("[SYSTEM] Shutdown signal received")
    running = False


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)


def wait_until_next_boundary(interval_seconds):
    now = datetime.now(LOCAL_TZ)

    # Calculate next aligned boundary cleanly
    seconds = now.minute * 60 + now.second
    remainder = seconds % interval_seconds
    wait_seconds = interval_seconds - remainder

    if remainder == 0:
        wait_seconds = interval_seconds

    # Small jitter (prevents sync collision if multiple engines exist)
    wait_seconds += random.uniform(0.2, 0.8)

    time.sleep(wait_seconds)


def fetch_with_retry(client, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return client.fetch_alarms()
        except Exception as e:
            if "500" in str(e) and attempt < max_attempts - 1:
                backoff = 2 ** attempt
                print(f"[RETRY] 500 error. Retrying in {backoff}s...")
                time.sleep(backoff)
            else:
                raise


def main():
    global last_run_slot

    print("[SYSTEM] NSP REST Alarm Engine Starting...")

    client = RestClient()
    db = AlarmDB()
    lifecycle = AlarmLifecycle(db)

    last_snapshot_slot = None
    last_cleanup_hour = None

    while running:

        wait_until_next_boundary(POLL_INTERVAL)

        now = datetime.now(LOCAL_TZ)
        current_slot = now.strftime("%Y-%m-%d %H:%M")

        # Prevent duplicate execution within same slot
        if current_slot == last_run_slot:
            print("[SKIP] Duplicate boundary trigger avoided")
            continue

        if not poll_lock.acquire(blocking=False):
            print("[SKIP] Poll already running")
            continue

        try:
            last_run_slot = current_slot

            alarms = fetch_with_retry(client)
            alarm_count = len(alarms)

            print(f"[POLL] Completed at {now} | Fetched {alarm_count} alarms")

            lifecycle.process(alarms)

            # ---- Snapshot isolation ----
            if now.minute in (0, 30):
                slot = now.strftime("%Y-%m-%d %H:%M")
                if slot != last_snapshot_slot:
                    print(f"[SNAPSHOT] Saving aligned snapshot at {slot}")
                    db.insert_snapshot(now, alarms)
                    last_snapshot_slot = slot

            # ---- Cleanup isolation ----
            current_hour = now.strftime("%Y-%m-%d %H")
            if current_hour != last_cleanup_hour:
                print("[CLEANUP] Running 7-day retention cleanup")
                db.cleanup_old_data(days=7)
                last_cleanup_hour = current_hour

        except Exception as e:
            print(f"[ERROR] {e}")

        finally:
            poll_lock.release()


if __name__ == "__main__":
    main()