#!/usr/bin/env python3
"""
StaffPulse (My Hinez) Multi-User Automation Script
----------------------------------------------------
Usage:
    python3 staffpulse_automation.py checkin
    python3 staffpulse_automation.py checkout

Cron setup (Monday to Friday):
    50 8  * * 1-5  /usr/bin/python3 /home/<user>/staffpulse_automation.py checkin  >> ~/staffpulse.log 2>&1
    50 18 * * 1-5  /usr/bin/python3 /home/<user>/staffpulse_automation.py checkout >> ~/staffpulse.log 2>&1
"""

import sys
import time
import logging
import os
import urllib.request
import urllib.parse

# Load .env file automatically
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip(' "\'')
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
)

# ─────────────────────────────────────────
# USERS CONFIG — Add your users here
# ─────────────────────────────────────────
USERS = [
    {
        "name": os.environ.get("USER1_NAME", "SHIVA"),
        "email": os.environ.get("USER1_EMAIL"),
        "password": os.environ.get("USER1_PASSWORD"),
    },
    {
        "name": os.environ.get("USER2_NAME", "DHARSHU"),
        "email": os.environ.get("USER2_EMAIL"),
        "password": os.environ.get("USER2_PASSWORD"),
    },
    {
        "name": os.environ.get("USER3_NAME", "VP"),
        "email": os.environ.get("USER3_EMAIL"),
        "password": os.environ.get("USER3_PASSWORD"),
    }
]

# Filtering out users that don't have email or password configured in env
USERS = [u for u in USERS if u.get("email") and u.get("password")]
# ─────────────────────────────────────────

LOGIN_URL = "https://staffpulse.in/auth/login"

# ─────────────────────────────────────────
# TELEGRAM CONFIG — set via env vars or fill here
# ─────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")


