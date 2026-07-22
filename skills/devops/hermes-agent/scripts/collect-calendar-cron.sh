#!/usr/bin/env bash
set -euo pipefail
python3 /home/tapway/.hermes/scripts/collect-calendar.py 2>&1
gbrain import /home/tapway/brain/data/calendar --no-embed 2>&1