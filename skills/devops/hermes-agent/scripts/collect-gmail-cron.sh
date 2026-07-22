#!/usr/bin/env bash
set -euo pipefail
python3 /home/tapway/.hermes/scripts/collect-gmail.py 2>&1
gbrain import /home/tapway/brain/data/email --no-embed 2>&1