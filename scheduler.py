from datetime import datetime
import subprocess

now = datetime.utcnow()

# Monday=0, Sunday=6
weekday = now.weekday()

# Only Mon-Sat (0–5)
if weekday < 6:

    # Checkin → 8:50 AM to 8:55 AM IST (3:20 to 3:25 UTC)
    if now.hour == 3 and 43 <= now.minute <= 45:
        print("Running CHECKIN")
        subprocess.run(["python3", "staffpulse_automation.py", "checkin"])

    # Checkout → 6:50 PM to 6:55 PM IST (13:20 to 13:25 UTC)
    elif now.hour == 13 and 20 <= now.minute <= 25:
        print("Running CHECKOUT")
        subprocess.run(["python3", "staffpulse_automation.py", "checkout"])

    else:
        print("No task now:", now)

else:
    print("Sunday - No run")
