# /bizdev-setup — Initialize the Bizdev Scraping Pipeline

Walk a new team member through every step needed to get the give.do NGO scraper
running from scratch. Verify each step before moving to the next.

---

## Process

### Step 1 — Check Python 3

Run:
```bash
python3 --version
```

- If Python 3.9+ is present, proceed.
- If missing or below 3.9, tell the user to install it from https://python.org and stop.

### Step 2 — Install Python dependencies

Run from the repo root:
```bash
pip install -r scripts/give_do_requirements.txt
```

Confirm all packages installed without errors (requests, beautifulsoup4, lxml,
gspread, google-auth). If any fail, surface the error and suggest fixes (e.g.
`pip3` vs `pip`, or `--break-system-packages` on newer macOS).

### Step 3 — Google Cloud Project

Prompt the user:

> Do you already have a Google Cloud project you want to use, or should we create
> a new one?

If new: direct them to https://console.cloud.google.com/ → "New Project".

Once they have a project, ask them to enable two APIs inside it:
- Google Sheets API: https://console.cloud.google.com/apis/library/sheets.googleapis.com
- Google Drive API: https://console.cloud.google.com/apis/library/drive.googleapis.com

Wait for confirmation both are enabled before continuing.

### Step 4 — Create a Service Account

Guide the user to:
1. In GCP Console → IAM & Admin → Service Accounts → "Create Service Account"
2. Give it a descriptive name (e.g. `dalgo-bizdev-scraper`)
3. No special IAM role needed at the project level — permissions are granted via
   Sheet sharing (Step 7)
4. On the service account page → Keys → Add Key → JSON → Create
5. A `.json` file will download automatically

Note the `client_email` field in that JSON — they'll need it for Step 7.

### Step 5 — Place the key file in `secrets/`

```bash
# From repo root
mkdir -p secrets
```

Move (do not copy) the downloaded JSON file into `secrets/`. Rename it to
something memorable (e.g. `dalgo-bizdev-scraper.json`). The `secrets/` folder
is gitignored — confirm with:

```bash
git check-ignore -v secrets/
```

If not gitignored, add it:
```bash
echo "secrets/" >> .gitignore
```

### Step 6 — Create the Google Sheet

1. Go to https://sheets.google.com → create a new blank spreadsheet
2. Give it a name like "Dalgo — NGO Prospects"
3. Copy the Sheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit
   ```

### Step 7 — Share the Sheet with the Service Account

In Google Sheets: Share → paste the `client_email` from the JSON key → set role
to **Editor** → Send.

This is the auth step — without it the scraper will get a 403.

### Step 8 — Create the directory structure

```bash
mkdir -p workdocs/bizdev/research
```

Confirm `workdocs/bizdev/` is gitignored (it holds the config with Sheet ID):
```bash
git check-ignore -v workdocs/bizdev/
```

If not gitignored, add it:
```bash
echo "workdocs/bizdev/" >> .gitignore
```

### Step 9 — Create `workdocs/bizdev/districts.json`

Create the file at `workdocs/bizdev/districts.json` with this structure:

```json
{
  "sheet_id": "<SHEET_ID from Step 6>",
  "service_account_file": "../../secrets/<key-filename>.json",
  "districts": [
    {
      "name": "Bangalore",
      "url": "https://give.do/discover/project-district/Bangalore/",
      "tab": "Bangalore"
    }
  ]
}
```

Notes:
- `service_account_file` is relative to the `scripts/` directory (where the
  scraper runs from), so use `../../secrets/...` to reach `secrets/` at the repo root.
- `tab` is the Google Sheet tab name that will be created or overwritten.
- Start with one district — more can be added later with `/bizdev/scraping/add-district`.

Ask the user for:
1. Their Sheet ID
2. Their service account JSON filename
3. Which district(s) they want to start with (suggest Bangalore, Hyderabad,
   Chennai, Kochi as common starting points)

Then write the file with their values.

### Step 10 — Smoke test

Run a single-district scrape to verify the full pipeline:

```bash
bash scripts/run_scraper.sh --district <first district name>
```

Expected output:
- Python version check ✓
- Dependencies ready ✓
- NGO count printed, pages scraped
- Rows written to the Sheet

Open the Google Sheet and confirm rows appeared.

**If 403 error:** Service account doesn't have Sheet access → revisit Step 7.
**If FileNotFoundError on districts.json:** Path issue → check Step 9 structure.
**If ModuleNotFoundError:** Dependencies missing → re-run Step 2.

---

## Setup Complete

Once the smoke test passes, tell the user:

> ✅ Bizdev setup complete! You can now:
>
> - `bash scripts/run_scraper.sh` — scrape all districts
> - `/bizdev/scraping/refresh-source` — same, via Claude
> - `/bizdev/scraping/add-district <Name>` — register a new district
> - `/bizdev/research/research-ngo <NGO Name>` — deep research on a specific NGO
>
> Scraped data lives in your Google Sheet. Research briefs are saved to
> `workdocs/bizdev/research/`.
