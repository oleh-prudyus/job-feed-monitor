#!/bin/sh
# Starts a virtual display (Xvfb) so Chromium can run headed inside the
# container -- see scraper/freelancehunt_scraper.py for why headed mode is
# needed there. xvfb-run itself was tried first but its startup relies on
# Xvfb sending SIGUSR1 back to the wrapping shell to signal readiness; that
# handshake hung indefinitely in this container (confirmed by hand: Xvfb was
# running fine per `ps`, but xvfb-run's `wait` never returned). Starting Xvfb
# directly and just giving it a moment to come up sidesteps that entirely.
set -e

Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp &
export DISPLAY=:99

# Give Xvfb a moment to start accepting connections before Chromium tries to
# use it -- a fixed short sleep, not a readiness handshake, on purpose (see
# the note above about why the signal-based approach wasn't reliable here).
sleep 2

exec "$@"
