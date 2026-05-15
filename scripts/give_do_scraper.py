#!/usr/bin/env python3
"""
give.do NGO Scraper
===================
Scrapes NGO listings from give.do district pages and writes to Google Sheets.

Usage:
  # Scrape all districts registered in districts.json
  python3 give_do_scraper.py

  # Scrape a single district by name (must exist in districts.json)
  python3 give_do_scraper.py --district Kochi

  # Scrape any give.do district URL directly (one-off, no config needed)
  python3 give_do_scraper.py --url "https://give.do/discover/project-district/Kochi/" --tab "Kochi"

Setup:
  pip install -r give_do_requirements.txt
"""

import argparse
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials

# ── Paths ─────────────────────────────────────────────────────────────────────
HERE = Path(__file__).parent
CONFIG_FILE = HERE.parent / "workdocs" / "bizdev" / "districts.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

DELAY_S = 1.2   # polite pause between page requests

# Profile link pattern: /discover/SHORTCODE/slug/
_PROFILE_RE = re.compile(r"^/discover/[A-Za-z0-9]+/[^/]+/$")

_NON_LOCATION = {
    "Transparency Rating", "Transparency", "Gold Certified 2023",
    "Silver Certified 2023", "Bronze Certified 2023", "Gold Certified",
    "Silver Certified", "Bronze Certified", "FCRA", "80G", "12A", "CSR-1",
    "Total Revenue", "Total Expenses",
}


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════════════

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config not found: {CONFIG_FILE}")
    return json.loads(CONFIG_FILE.read_text())


# ══════════════════════════════════════════════════════════════════════════════
#  FETCHING
# ══════════════════════════════════════════════════════════════════════════════

def fetch_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE-LEVEL METADATA
# ══════════════════════════════════════════════════════════════════════════════

def get_total_count(soup: BeautifulSoup) -> int:
    m = re.search(r"Showing\s+(\d+)\s+NGOs", soup.get_text(" "))
    return int(m.group(1)) if m else -1


PAGE_SIZE = 15  # give.do shows 15 NGOs per page

def get_last_page(total_count: int) -> int:
    """
    Calculate total pages from the advertised NGO count.
    give.do only shows a sliding window of pagination links (e.g. pages 1-3
    on page 1, pages 2-4 on page 2), so reading links from page 1 alone
    always under-counts. Deriving from total_count is reliable.
    """
    if total_count > 0:
        import math
        return math.ceil(total_count / PAGE_SIZE)
    return 1  # fallback: at least one page


# ══════════════════════════════════════════════════════════════════════════════
#  CARD EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def extract_cards(soup: BeautifulSoup) -> list[dict]:
    seen: set[str] = set()
    results: list[dict] = []

    for link in soup.find_all("a", href=_PROFILE_RE):
        href = link["href"]
        if href in seen:
            continue
        seen.add(href)

        ngo_name = link.get_text(strip=True)
        if not ngo_name:
            continue

        full_url = f"https://give.do{href}" if href.startswith("/") else href

        card = link.parent
        for _ in range(8):
            if card is None:
                break
            if "Total Revenue" in card.get_text():
                break
            card = card.parent

        if card is None:
            results.append(_empty_row(ngo_name, full_url))
            continue

        card_lines = [
            ln.strip()
            for ln in card.get_text("\n").splitlines()
            if ln.strip()
        ]

        results.append({
            "name":     ngo_name,
            "location": _extract_location(card_lines, ngo_name),
            "fy_year":  _extract_fy_year(card_lines),
            "revenue":  _extract_revenue(card_lines),
            "url":      full_url,
        })

    return results


def _empty_row(name: str, url: str) -> dict:
    return {"name": name, "location": "N/A", "fy_year": "N/A",
            "revenue": "N/A", "url": url}


def _extract_location(lines: list[str], ngo_name: str) -> str:
    try:
        name_idx = next(i for i, ln in enumerate(lines) if ngo_name in ln)
        for i in range(name_idx + 1, min(name_idx + 5, len(lines))):
            ln = lines[i]
            if ln in _NON_LOCATION:
                continue
            if re.match(r"^[A-Za-z][A-Za-z\s\.\-'()]+(?:,\s*[A-Za-z\s]+)?$", ln) and len(ln) < 70:
                return ln
    except StopIteration:
        pass
    return "N/A"


def _extract_fy_year(lines: list[str]) -> str:
    for ln in lines:
        m = re.match(r"^FY\s*(\d{2}-\d{2})$", ln)
        if m:
            return f"FY {m.group(1)}"
    return "N/A"


