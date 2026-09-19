# Base image already ships Chromium + all its system dependencies, so we
# don't have to hand-install a dozen apt packages for Playwright to work.
# The playwright pip version in requirements.txt MUST match this tag's
# version, or the bundled browser and the Python driver won't agree.
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
