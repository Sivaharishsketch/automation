#!/usr/bin/env python3
import html
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
BOT_TOKEN = ""
ALLOWED_CHAT_ID = ""
POLL_TIMEOUT_SECONDS = 30
MESSAGE_LIMIT = 3500
COMMAND_MAP = {
    "checkin": "checkin",
    "check in": "checkin",
    "/checkin": "checkin",
    "/check_in": "checkin",
    "checkout": "checkout",
    "check out": "checkout",
    "/checkout": "checkout",
    "/check_out": "checkout",
}


def load_env_file():
    if not os.path.exists(ENV_PATH):
        return

    with open(ENV_PATH, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip("\"'")


def telegram_api(method, params):
    query = urllib.parse.urlencode(params)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}?{query}"
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read().decode("utf-8")


def send_message(chat_id, message):
    if not message.strip():
        message = "(No output)"

    chunks = []
    remaining = message
    while remaining:
        chunks.append(remaining[:MESSAGE_LIMIT])
        remaining = remaining[MESSAGE_LIMIT:]

    for chunk in chunks:
        telegram_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": f"<pre>{html.escape(chunk)}</pre>",
                "parse_mode": "HTML",
            },
        )


def normalize_command(text):
    cleaned = " ".join(text.strip().lower().split())
    if "@" in cleaned and cleaned.startswith("/"):
        cleaned = cleaned.split("@", 1)[0]
    return COMMAND_MAP.get(cleaned)


def run_automation(action):
    result = subprocess.run(
        ["python3", "staffpulse_automation.py", action],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )

    parts = []
    if result.stdout:
        parts.append(result.stdout.rstrip())
    if result.stderr:
        parts.append(result.stderr.rstrip())

    combined_output = "\n".join(parts).strip()
    if not combined_output:
        combined_output = "(No output)"

    return combined_output


def process_message(message):
    chat = message.get("chat", {})
    chat_id = str(chat.get("id", ""))
    text = message.get("text", "")

    if not text:
        return

    if ALLOWED_CHAT_ID and chat_id != ALLOWED_CHAT_ID:
        send_message(chat_id, "Unauthorized chat id.")
        return

    action = normalize_command(text)
    if not action:
        send_message(
            chat_id,
            "Supported commands:\ncheckin\ncheckout",
        )
        return

    send_message(chat_id, f"Running {action}...")
    output = run_automation(action)
    send_message(chat_id, output)


def poll_updates():
    offset = None

    while True:
        params = {
            "timeout": POLL_TIMEOUT_SECONDS,
        }
        if offset is not None:
            params["offset"] = offset

        try:
            response = telegram_api("getUpdates", params)
            data = json.loads(response)
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message")
                if message:
                    process_message(message)
        except Exception as exc:
            print(f"Telegram polling error: {exc}", flush=True)
            time.sleep(5)


def main():
    global BOT_TOKEN, ALLOWED_CHAT_ID

    load_env_file()
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    ALLOWED_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    print("Telegram bot polling started", flush=True)
    poll_updates()


if __name__ == "__main__":
    main()
