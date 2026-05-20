#!/usr/bin/env python3
"""
give.do NGO Profile Scraper
============================
Looks up an NGO by name in the scraper sheet, fetches its give.do profile page,
and upserts a research row into the configured research Google Sheet.

Usage:
  python3 give_do_profile_scraper.py "NGO Name"

Setup:
  Requires 'research_sheet_id' in workdocs/bizdev/districts.json.
  The research sheet must be shared with the service account (Editor role).
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

RESEARCH_TAB = "NGO Research"
RESEARCH_HEADER = [
    "NGO Name", "Profile URL", "Cause Areas",
    "Program Count", "Impact Metric Count", "Leadership", "Researched At",
]


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG & AUTH
# ══════════════════════════════════════════════════════════════════════════════

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config not found: {CONFIG_FILE}")
    return json.loads(CONFIG_FILE.read_text())


def get_credentials(sa_file: str) -> Credentials:
    return Credentials.from_service_account_file(sa_file, scopes=SCOPES)


# ══════════════════════════════════════════════════════════════════════════════
#  HTTP
# ══════════════════════════════════════════════════════════════════════════════

def fetch_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


# ══════════════════════════════════════════════════════════════════════════════
#  SHEET LOOKUP
# ══════════════════════════════════════════════════════════════════════════════

def lookup_profile_url(ngo_name: str, sheet_id: str, creds: Credentials) -> str | None:
    """Search all district tabs in the scraper sheet for the NGO → return its Profile URL."""
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    name_lower = ngo_name.strip().lower()

    for ws in sh.worksheets():
        records = ws.get_all_values()
        if not records:
            continue

        header = [h.strip().lower() for h in records[0]]
        try:
            name_col = header.index("ngo name")
            url_col  = header.index("profile url")
        except ValueError:
            continue  # tab has a different structure — skip

        for row in records[1:]:
            if len(row) > max(name_col, url_col):
                if row[name_col].strip().lower() == name_lower:
                    url = row[url_col].strip()
                    if url:
                        return url

    return None


# ══════════════════════════════════════════════════════════════════════════════
#  PROFILE SCRAPING
#
#  give.do profile page structure (verified 2026-05):
#    Each section lives in: div.OverviewTabContentouter
#      ├── div.OverviewMainHeadContent  (contains the h2 heading)
#      └── div.overviewMainDescription (contains the actual content)
#
#    h2 "Cause Area"     → overviewMainDescription
#                            ├── div.OverviewSectors       (primary)
#                            └── div.overviewDesMaincontent (secondary)
#                          each containing ul > li > a > span.badge (sector name)
#    h2 "Programs"       → overviewMainDescription > div.overviewDesOuter
#                            ul.accordionMain.overviewProgram > li (one per program)
#    h2 "Impact Metrics" → overviewMainDescription > div.overviewDesOuter
#                            ul.accordionMain > li (one per metric)
#    h2 "Leadership Team"→ overviewMainDescription > div.overviewDesOuter
#                            ul.tab-inner__team > li
#                              div.tab-inner__info--name (name text + optional LinkedIn a)
# ══════════════════════════════════════════════════════════════════════════════

def scrape_profile(url: str) -> dict:
    print(f"🌐  Fetching: {url}")
    soup = fetch_soup(url)
    return {
        "cause_areas":          _extract_cause_areas(soup),
        "program_count":        _extract_program_count(soup),
        "impact_metric_count":  _extract_impact_metric_count(soup),
        "leadership":           _extract_leadership(soup),
    }


def _section(soup: BeautifulSoup, h2_text: str):
    """Return the OverviewTabContentouter div whose h2 matches h2_text."""
    for h2 in soup.find_all("h2"):
        if h2.get_text(strip=True) == h2_text:
            # h2 → OverviewMainHeading → OverviewMainHeadContent → OverviewTabContentouter
            return h2.parent.parent.parent
    return None


def _extract_cause_areas(soup: BeautifulSoup) -> str:
    sec = _section(soup, "Cause Area")
    if not sec:
        return "N/A"

    desc = sec.find("div", class_="overviewMainDescription")
    if not desc:
        return "N/A"

    areas = []
    # Primary sectors live in div.OverviewSectors, secondary in div.overviewDesMaincontent
    for container in desc.find_all("div", class_=re.compile(r"OverviewSectors|overviewDesMaincontent")):
        for span in container.find_all("span", class_="badge"):
            text = span.get_text(strip=True)
            if text:
                areas.append(text)

    return ", ".join(dict.fromkeys(areas)) if areas else "N/A"


def _extract_program_count(soup: BeautifulSoup) -> int | str:
    sec = _section(soup, "Programs")
    if not sec:
        return "N/A"

    desc = sec.find("div", class_="overviewMainDescription")
    if not desc:
        return "N/A"

    outer = desc.find("div", class_="overviewDesOuter")
    if not outer:
        return "N/A"

    # Each program is one <li> in ul.accordionMain.overviewProgram
    prog_ul = outer.find("ul", class_="overviewProgram")
    if not prog_ul:
        return "N/A"

    count = len(prog_ul.find_all("li", recursive=False))
    return count if count > 0 else "N/A"


def _extract_impact_metric_count(soup: BeautifulSoup) -> int | str:
    sec = _section(soup, "Impact Metrics")
    if not sec:
        return "N/A"

    desc = sec.find("div", class_="overviewMainDescription")
    if not desc:
        return "N/A"

    outer = desc.find("div", class_="overviewDesOuter")
    if not outer:
        return "N/A"

    # Each metric is one <li> in ul.accordionMain
    metric_ul = outer.find("ul", class_="accordionMain")
    if not metric_ul:
        return "N/A"

    count = len(metric_ul.find_all("li", recursive=False))
    return count if count > 0 else "N/A"


def _extract_leadership(soup: BeautifulSoup) -> list[dict]:
    sec = _section(soup, "Leadership Team")
    if not sec:
        return []

    desc = sec.find("div", class_="overviewMainDescription")
    if not desc:
        return []

    outer = desc.find("div", class_="overviewDesOuter")
    if not outer:
        return []

    team_ul = outer.find("ul", class_="tab-inner__team")
    if not team_ul:
        return []

    leaders: list[dict] = []
    for li in team_ul.find_all("li"):
        name_div = li.find("div", class_="tab-inner__info--name")
        if not name_div:
            continue
        # First text node is the person's name; LinkedIn <a> may follow inside the div
        raw_name = next((t.strip() for t in name_div.strings if t.strip()), None)
        if not raw_name:
            continue
        linkedin_a = name_div.find("a", href=re.compile(r"linkedin\.com/in/", re.I))
        linkedin = linkedin_a["href"].strip() if linkedin_a else ""
        leaders.append({"name": raw_name, "linkedin": linkedin})

    return leaders


def _format_leadership(leadership: list[dict]) -> str:
    if not leadership:
        return "N/A"
    parts = []
    for p in leadership:
        if p.get("linkedin"):
            parts.append(f"{p['name']} | {p['linkedin']}")
        else:
            parts.append(p["name"])
    return "\n".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
#  SHEET WRITER
# ══════════════════════════════════════════════════════════════════════════════

def upsert_research_row(
    ngo_name: str,
    profile_url: str,
    data: dict,
    research_sheet_id: str,
    creds: Credentials,
) -> None:
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(research_sheet_id)

    try:
        ws = sh.worksheet(RESEARCH_TAB)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=RESEARCH_TAB, rows=5000, cols=10)
        print(f"   Created tab '{RESEARCH_TAB}'")

    existing = ws.get_all_values()

    # Write header if sheet is empty
    if not existing:
        ws.update([RESEARCH_HEADER], "A1", value_input_option="USER_ENTERED")
        existing = [RESEARCH_HEADER]

    new_row = [
        ngo_name,
        profile_url,
        data["cause_areas"],
        str(data["program_count"]),
        str(data["impact_metric_count"]),
        _format_leadership(data["leadership"]),
        time.strftime("%Y-%m-%d %H:%M:%S"),
    ]

    # Find existing row for this NGO (column A)
    row_index = None
    for i, row in enumerate(existing[1:], start=2):
        if row and row[0].strip().lower() == ngo_name.strip().lower():
            row_index = i
            break

    if row_index:
        ws.update([new_row], f"A{row_index}", value_input_option="USER_ENTERED")
        print(f"   ✓ Updated row {row_index} in '{RESEARCH_TAB}'")
    else:
        ws.append_row(new_row, value_input_option="USER_ENTERED")
        print(f"   ✓ Appended new row in '{RESEARCH_TAB}'")


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Research an NGO from its give.do profile")
    parser.add_argument("ngo_name", help="NGO name as it appears in the scraper sheet")
    args = parser.parse_args()

    config = load_config()
    sheet_id          = config["sheet_id"]
    research_sheet_id = config.get("research_sheet_id")
    sa_file           = str(HERE / config["service_account_file"])

    if not research_sheet_id:
        print("❌  'research_sheet_id' not set in workdocs/bizdev/districts.json")
        print("   Add: \"research_sheet_id\": \"<your-sheet-id>\"")
        return

    creds = get_credentials(sa_file)

    # Step 1: look up profile URL from scraper sheet
    print(f"\n🔍  Looking up '{args.ngo_name}' in scraper sheet …")
    profile_url = lookup_profile_url(args.ngo_name, sheet_id, creds)

    if not profile_url:
        print(f"❌  '{args.ngo_name}' not found in any district tab.")
        print("   Run the scraper first: bash scripts/run_scraper.sh")
        return

    print(f"   Found: {profile_url}")

    # Step 2: scrape the profile page
    data = scrape_profile(profile_url)

    # Step 3: write to research sheet
    print(f"\n📤  Writing to research sheet …")
    upsert_research_row(args.ngo_name, profile_url, data, research_sheet_id, creds)

    # Step 4: summary
    leader_names = ", ".join(p["name"] for p in data["leadership"]) or "N/A"
    print(f"\n{'='*52}")
    print(f"  Research complete: {args.ngo_name}")
    print(f"{'='*52}")
    print(f"  Profile URL:    {profile_url}")
    print(f"  Cause Areas:    {data['cause_areas']}")
    print(f"  Programs:       {data['program_count']}")
    print(f"  Impact Metrics: {data['impact_metric_count']}")
    print(f"  Leadership:     {leader_names}")
    print(f"\n  Sheet: https://docs.google.com/spreadsheets/d/{research_sheet_id}/")


if __name__ == "__main__":
    main()