def _extract_revenue(lines: list[str]) -> str:
    for i, ln in enumerate(lines):
        if ln == "Total Revenue":
            for j in range(i + 1, min(i + 4, len(lines))):
                val = lines[j].strip()
                if not val:
                    continue
                if val == "--":
                    return "N/A"
                if val in ("₹ None", "₹None"):
                    return "N/A"
                num_str = re.sub(r"[₹\s,]", "", val)
                if num_str.isdigit():
                    return f"₹{int(num_str):,}"
                return val
            break
    return "N/A"


# ══════════════════════════════════════════════════════════════════════════════
#  SCRAPE ONE DISTRICT
# ══════════════════════════════════════════════════════════════════════════════

def scrape_district(base_url: str, district_name: str) -> tuple[list[dict], int]:
    print(f"\n🌐  [{district_name}] Opening page 1 …")
    soup = fetch_soup(base_url)

    total_count = get_total_count(soup)
    last_page   = get_last_page(total_count)

    print(f"📊  Total: {total_count} NGOs  |  Pages: {last_page}")

    all_data: list[dict] = []

    for page_num in range(1, last_page + 1):
        if page_num > 1:
            url = f"{base_url.rstrip('/')}?page={page_num}"
            print(f"   Page {page_num}/{last_page} …")
            time.sleep(DELAY_S)
            soup = fetch_soup(url)
        else:
            print(f"   Page 1/{last_page} …")

        cards = extract_cards(soup)
        all_data.extend(cards)

    print(f"✅  [{district_name}] {len(all_data)} NGOs scraped.")
    return all_data, total_count


# ══════════════════════════════════════════════════════════════════════════════
#  GOOGLE SHEETS WRITER
# ══════════════════════════════════════════════════════════════════════════════

def write_to_sheet(
    data: list[dict],
    total_count: int,
    sheet_id: str,
    tab_name: str,
    sa_file: str,
) -> None:
    print(f"\n📤  Writing to '{tab_name}' …")
    creds = Credentials.from_service_account_file(sa_file, scopes=SCOPES)
    gc    = gspread.authorize(creds)
    sh    = gc.open_by_key(sheet_id)

    try:
        ws = sh.worksheet(tab_name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab_name, rows=5000, cols=10)
        print(f"   Created new tab: '{tab_name}'")

    scraped_at  = time.strftime("%Y-%m-%d %H:%M:%S")
    total_label = str(total_count) if total_count > 0 else "N/A"

    header = [["NGO Name", "HQ Location", "FY Year", "Total Revenue (FY)",
               "Profile URL", "Scraped At", "give.do Total Count"]]

    rows = [
        [
            d["name"], d["location"], d["fy_year"], d["revenue"], d["url"],
            scraped_at  if i == 0 else "",
            total_label if i == 0 else "",
        ]
        for i, d in enumerate(data)
    ]

    ws.update(header + rows, "A1", value_input_option="USER_ENTERED")
    print(f"   ✓ {len(data)} rows written to '{tab_name}'")


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Scrape NGO data from give.do")
    parser.add_argument(
        "--district",
        help="Scrape a specific district by name (must exist in districts.json)",
    )
    parser.add_argument(
        "--url",
        help="Scrape any give.do district URL directly (use with --tab)",
    )
    parser.add_argument(
        "--tab",
        help="Google Sheet tab name (used with --url)",
    )
    args = parser.parse_args()

    config = load_config()
    sheet_id = config["sheet_id"]
    sa_file  = str(HERE / config["service_account_file"])

    # ── Mode 1: one-off URL (no config entry needed) ──
    if args.url:
        tab = args.tab or args.url.rstrip("/").split("/")[-1]
        data, total = scrape_district(args.url, tab)
        if data:
            write_to_sheet(data, total, sheet_id, tab, sa_file)
        return

    # ── Mode 2: single district from config ──────────
    if args.district:
        matches = [d for d in config["districts"]
                   if d["name"].lower() == args.district.lower()]
        if not matches:
            print(f"❌  District '{args.district}' not found in districts.json")
            print(f"   Registered: {[d['name'] for d in config['districts']]}")
            return
        districts = matches

    # ── Mode 3: all districts from config ────────────
    else:
        districts = config["districts"]

    print(f"\n{'='*50}")
    print(f"  give.do Scraper — {len(districts)} district(s)")
    print(f"{'='*50}")

    for d in districts:
        data, total = scrape_district(d["url"], d["name"])
        if data:
            write_to_sheet(data, total, sheet_id, d["tab"], sa_file)

    print(f"\n🎉  All done!")
    print(f"   Sheet: https://docs.google.com/spreadsheets/d/{sheet_id}/")


if __name__ == "__main__":
    main()
