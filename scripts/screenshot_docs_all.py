#!/usr/bin/env python3
"""
Capture all documentation screenshots for Dalgo docs.
Handles tab switching, dialog opening, and interactive states.

Usage:
    E2E_ADMIN_EMAIL=... E2E_ADMIN_PASSWORD=... E2E_BASE_URL=https://staging-app.dalgo.org \
    python3 scripts/screenshot_docs_all.py

Output dirs are relative to the repo root (dalgo-core/).
"""

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, Page

BASE_URL = os.environ.get("E2E_BASE_URL", "https://staging-app.dalgo.org")
EMAIL = os.environ.get("E2E_ADMIN_EMAIL")
PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD")
DOCS_ROOT = Path(__file__).parent.parent.parent / "dalgo_docs" / "static" / "img"

RESULTS = []
FAILURES = []


def ensure_dirs():
    for d in ["ingest", "analysis", "managedata", "orchestrate", "reports", "transform"]:
        (DOCS_ROOT / d).mkdir(parents=True, exist_ok=True)


def login(page: Page):
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("load")
    page.wait_for_timeout(2000)

    # Fill email — try by label, placeholder, or input type
    email_input = (
        page.get_by_label("Business Email*")
        if page.get_by_label("Business Email*").count() > 0
        else page.get_by_placeholder("eg. user@domain.com")
    )
    email_input.fill(EMAIL)

    password_input = (
        page.get_by_label("Password*")
        if page.get_by_label("Password*").count() > 0
        else page.get_by_placeholder("Enter your password")
    )
    password_input.fill(PASSWORD)

    # Click sign in button (case-insensitive match)
    page.get_by_role("button", name="SIGN IN").click()

    # Wait for redirect away from /login (to /impact or wherever)
    page.wait_for_function("window.location.pathname !== '/login'", timeout=20000)
    page.wait_for_load_state("load")
    page.wait_for_timeout(1500)
    print(f"✓ Login successful — landed on {page.url}\n")


def snap(page: Page, rel_path: str, label: str, full_page: bool = False):
    """Take a screenshot and record result."""
    out = DOCS_ROOT / rel_path
    try:
        page.wait_for_timeout(1500)
        page.screenshot(path=str(out), full_page=full_page)
        RESULTS.append((label, str(out)))
        print(f"  ✓ {label} → {rel_path}")
    except Exception as e:
        FAILURES.append((label, str(e)))
        print(f"  ✗ {label} FAILED: {e}")


def try_click(page: Page, selector_fn, timeout=3000) -> bool:
    """Try to click an element; return True if successful."""
    try:
        el = selector_fn()
        el.wait_for(state="visible", timeout=timeout)
        el.click()
        return True
    except Exception:
        return False


def pipeline_overview(page: Page):
    print("--- Pipeline Overview ---")
    page.goto(f"{BASE_URL}/pipeline")
    page.wait_for_load_state("load")
    page.wait_for_timeout(2000)
    snap(page, "managedata/pipeline_overview.png", "Pipeline Overview — cards")

    # Click a bar to expand logs
    clicked = False
    for sel in [
        ".recharts-bar-rectangle",
        "[data-testid='pipeline-run-bar']",
        ".recharts-rectangle",
    ]:
        bars = page.locator(sel).all()
        if bars:
            try:
                bars[0].click(force=True)
                page.wait_for_timeout(1500)
                snap(page, "managedata/pipeline_overview_logs.png", "Pipeline Overview — expanded logs")
                clicked = True
                break
            except Exception:
                pass
    if not clicked:
        print("  ⚠ Could not click a bar to expand logs")


def user_management(page: Page):
    print("--- User Management ---")
    page.goto(f"{BASE_URL}/settings/user-management")
    page.wait_for_load_state("load")
    page.wait_for_timeout(2000)
    snap(page, "managedata/user_management.png", "User Management — users table")

    # Open Invite User dialog
    for name in ["Invite User", "INVITE USER"]:
        btn = page.get_by_role("button", name=name)
        if btn.is_visible():
            btn.click()
            page.wait_for_timeout(1000)
            snap(page, "managedata/user_management_invite.png", "User Management — invite dialog")
            page.keyboard.press("Escape")
            break


def usage_dashboard(page: Page):
    print("--- Usage Dashboard ---")
    page.goto(f"{BASE_URL}/usage-dashboard")
    page.wait_for_load_state("load")
    page.wait_for_timeout(4000)  # Superset iframe may take longer
    snap(page, "managedata/usage_dashboard.png", "Usage Dashboard")


def superset(page: Page):
    print("--- Superset ---")
    page.goto(f"{BASE_URL}/analysis/superset")
    page.wait_for_load_state("load")
    page.wait_for_timeout(3000)
    snap(page, "analysis/superset_signin.png", "Superset sign-in")


