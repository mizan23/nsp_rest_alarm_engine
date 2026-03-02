from datetime import datetime
from zoneinfo import ZoneInfo

# 🔥 Force all timestamps to UTC+6
LOCAL_TZ = ZoneInfo("Asia/Dhaka")


# ---------------- Alarm Filtering ----------------

# These threshold alarms should still be stored
FORCE_INCLUDE_KEYWORDS = [
    "postFEC BER",
    "Optical Lane High",
    "Optical Lane Low"
]

# These should be excluded (noise)
EXCLUDED_KEYWORDS = [
    "Threshold Crossing",
    "Quality Threshold",
    "Pluggable Module missing"
]


def is_excluded(alarm):
    """
    Returns True if alarm should NOT be stored.
    Keeps Optical Lane and postFEC BER alarms intentionally.
    """

    label = (alarm.get("guiLabel") or "").strip()

    # 1️⃣ Always keep important degradation alarms
    for keyword in FORCE_INCLUDE_KEYWORDS:
        if keyword in label:
            return False

    # 2️⃣ Exclude general noisy threshold alarms
    for keyword in EXCLUDED_KEYWORDS:
        if keyword in label:
            return True

    return False


# ---------------- Alarm Lifecycle ----------------

class AlarmLifecycle:
    def __init__(self, db):
        self.db = db

    def process(self, alarms):

        current_ids = set()

        # -------- Process Current Active Alarms --------
        for alarm in alarms:

            # 🔴 Skip unwanted alarms
            if is_excluded(alarm):
                continue

            alarm_id = alarm["id"]
            current_ids.add(alarm_id)

            # Store full payload
            self.db.upsert_alarm(alarm)

        # -------- Detect Cleared Alarms --------
        previous_ids = self.db.get_active_ids()
        cleared_ids = previous_ids - current_ids

        if cleared_ids:
            print(f"[CLEAR] {len(cleared_ids)} alarms cleared", flush=True)

        for alarm_id in cleared_ids:

            record = self.db.get_alarm_record(alarm_id)

            if record:
                cleared_at = datetime.now(LOCAL_TZ)

                payload = record["payload"]

                self.db.move_to_history(
                    alarm_id=alarm_id,
                    severity=record["severity"],
                    first_seen=record["first_seen"],
                    cleared_at=cleared_at,
                    payload=payload
                )

            self.db.clear_alarm(alarm_id)