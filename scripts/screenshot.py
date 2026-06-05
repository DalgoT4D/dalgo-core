#!/usr/bin/env python3
"""
Dalgo docs screenshot engine.

Loads YAML recipes from scripts/recipes/ and executes them against a logged-in
Playwright session. Each recipe describes the user flows for one product feature
as a list of `flows`, each containing `steps` (navigate, click, wait, snap, press).

Usage:
    uv run python scripts/screenshot.py              # run all recipes
    uv run python scripts/screenshot.py kpis         # one recipe
    uv run python scripts/screenshot.py kpis metrics # several
    uv run python scripts/screenshot.py --list       # list recipes

Environment (from dalgo-core/.env):
    E2E_ADMIN_EMAIL, E2E_ADMIN_PASSWORD, E2E_BASE_URL
"""

import argparse
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page

load_dotenv(Path(__file__).parent.parent / ".env")

REPO_ROOT = Path(__file__).parent.parent
RECIPES_DIR = REPO_ROOT / "scripts" / "recipes"
# Resolve dalgo_docs via the symlink at dalgo-core/dalgo_docs (set up in the repo root).
# This is the sanctioned path — don't assume a sibling layout.
DOCS_IMG_ROOT = (REPO_ROOT / "dalgo_docs" / "static" / "img").resolve()
BASE_URL = os.environ.get("E2E_BASE_URL", "https://staging-app.dalgo.org")
EMAIL = os.environ.get("E2E_ADMIN_EMAIL")
PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD")

RESULTS = []     # list of (feature, label, path)
FAILURES = []    # required-step failures: (feature, message)
WARNINGS = []    # optional-flow skips: (feature, flow_name, message)


def login(page: Page):
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("load")
    page.wait_for_timeout(2000)

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

    page.get_by_role("button", name="SIGN IN").click()
    page.wait_for_function("window.location.pathname !== '/login'", timeout=20000)
    page.wait_for_load_state("load")
    page.wait_for_timeout(1500)
    print(f"✓ Login successful — landed on {page.url}\n")


def discover_recipes():
    """Return {name: path} for all *.yaml files in RECIPES_DIR."""
    return {p.stem: p for p in sorted(RECIPES_DIR.glob("*.yaml"))}


def load_recipe(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def resolve_locator(page: Page, spec: dict):
    """Resolve a click spec to a Playwright locator (or None if no element matched)."""
    if "role" in spec:
        role = spec["role"]
        candidates = spec.get("candidates") or ([spec["name"]] if "name" in spec else [])
        for name in candidates:
            loc = page.get_by_role(role, name=name)
            if loc.count() > 0:
                return loc.first if spec.get("first") else loc
        return None
    if "css" in spec:
        loc = page.locator(spec["css"])
        if loc.count() == 0:
            return None
        return loc.first if spec.get("first") else loc
    raise ValueError(f"click spec needs 'role' or 'css': {spec}")


def execute_step(page: Page, step: dict, feature: str, output_dir: str):
    """Run one step. Raises RuntimeError on failure (caller decides what to do)."""
    if "navigate" in step:
        page.goto(f"{BASE_URL}{step['navigate']}")
        page.wait_for_load_state("load")
        page.wait_for_timeout(2000)
        return

    if "wait" in step:
        page.wait_for_timeout(int(step["wait"]))
        return

    if "click" in step:
        spec = step["click"]
        loc = resolve_locator(page, spec)
        if loc is None:
            raise RuntimeError(f"click selector not found: {spec}")
        loc.click(force=bool(spec.get("force")))
        return

    if "press" in step:
        page.keyboard.press(step["press"])
        return

    if "snap" in step:
        filename = step["snap"]
        label = step.get("label", filename)
        out = DOCS_IMG_ROOT / output_dir / filename
        out.parent.mkdir(parents=True, exist_ok=True)
        page.wait_for_timeout(1000)
        page.screenshot(path=str(out), full_page=bool(step.get("full_page")))
        RESULTS.append((feature, label, str(out)))
        print(f"  ✓ {label} → {out.relative_to(DOCS_IMG_ROOT)}")
        return

    raise ValueError(f"unknown step keys: {list(step.keys())}")


def run_flow(page: Page, flow: dict, feature: str, output_dir: str):
    """Run all steps in a flow. Optional flows skip silently on failure; required abort the recipe."""
    name = flow.get("name", "<unnamed>")
    optional = bool(flow.get("optional"))
    print(f"  ↳ flow: {name}{' (optional)' if optional else ''}")
    try:
        for step in flow.get("steps", []):
            execute_step(page, step, feature, output_dir)
    except Exception as e:
        msg = str(e)
        if optional:
            WARNINGS.append((feature, name, msg))
            print(f"    ⚠ skipped: {msg}")
        else:
            raise  # propagate to abort recipe


def run_recipe(page: Page, name: str, path: Path):
    print(f"\n--- {name} ---")
    recipe = load_recipe(path)
    feature = recipe.get("feature", name)
    output_dir = recipe.get("output_dir", feature)
    nuances = (recipe.get("nuances") or "").strip()
    if nuances:
        for line in nuances.splitlines():
            print(f"  # {line.strip()}")

    try:
        for flow in recipe.get("flows", []):
            run_flow(page, flow, feature, output_dir)
    except RuntimeError as e:
        FAILURES.append((feature, str(e)))
        print(f"  ✗ ABORT recipe '{name}': {e}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run YAML recipes to capture Dalgo docs screenshots."
    )
    parser.add_argument(
        "recipes", nargs="*",
        help="Recipe names to run (e.g. 'kpis metrics'). Default: all.",
    )
    parser.add_argument("--list", action="store_true", help="List available recipes and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    available = discover_recipes()

    if args.list:
        print(f"Available recipes (in {RECIPES_DIR.relative_to(REPO_ROOT)}):")
        for n, p in available.items():
            print(f"  {n}")
        return 0

    if not available:
        print(f"Error: no recipes found in {RECIPES_DIR}", file=sys.stderr)
        return 1

    unknown = [r for r in args.recipes if r not in available]
    if unknown:
        print(f"Error: unknown recipes: {unknown}", file=sys.stderr)
        print(f"Available: {list(available.keys())}", file=sys.stderr)
        return 1

    to_run = {r: available[r] for r in args.recipes} if args.recipes else available

    if not EMAIL or not PASSWORD:
        print("Error: E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD must be set in .env.", file=sys.stderr)
        return 1

    print(f"Base URL: {BASE_URL}")
    print(f"Recipes:  {', '.join(to_run)}")
    print(f"Output:   {DOCS_IMG_ROOT}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1470, "height": 900})
        page = context.new_page()

        print(f"Logging in as {EMAIL}...")
        login(page)

        for name, path in to_run.items():
            run_recipe(page, name, path)

        browser.close()

    print(f"\n{'='*60}")
    print(f"✓ {len(RESULTS)} screenshots saved")
    if WARNINGS:
        print(f"⚠ {len(WARNINGS)} optional flows skipped:")
        for feature, flow, msg in WARNINGS:
            print(f"  - {feature}/{flow}: {msg}")
    if FAILURES:
        print(f"✗ {len(FAILURES)} recipes aborted on required-step failure:")
        for feature, msg in FAILURES:
            print(f"  - {feature}: {msg}")
    print("="*60)
    return 0 if not FAILURES else 2


if __name__ == "__main__":
    sys.exit(main())
