import os
import subprocess
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

# ---------- CONFIG ----------
CHECKIN_LOCK = "checkin.lock"
CHECKOUT_LOCK = "checkout.lock"
LOG_FILE = "scheduler.log"

# ---------- LOGGING ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# ---------- LOCK (DATE BASED) ----------
def is_locked(lock_file):
    if not os.path.exists(lock_file):
        return False

    with open(lock_file, "r") as f:
        saved_date = f.read().strip()

    return saved_date == datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")


def create_lock(lock_file):
    with open(lock_file, "w") as f:
        f.write(datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d"))

import time

# ---------- MAIN ----------
logging.info("Starting continuous scheduler... (Checking every 1 minute)")

while True:
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    weekday = now.weekday()

    if weekday < 6:  # Mon-Sat

        # ✅ CHECKIN → 8:50–8:55 AM IST
        if now.hour == 9 and 25 <= now.minute <= 30:
            if not is_locked(CHECKIN_LOCK):
                logging.info(f"[{now.time()}] Running CHECKIN")
                subprocess.run(["python3", "staffpulse_automation.py", "checkin"], check=True)
                create_lock(CHECKIN_LOCK)

        # ✅ CHECKOUT → 6:50–6:55 PM IST
        elif now.hour == 18 and 50 <= now.minute <= 55:
            if not is_locked(CHECKOUT_LOCK):
                logging.info(f"[{now.time()}] Running CHECKOUT")
                subprocess.run(["python3", "staffpulse_automation.py", "checkout"], check=True)
                create_lock(CHECKOUT_LOCK)

    # Sleep for exactly 1 minute before checking again
    time.sleep(60)