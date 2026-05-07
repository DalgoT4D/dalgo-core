#!/usr/bin/env python3
"""
Playwright screenshot utility for Dalgo documentation.

Logs into the Dalgo webapp and captures screenshots of specified routes.
Reuses the same auth pattern as webapp_v2/e2e/login.spec.ts.

Usage:
    python3 scripts/screenshot.py \
        --urls "/orchestrate" "/orchestrate/create" \
        --output dalgo_docs/static/img/orchestrate/ \
        --names "pipeline_list" "pipeline_create"

Environment variables:
    E2E_ADMIN_EMAIL     Login email (required)
    E2E_ADMIN_PASSWORD  Login password (required)
    E2E_BASE_URL        Base URL (default: http://localhost:3001)
"""

import argparse
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def parse_args():
    parser = argparse.ArgumentParser(
        description="Capture screenshots of Dalgo webapp pages"
    )
    parser.add_argument(
        "--urls",
        nargs="+",
        required=True,
        help="Route paths to screenshot (e.g. /orchestrate /transform)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory for screenshots",
    )
    parser.add_argument(
        "--names",
        nargs="+",
        required=True,
        help="Filenames for each screenshot (without extension), must match --urls count",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1470,
        help="Viewport width (default: 1470)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=900,
        help="Viewport height (default: 900)",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=3000,
        help="Wait time in ms after page load (default: 3000)",
    )
    parser.add_argument(
        "--full-page",
        action="store_true",
        help="Capture full page instead of just the viewport",
    )
    return parser.parse_args()


def login(page, base_url, email, password):
    """Log into Dalgo using the same flow as webapp_v2/e2e/login.spec.ts."""
    page.goto(f"{base_url}/login")

    # Wait for the login form to be ready
    page.get_by_label("Business Email*").wait_for(state="visible", timeout=15000)

    # Fill credentials
    page.get_by_label("Business Email*").fill(email)
    page.get_by_label("Password*").fill(password)

    # Click sign in and wait for redirect to /impact
    page.get_by_role("button", name="Sign In").click()
    page.wait_for_url("**/impact", timeout=15000)


def capture_screenshots(page, base_url, urls, output_dir, names, wait_ms, full_page):
    """Navigate to each URL and capture a screenshot."""
    results = []

    for url, name in zip(urls, names):
        full_url = f"{base_url}{url}"
        output_path = output_dir / f"{name}.png"

        print(f"  Navigating to {url}...")
        page.goto(full_url)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(wait_ms)

        page.screenshot(path=str(output_path), full_page=full_page)
        print(f"  Saved: {output_path}")
        results.append(output_path)

    return results


def main():
    args = parse_args()

    if len(args.urls) != len(args.names):
        print(
            f"Error: --urls has {len(args.urls)} entries but --names has {len(args.names)}. They must match.",
            file=sys.stderr,
        )
        sys.exit(1)

    email = os.environ.get("E2E_ADMIN_EMAIL")
    password = os.environ.get("E2E_ADMIN_PASSWORD")
    base_url = os.environ.get("E2E_BASE_URL", "http://localhost:3001")

    if not email or not password:
        print(
            "Error: E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD environment variables are required.",
            file=sys.stderr,
        )
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": args.width, "height": args.height}
        )
        page = context.new_page()

        print(f"Logging in to {base_url}...")
        login(page, base_url, email, password)
        print("Login successful.")

        print(f"Capturing {len(args.urls)} screenshot(s)...")
        results = capture_screenshots(
            page, base_url, args.urls, output_dir, args.names, args.wait, args.full_page
        )

        browser.close()

    print(f"\nDone. {len(results)} screenshot(s) saved to {output_dir}/")
    for path in results:
        print(f"  {path}")


if __name__ == "__main__":
    main()
