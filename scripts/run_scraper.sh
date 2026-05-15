#!/bin/bash
# ============================================================
# give.do NGO Scraper — One-click runner for macOS
# Scrapes all districts registered in districts.json
#
# Usage:
#   bash run_scraper.sh                        # all districts
#   bash run_scraper.sh --district Kochi       # one district
#   bash run_scraper.sh --url <url> --tab <tab> # one-off URL
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=================================================="
echo "  give.do NGO Scraper"
echo "=================================================="
echo ""

# ── 1. Check Python 3 ──────────────────────────────────────
echo "▶  Checking Python 3..."
if ! command -v python3 &>/dev/null; then
  echo "❌  Python 3 not found. Install it from https://python.org"
  exit 1
fi
echo "   $(python3 --version) ✓"
echo ""

# ── 2. Install dependencies ────────────────────────────────
echo "▶  Installing dependencies..."
python3 -m pip install -q --upgrade pip
python3 -m pip install -q -r requirements.txt
echo "   Dependencies ready ✓"
echo ""

# ── 3. Check required files ────────────────────────────────
echo "▶  Checking required files..."
if [ ! -f "districts.json" ]; then
  echo "❌  districts.json not found in $SCRIPT_DIR"
  exit 1
fi
echo "   districts.json ✓"

if [ ! -f "give_do_scraper.py" ]; then
  echo "❌  give_do_scraper.py not found in $SCRIPT_DIR"
  exit 1
fi
echo "   give_do_scraper.py ✓"
echo ""

# ── 4. Run the scraper (pass through any arguments) ────────
echo "▶  Running scraper..."
echo ""
python3 give_do_scraper.py "$@"

echo ""
echo "=================================================="
echo "  All done!"
echo "=================================================="
echo ""