def ingest(page: Page):
    print("--- Ingest ---")
    # Connections (default tab)
    page.goto(f"{BASE_URL}/ingest")
    page.wait_for_load_state("load")
    page.wait_for_timeout(2000)
    snap(page, "ingest/connections_list.png", "Ingest — Connections tab")

    # Sources tab
    for tab_name in ["Sources", "SOURCES"]:
        tab = page.get_by_role("tab", name=tab_name)
        if tab.is_visible():
            tab.click()
            page.wait_for_timeout(1500)
            snap(page, "ingest/sources_list.png", "Ingest — Sources tab")

            # Try to open Add Source dialog
            for btn_name in ["+ Add Source", "Add Source", "ADD SOURCE"]:
                btn = page.get_by_role("button", name=btn_name)
                if btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(1000)
                    snap(page, "ingest/sources_add.png", "Ingest — Add Source dialog")
                    page.keyboard.press("Escape")
                    break
            break

    # Your Warehouse tab
    for tab_name in ["Your Warehouse", "YOUR WAREHOUSE", "Warehouse"]:
        tab = page.get_by_role("tab", name=tab_name)
        if tab.is_visible():
            tab.click()
            page.wait_for_timeout(1500)
            snap(page, "ingest/warehouse_form.png", "Ingest — Your Warehouse tab")
            break


def dashboards(page: Page):
    print("--- Dashboards ---")
    page.goto(f"{BASE_URL}/dashboards")
    page.wait_for_load_state("load")
    page.wait_for_timeout(2000)
    snap(page, "analysis/dashboard_list.png", "Dashboards — list")

    # Chart type selector
    page.goto(f"{BASE_URL}/charts/new")
    page.wait_for_load_state("load")
    page.wait_for_timeout(2000)
    snap(page, "analysis/chart_type_selector.png", "Charts — type selector")

    # Dashboard builder — navigate to create, which auto-creates and opens builder
    page.goto(f"{BASE_URL}/dashboards/create")
    page.wait_for_load_state("load")
    page.wait_for_timeout(4000)
    snap(page, "analysis/dashboard_builder.png", "Dashboard — builder canvas")


def orchestrate(page: Page):
    print("--- Orchestrate ---")
    page.goto(f"{BASE_URL}/orchestrate")
    page.wait_for_load_state("load")
    page.wait_for_timeout(2000)
    snap(page, "orchestrate/pipeline_list.png", "Orchestrate — pipeline list")


def reports(page: Page):
    print("--- Reports ---")
    page.goto(f"{BASE_URL}/reports")
    page.wait_for_load_state("load")
    page.wait_for_timeout(2000)
    snap(page, "reports/reports_list.png", "Reports — list")

    # Open Create Report dialog
    for btn_name in ["CREATE REPORT", "Create Report", "+ CREATE REPORT"]:
        btn = page.get_by_role("button", name=btn_name)
        if btn.is_visible():
            btn.click()
            page.wait_for_timeout(1000)
            snap(page, "reports/reports_create.png", "Reports — create dialog")
            page.keyboard.press("Escape")
            break

    # Share menu — click share icon on first report row
    share_btns = page.get_by_test_id("report-share-btn").all()
    if share_btns:
        share_btns[0].click()
        page.wait_for_timeout(800)
        snap(page, "reports/reports_share.png", "Reports — share menu")
        page.keyboard.press("Escape")

    # Comment — open a report and capture comment popover
    report_rows = page.locator("table tbody tr").all()
    if report_rows:
        report_rows[0].click()
        page.wait_for_load_state("load")
        page.wait_for_timeout(2000)
        snap(page, "reports/reports_detail.png", "Reports — detail view")

        # Try clicking comment icon
        comment_btns = page.locator("[data-testid*='comment'], [aria-label*='comment']").all()
        if comment_btns:
            comment_btns[0].click()
            page.wait_for_timeout(800)
            snap(page, "reports/reports_comment.png", "Reports — comment popover")
            page.keyboard.press("Escape")


def main():
    if not EMAIL or not PASSWORD:
        print("Error: E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD must be set.", file=sys.stderr)
        sys.exit(1)

    ensure_dirs()
    print(f"Base URL: {BASE_URL}")
    print(f"Output:   {DOCS_ROOT}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1470, "height": 900})
        page = context.new_page()

        print(f"Logging in as {EMAIL}...")
        login(page)

        pipeline_overview(page)
        user_management(page)
        usage_dashboard(page)
        ingest(page)
        dashboards(page)
        orchestrate(page)
        reports(page)

        browser.close()

    print(f"\n{'='*50}")
    print(f"✓ {len(RESULTS)} screenshots saved")
    if FAILURES:
        print(f"✗ {len(FAILURES)} failed:")
        for label, err in FAILURES:
            print(f"  - {label}: {err}")
    print("="*50)


if __name__ == "__main__":
    main()