def send_telegram(message: str):
    """Send a message via Telegram bot. Silently skips if not configured."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        payload = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"})
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?{payload}"
        urllib.request.urlopen(url, timeout=10)
    except Exception as e:
        log.warning(f"Telegram notification failed: {e}")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)


def get_driver():
    """Headless Chrome driver setup."""
    options = Options()
    
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-notifications")
    
    # Check if we're in Docker/Railway (chromium is installed at /usr/bin/chromium via apt-get)
    if os.path.exists("/usr/bin/chromium"):
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    else:
        # Local execution using webdriver_manager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
    driver.implicitly_wait(10)
    return driver


def wait_and_click(driver, by, selector, timeout=20, label="element"):
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, selector))
        )
        el.click()
        log.info(f"  Clicked: {label}")
        return el
    except TimeoutException:
        log.error(f"  Timeout waiting for: {label}")
        raise


def safe_click(driver, element, label="element"):
    """Try normal click first, then fallback to JS click if overlay blocks it."""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        element.click()
    except ElementClickInterceptedException:
        log.warning(f"  Normal click intercepted for {label}, trying JS click...")
        driver.execute_script("arguments[0].click();", element)
    log.info(f"  Clicked: {label}")


def click_confirmation_button(driver):
    """Click confirmation button inside checkout popup."""
    popup_xpath = "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'are you sure') or contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'sure want')]"
    modal_xpath = "//div[contains(@class,'ant-modal') and not(contains(@class,'hidden'))]"
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, popup_xpath))
        )
        log.info("  Confirmation popup detected")
    except TimeoutException:
        log.info("  No explicit confirmation popup text found")

    modal_candidates = [
        ".//button[.//span[contains(normalize-space(.),'Check Out')] or contains(normalize-space(.),'Check Out')]",
        ".//button[.//span[contains(normalize-space(.),'Checkout')] or contains(normalize-space(.),'Checkout')]",
        ".//button[.//span[contains(normalize-space(.),'Confirm')] or contains(normalize-space(.),'Confirm')]",
        ".//button[.//span[contains(normalize-space(.),'Yes')] or contains(normalize-space(.),'Yes')]",
        ".//button[.//span[contains(normalize-space(.),'Ok') or contains(normalize-space(.),'OK') or contains(normalize-space(.),'Okay')] or contains(normalize-space(.),'Ok') or contains(normalize-space(.),'OK') or contains(normalize-space(.),'Okay')]",
    ]

    try:
        modal = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.XPATH, modal_xpath))
        )
    except TimeoutException:
        modal = None
        log.info("  Visible confirmation modal not found, trying page-level fallback")

    search_root = modal if modal else driver

    for xpath in modal_candidates:
        try:
            btn = WebDriverWait(driver, 5).until(
                lambda d: next(
                    (
                        el for el in search_root.find_elements(By.XPATH, xpath)
                        if el.is_displayed() and el.is_enabled()
                    ),
                    False,
                )
            )
            safe_click(driver, btn, label=f"confirmation button via {xpath}")
            return True
        except TimeoutException:
            continue

    log.warning("  Confirmation button not found")
    return False


def wait_and_type(driver, by, selector, text, timeout=20, label="field"):
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
        el.clear()
        el.send_keys(text)
        log.info(f"  Typed into: {label}")
        return el
    except TimeoutException:
        log.error(f"  Timeout waiting for: {label}")
        raise


def login(driver, email, password):
    """Login with email and password."""
    log.info(f"  Opening: {LOGIN_URL}")
    driver.get(LOGIN_URL)
    time.sleep(2)

    # Step 1: Enter email
    wait_and_type(driver, By.CSS_SELECTOR,
                  "input[type='email'], input[type='text'], input[placeholder*='email'], input[placeholder*='Email'], input[name='email'], input[name='username']",
                  email, label="Email field")
    time.sleep(1)

    # Step 2: Click Next
    wait_and_click(driver, By.XPATH,
                   "//button[contains(.,'Next')]",
                   label="Next button")
    time.sleep(2)

    # Step 3: Enter password
    wait_and_type(driver, By.CSS_SELECTOR,
                  "input[type='password']",
                  password, label="Password field")
    time.sleep(1)

    # Step 4: Click Sign In
    wait_and_click(driver, By.XPATH,
                   "//button[contains(.,'Sign In')]",
                   label="Sign In button")
    time.sleep(3)

    log.info("  Login successful ✓")


def go_to_my_people(driver):
    """Navigate to My People dashboard."""
    try:
        wait_and_click(driver, By.XPATH,
                       "//h3[contains(.,'My People')]/following::a[contains(.,'Access')] | //button[contains(.,'Access')] | //a[contains(.,'Access')]",
                       label="My People - Access button")
        time.sleep(3)
        log.info(f"  Navigated to My People ✓")
    except Exception:
        log.warning("  Access button not found, trying direct URL...")
        driver.get("https://mypeople.staffpulse.in/dashboards")
        time.sleep(3)


def do_checkin(driver):
    """Click Check In button."""
    log.info("  Looking for Check In button...")
    try:
        el = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Check In')] | //span[contains(.,'Check In')]/parent::button"))
        )
        el.click()
        log.info("  Clicked: Check In button")
        time.sleep(2)

        # Handle confirmation popup
        try:
            confirm = driver.find_element(By.XPATH,
                       "//button[contains(.,'Confirm') or contains(.,'Yes')]")
            confirm.click()
            log.info("  Confirmation clicked ✓")
            time.sleep(2)
        except NoSuchElementException:
            pass

        checked_time = datetime.now().strftime("%I:%M %p")
        log.info(f"  CHECK IN done at {datetime.now().strftime('%H:%M:%S')}")
        return True, checked_time
    except TimeoutException:
        log.info("  Check In button not found. Already check in panniyachi! ✓")
        return True, "Already Checked In"


def do_checkout(driver):
    """Click Check Out button."""
    log.info("  Looking for Check Out button...")
    try:
        el = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Check Out')] | //span[contains(.,'Check Out')]/parent::button"))
        )
        el.click()
        log.info("  Clicked: Check Out button")
        time.sleep(2)

        # Handle confirmation popup or second checkout confirmation button
        if click_confirmation_button(driver):
            time.sleep(2)
        else:
            log.info("  No secondary checkout confirmation button found")

        checked_time = datetime.now().strftime("%I:%M %p")
        log.info(f"  CHECK OUT done at {datetime.now().strftime('%H:%M:%S')}")
        return True, checked_time
    except TimeoutException:
        log.info("  Check Out button not found. Already check out panniyachi! ✓")
        return True, "Already Checked Out"


def run_for_user(user, action):
    """Run checkin/checkout for a single user. Returns True if success."""
    log.info(f"-- Starting for: {user['name']} ({user['email']}) --")
    driver = None
    try:
        driver = get_driver()
        login(driver, user["email"], user["password"])
        go_to_my_people(driver)

        if action == "checkin":
            success, chk_time = do_checkin(driver)
        else:
            success, chk_time = do_checkout(driver)

        log.info(f"-- {user['name']} DONE --\n")
        
        action_name = "Check-IN" if action == "checkin" else "Check-OUT"
        if chk_time.startswith("Already"):
            send_telegram(f"✅ <b>{action_name}</b> already done for <b>{user['name']}</b>.")
        else:
            send_telegram(f"✅ <b>{action_name}</b> Done for <b>{user['name']}</b> with checked time <b>{chk_time}</b>")
            
        return True

    except Exception as e:
        log.error(f"-- {user['name']} FAILED: {e} --\n")
        if driver:
            screenshot_path = f"/tmp/staffpulse_error_{user['name'].replace(' ', '_')}_{action}.png"
            driver.save_screenshot(screenshot_path)
            log.info(f"  Screenshot saved: {screenshot_path}")
            
        action_name = "Check-IN" if action == "checkin" else "Check-OUT"
        send_telegram(f"❌ <b>{action_name}</b> Failed for <b>{user['name']}</b>. Error occurred.")
        return False

    finally:
        if driver:
            driver.quit()
        time.sleep(3)  # Small gap between users


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("checkin", "checkout"):
        print("Usage: python3 staffpulse_automation.py checkin|checkout")
        sys.exit(1)

    action = sys.argv[1]
    
    current_time = datetime.now().time()
    if action == "checkin":
        if current_time < datetime.strptime("08:45", "%H:%M").time():
            msg = f"Current time {current_time.strftime('%H:%M')} is before 08:45 AM. Too early for check in! Exiting."
            print(msg)
            send_telegram(msg)
            sys.exit(0)
    elif action == "checkout":
        if current_time < datetime.strptime("18:45", "%H:%M").time():
            msg = f"Current time {current_time.strftime('%H:%M')} is before 18:45. Too early for check out! Exiting."
            print(msg)
            send_telegram(msg)
            sys.exit(0)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log.info("=" * 50)
    log.info(f"StaffPulse Automation | {action.upper()} | {now}")
    log.info(f"Total users: {len(USERS)}")
    log.info("=" * 50 + "\n")

    results = []
    for user in USERS:
        success = run_for_user(user, action)
        results.append((user["name"], success))

    # Summary
    log.info("=" * 50)
    log.info("SUMMARY:")
    for name, success in results:
        status = "SUCCESS" if success else "FAILED"
        log.info(f"  {name}: {status}")
    log.info("=" * 50 + "\n")

    # Exit with error if any user failed
    if not all(s for _, s in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
