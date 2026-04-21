from datetime import datetime
import subprocess

now = datetime.utcnow()

# Monday=0, Sunday=6
weekday = now.weekday()

# Only Mon-Sat (0–5)
if weekday < 6:

    # Checkin → 3:20 UTC
    if now.hour == 3 and now.minute == 20:
        print("Running CHECKIN")
        subprocess.run(["python3", "/app/staffpulse_automation.py", "checkin"])

    # Checkout → 13:20 UTC
    elif now.hour == 13 and now.minute == 20:
        print("Running CHECKOUT")
        subprocess.run(["python3", "/app/staffpulse_automation.py", "checkout"])

    else:
        print("No task now:", now)

else:
    print("Sunday - No run")