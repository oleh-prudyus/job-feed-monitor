# Base image already ships Chromium + all its system dependencies, so we
# don't have to hand-install a dozen apt packages for Playwright to work.
# The playwright pip version in requirements.txt MUST match this tag's
# version, or the bundled browser and the Python driver won't agree.
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Gives Chromium a real (virtual) display via Xvfb, already bundled in this base
# image -- see docker/entrypoint.sh for why it's started manually instead of via
# xvfb-run. Only scraper/freelancehunt_scraper.py actually launches headed (see
# its own comment) -- the other scrapers stay headless=True and are unaffected
# by having a DISPLAY available.
RUN chmod +x docker/entrypoint.sh
ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["python", "main.py"]
