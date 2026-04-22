FROM python:3.11-slim

WORKDIR /app

COPY . .

# Install Chromium + driver
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Install python packages
RUN pip install --no-cache-dir --disable-pip-version-check --root-user-action=ignore -r requirements.txt

CMD ["python3", "scheduler.py"]
